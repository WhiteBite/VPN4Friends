const net = require('net');
const config = require('../vpn-config.json');

const duration = 60 * 1000;
console.log(`🚀 Запускаю TCP Бенчмарк для MTProto (Длительность: 60с) на сервере Moscow...`);

async function benchMTProto(host, port, name) {
    let success = 0;
    let drops = 0;
    let totalLatency = 0;
    const startTime = Date.now();
    let bar = `⏳ ${name} (${host}:${port}) [`;
    
    return new Promise(resolve => {
        const interval = setInterval(() => {
            if (Date.now() - startTime > duration) {
                clearInterval(interval);
                bar += "]";
                const avg = success > 0 ? Math.round(totalLatency / success) : 0;
                const loss = Math.round((drops / (success + drops)) * 100);
                console.log(`${bar} Готово! Ping: ${avg}ms, Drops: ${loss}%`);
                resolve();
                return;
            }

            const startRequest = Date.now();
            const socket = new net.Socket();
            socket.setTimeout(2000); // 2s timeout
            
            socket.connect(port, host, () => {
                const latency = Date.now() - startRequest;
                totalLatency += latency;
                success++;
                process.stdout.write('O');
                socket.destroy();
            });
            
            socket.on('timeout', () => {
                drops++;
                process.stdout.write('!');
                socket.destroy();
            });
            
            socket.on('error', () => {
                drops++;
                process.stdout.write('E');
                socket.destroy();
            });
            
        }, 1000);
    });
}

(async () => {
    // mtproto.finland runs on moscow relay at port 4443
    await benchMTProto(config.servers.moscow.ip, config.mtproto.finland.port, 'MTProto Finland');
    // mtproto.netherlands runs on moscow relay at port 4444
    await benchMTProto(config.servers.moscow.ip, config.mtproto.germany.port, 'MTProto Germany');
})();
