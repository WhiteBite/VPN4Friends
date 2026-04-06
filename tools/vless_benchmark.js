const fs = require('fs');
const cp = require('child_process');
const path = require('path');
const https = require('https');
const Table = require('cli-table3');
require('colors');

const XRAY_ZIP_URL = "https://github.com/XTLS/Xray-core/releases/download/v1.8.24/Xray-windows-64.zip";
const XRAY_DIR = path.join(__dirname, 'xray_bin');
const XRAY_EXE = path.join(XRAY_DIR, 'xray.exe');

// Функция скачивания и распаковки Xray
async function ensureXray() {
    if (fs.existsSync(XRAY_EXE)) {
        console.log("✅ Локальный Xray Core найден.");
        return;
    }
    console.log("⬇️ Скачивание Xray Core для проведения тестов...");
    try {
        cp.execSync(`powershell -Command "Invoke-WebRequest -Uri '${XRAY_ZIP_URL}' -OutFile xray.zip"`, { stdio: 'inherit' });
        console.log("📦 Распаковка архива...");
        cp.execSync(`powershell -Command "Expand-Archive -Path xray.zip -DestinationPath '${XRAY_DIR}' -Force"`, { stdio: 'inherit' });
        fs.unlinkSync('xray.zip');
        console.log("✅ Xray Core успешно установлен.");
    } catch(e) {
        console.error("❌ Ошибка при скачивании Xray:", e.message);
        process.exit(1);
    }
}

// Генератор конфига клиента
function generateClientConfig(endpoint) {
    const streamSettings = {
        network: endpoint.transport,
        security: endpoint.security,
        realitySettings: {
            serverName: endpoint.sni,
            fingerprint: "chrome",
            publicKey: endpoint.pbk,
            shortId: endpoint.sid,
            spiderX: ""
        }
    };

    if (endpoint.transport === "grpc") {
        streamSettings.grpcSettings = { serviceName: endpoint.serviceName || "grpc", multiMode: true };
    } else if (endpoint.transport === "xhttp") {
        streamSettings.xhttpSettings = { path: endpoint.path || "/xhttp", host: endpoint.sni };
    } else if (endpoint.transport === "tcp") {
        // TCP typically uses none or http headers if configured, here none
    }

    return {
        log: { loglevel: "none" },
        inbounds: [{
            port: 14808,
            listen: "127.0.0.1",
            protocol: "socks",
            settings: { udp: true }
        }],
        outbounds: [{
            protocol: "vless",
            settings: {
                vnext: [{
                    address: endpoint.host,
                    port: endpoint.port,
                    users: [{ id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890", encryption: "none", flow: endpoint.flow || "" }]
                }]
            },
            streamSettings
        }]
    };
}

// Запуск бенчмарка через curl (Parallel Live Streaming)
function runBenchmark(durationSeconds = 60) {
    return new Promise((resolve) => {
        let successCount = 0;
        let failCount = 0;
        let latencies = [];
        let reqsStarted = 0;
        let reqsFinished = 0;

        process.stdout.write(` [`);

        const durationMs = durationSeconds * 1000;
        const intervalMs = 200; // 5 pings per second
        const totalExpectedReqs = Math.floor(durationMs / intervalMs);

        let timeoutHandler;

        const finish = () => {
             process.stdout.write(`] `);
             const total = successCount + failCount;
             const loss = total === 0 ? "100" : ((failCount / total) * 100).toFixed(0);
             if (latencies.length === 0) {
                 return resolve({ avg: 'N/A', max: 'N/A', jitter: 'N/A', loss: `${loss}%` });
             }
             const sum = latencies.reduce((a,b)=>a+b, 0);
             const avg = sum / latencies.length;
             const max = Math.max(...latencies);
             const variance = latencies.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / latencies.length;
             const jitter = Math.round(Math.sqrt(variance));
             return resolve({ avg: Math.round(avg), max: Math.round(max), jitter, loss: `${loss}%` });
        };

        const timer = setInterval(() => {
            reqsStarted++;
            if (reqsStarted > totalExpectedReqs) {
                clearInterval(timer);
                timeoutHandler = setTimeout(() => {
                    // Timeout fallback to resolve if curls get permanently stuck
                    if(reqsFinished < totalExpectedReqs) {
                         failCount += (totalExpectedReqs - reqsFinished);
                         reqsFinished = totalExpectedReqs;
                         finish();
                    }
                }, 3000);
                return;
            }

            const curlCmd = `curl -s -o NUL -w "%{time_starttransfer}" -x socks5h://127.0.0.1:14808 --connect-timeout 2 -m 2 http://www.gstatic.com/generate_204`;
            
            cp.exec(curlCmd, (err, stdout) => {
                if (reqsFinished >= totalExpectedReqs) return;
                reqsFinished++;
                
                let time = parseFloat(stdout.replace(',', '.'));
                if (err || isNaN(time) || time === 0) {
                    failCount++;
                    process.stdout.write('X'.red);
                } else {
                    successCount++;
                    const ms = time * 1000;
                    latencies.push(ms);
                    if (ms < 50) process.stdout.write('.'.green);
                    else if (ms < 100) process.stdout.write('o'.yellow);
                    else if (ms < 300) process.stdout.write('O'.magenta);
                    else process.stdout.write('!'.red);
                }

                if (reqsStarted >= totalExpectedReqs && reqsFinished >= totalExpectedReqs) {
                    clearTimeout(timeoutHandler);
                    finish();
                }
            });
        }, intervalMs);
    });
}

async function run() {
    await ensureXray();

    // Parse arguments
    const args = process.argv.slice(2);
    let durationSeconds = 60;
    let filterString = "";

    for (const arg of args) {
        if (arg === "--help" || arg === "-h") {
            console.log("Usage: node vless_benchmark.js [--duration=SECONDS] [--filter=TEXT]");
            console.log("  --duration=SEC   Test duration per node in seconds (default: 60)");
            console.log("  --filter=TEXT    Only test endpoints containing TEXT (e.g. msk_tcp, finland)");
            process.exit(0);
        } else if (arg.startsWith("--duration=")) {
            durationSeconds = parseInt(arg.split("=")[1], 10);
        } else if (arg.startsWith("--filter=")) {
            filterString = arg.split("=")[1];
        }
    }

    let config;
    try {
        config = JSON.parse(fs.readFileSync('../vpn-config.json', 'utf8'));
    } catch(e) {
        console.error("vpn-config.json not found");
        return;
    }

    // Ищем все эндпоинты (Direct и Relay)
    let endpointsToTest = config.endpoints;
    if (filterString) {
        endpointsToTest = endpointsToTest.filter(e => e.name.includes(filterString));
    }
    
    console.log(`\n🚀 Запускаю Payload-Бенчмарк для ${endpointsToTest.length} протоколов (Длительность: ${durationSeconds}с/каждый)...`.bold);
    console.log(`Это стресс-тест через настоящий туннель: поднимаем Xray, прогоняем серию HTTP-запросов, замеряем Jitter.\n`.gray);

    const table = new Table({
        head: ['Эндпоинт', 'Протокол', 'Avg Ping', 'Max Ping', 'Jitter (Скачки)', 'Loss %'],
        style: { head: ['cyan'] }
    });

    for (const ep of endpointsToTest) {
        process.stdout.write(`⏳ ${ep.name.bold.yellow} (${ep.transport})`);
        
        // ВАЖНО: Вписываем UUID (его тут нет жестко в endpoints, берем из reality)
        const clientCfg = generateClientConfig(ep);
        clientCfg.outbounds[0].settings.vnext[0].users[0].id = config.reality.uuid;

        fs.writeFileSync('temp_config.json', JSON.stringify(clientCfg, null, 2));

        // Старт локального Xray
        let xrayProc;
        try {
            xrayProc = cp.spawn(XRAY_EXE, ['run', '-c', 'temp_config.json']);
        } catch(e) {
            console.log(" Не удалось запустить Xray");
            continue;
        }

        // Ждем 1500мс для надежного старта туннеля
        await new Promise(r => setTimeout(r, 1500));

        // Запуск теста
        const metrics = await runBenchmark(durationSeconds);
        
        const lossColor = metrics.loss === '0%' ? 'green' : (metrics.loss === '100%' ? 'red' : 'yellow');
        const jitterColor = metrics.jitter === 'N/A' ? 'red' : (metrics.jitter < 20 ? 'green' : 'yellow');
        
        table.push([
            ep.name,
            ep.transport,
            metrics.avg !== 'N/A' ? `${metrics.avg}ms` : 'N/A',
            metrics.max !== 'N/A' ? `${metrics.max}ms` : 'N/A',
            metrics.jitter !== 'N/A' ? String(metrics.jitter)[jitterColor] : 'N/A',
            metrics.loss[lossColor]
        ]);

        process.stdout.write(` Готово! Jitter: ${metrics.jitter}ms\n`);
        
        // Убиваем процесс надежно
        try {
            cp.execSync('taskkill /F /IM xray.exe /T', { stdio: 'inherit' });
        } catch(e) {}
        await new Promise(r => setTimeout(r, 500));
    }

    console.log("\n" + table.toString());
    console.log("\n💡 Как читать результаты:");
    console.log(" - Jitter (Скачки): Чем ниже, тем лучше для онлайн-игр. Высокий джиттер означает, что провайдер роняет пакеты на пути, и TCP-ретрай тормозит весь туннель.");
    console.log(" - Loss %: Если не 0%, значит Xray не справляется и сервер физически недоступен или жестко фильтруется.");
}

run();
