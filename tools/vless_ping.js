const fs = require('fs');
const ping = require('tcp-ping');
const Table = require('cli-table3');
require('colors');

async function measureVless() {
    console.log("🔍 Запускаю замеры латенси и потери пакетов(SYN) для каждого VLESS...\n".cyan);
    
    let config;
    try {
        config = JSON.parse(fs.readFileSync('../vpn-config.json', 'utf8'));
    } catch (e) {
        console.error("Не найден vpn-config.json", e);
        process.exit(1);
    }
    
    if (!config.endpoints || !Array.isArray(config.endpoints)) {
        console.error("В vpn-config.json не найден массив endpoints!");
        process.exit(1);
    }

    const table = new Table({
        head: ['Эндпоинт', 'Тип', 'Хост:Порт', 'Запросы', 'Потеря %', 'Ср. Latency (ms)', 'Статус'],
        style: { head: ['cyan'] }
    });

    const results = [];

    // Подготовим список целей для пинга (VLESS + MTProto)
    const testingTargets = [];
    config.endpoints.forEach(ep => {
        testingTargets.push({
            name: ep.name,
            transport: ep.transport,
            host: ep.host,
            port: ep.port
        });
    });

    if (config.mtproto && config.servers) {
        for (const exitKey in config.mtproto) {
            const exitIP = config.servers[exitKey].ip;
            const mtPort = config.mtproto[exitKey].port;
            
            // Прямое подключение к серверу на порт Docker (8888)
            testingTargets.push({
                name: `mtproto_${exitKey}_direct`,
                transport: 'mtproto',
                host: exitIP,
                port: 8888 
            });
            
            // Подключение через московский relay (порт из конфига)
            if (config.servers.moscow) {
                testingTargets.push({
                    name: `mtproto_${exitKey}_relay`,
                    transport: 'mtproto',
                    host: config.servers.moscow.ip,
                    port: mtPort
                });
            }
        }
    }

    // Запускаем тесты параллельно
    const promises = testingTargets.map(ep => {
        return new Promise((resolve) => {
            ping.ping({ address: ep.host, port: ep.port, attempts: 10, timeout: 1500 }, (err, data) => {
                const loss = data && data.results ? data.results.filter(r => r.err).length : 10;
                const lossPercent = (loss / 10) * 100;
                
                let avg = 'N/A';
                if (data && data.avg && !isNaN(data.avg)) {
                    avg = Math.round(data.avg);
                }

                let statusText = lossPercent === 0 ? '✅ Отлично'.green :
                                 lossPercent < 100 ? '⚠️ Дропы'.yellow : '❌ Мёртв (Time Out)'.red;

                results.push({
                    name: ep.name,
                    transport: ep.transport,
                    target: `${ep.host}:${ep.port}`,
                    lossPercent,
                    avg,
                    statusText
                });

                resolve();
            });
        });
    });

    await Promise.all(promises);

    results.sort((a, b) => a.name.localeCompare(b.name)).forEach(r => {
        table.push([
            r.name,
            r.transport,
            r.target,
            10,
            `${r.lossPercent}%`,
            r.avg,
            r.statusText
        ]);
    });

    console.log(table.toString());

    const deadCount = results.filter(r => r.lossPercent === 100).length;
    if (deadCount > 0) {
        console.log(`\n❌ НАЙДЕНА ПРОБЛЕМА: ${deadCount} эндпоинтов полностью падают по тайм-ауту (Drop).`.red.bold);
        console.log("Это не DPI-блокировка, а закрытые порты на самом сервере! Relay (Moscow) скорее всего не слушает эти порты.".yellow);
    } else {
        console.log("\n✅ Все VLESS эндпоинты доступны, SYN пакеты доходят штатно.".green.bold);
    }
}

measureVless();
