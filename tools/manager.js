const fs = require('fs');
const path = require('path');
const { Client } = require('ssh2');
const crypto = require('crypto');

const CONFIG_PATH = path.join(__dirname, '../vpn-config.json');

function loadConfig() {
    if (!fs.existsSync(CONFIG_PATH)) {
        console.error("vpn-config.json not found! Please create it from vpn-config.example.json.");
        process.exit(1);
    }
    return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
}

async function sshExec(conn, cmd) {
    return new Promise((resolve, reject) => {
        conn.exec(cmd, (err, stream) => {
            if (err) return reject(err);
            let out = '';
            stream.on('close', (code, signal) => resolve({ code, out })).on('data', (data) => out += data).stderr.on('data', (data) => out += data);
        });
    });
}

async function sftpWrite(conn, path, content) {
    return new Promise((resolve, reject) => {
        conn.sftp((err, sftp) => {
            if (err) return reject(err);
            const stream = sftp.createWriteStream(path);
            stream.on('close', () => resolve());
            stream.on('error', reject);
            stream.write(content);
            stream.end();
        });
    });
}

async function connectSSH(host, user, password) {
    return new Promise((resolve, reject) => {
        const conn = new Client();
        conn.on('ready', () => resolve(conn)).on('error', reject).connect({
            host, port: 22, username: user, password, readyTimeout: 10000
        });
    });
}

// Generate MTProxy string
function generateMTProxySecret() {
    const randomHex = crypto.randomBytes(16).toString('hex');
    const domainHex = Buffer.from('google.com').toString('hex');
    return 'ee' + randomHex + domainHex;
}

// Ensure Xray is installed
async function installXray(conn) {
    console.log("   Checking Xray installation...");
    const res = await sshExec(conn, "xray version || echo 'NOT_FOUND'");
    if (res.out.includes('NOT_FOUND')) {
        console.log("   Installing Xray...");
        await sshExec(conn, "bash -c '$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)' @ install");
    }
}

async function deployExitNode(name, data, config) {
    console.log(`\n[+] Deploying Exit Node: ${name} (${data.ip})`);
    if (!data.ssh_pass) {
        console.log(`   Skipping: No ssh_pass set in config for ${name}`);
        return;
    }
    
    const conn = await connectSSH(data.ip, data.ssh_user || 'root', data.ssh_pass);
    await installXray(conn);

    // 1. Configure Xray Tunnel Receiver
    const xrayConfig = {
        inbounds: [{
            port: 9443,
            protocol: "vless",
            settings: {
                clients: [ { id: config.reality.uuid, flow: "" } ],
                decryption: "none"
            },
            streamSettings: {
                network: "tcp",
                security: "reality",
                realitySettings: {
                    dest: "vk.com:443",
                    serverNames: ["vk.com"],
                    privateKey: config.reality.private_key,
                    shortIds: [config.reality.short_id]
                }
            }
        }],
        outbounds: [ { protocol: "freedom" } ]
    };

    console.log("   Pushing Xray receiver config...");
    await sftpWrite(conn, "/tmp/config.json", JSON.stringify(xrayConfig, null, 2));
    await sshExec(conn, "mkdir -p /etc/xray && cp /tmp/config.json /etc/xray/config.json");
    await sshExec(conn, "systemctl restart xray");

    // 2. Install Docker & MTProxy
    console.log("   Checking Docker...");
    await sshExec(conn, "apt-get update && apt-get install -y docker.io");
    
    console.log("   Deploying MTProxy container...");
    let mt_secret = config.mtproto[name]?.secret || generateMTProxySecret();
    if (mt_secret.startsWith('ee') && mt_secret.length > 34) {
        mt_secret = mt_secret.substring(2, 34);
    }
    await sshExec(conn, "docker stop mtproxy || true");
    await sshExec(conn, "docker rm mtproxy || true");
    
    const dockerCmd = `docker run -d --name mtproxy -p 8888:443 --restart always -v proxy-config:/data -e SECRET=${mt_secret} telegrammessenger/proxy:latest`;
    await sshExec(conn, dockerCmd);

    console.log("   Exit Node deployed!");
    conn.end();
}

async function deployRelayNode(data, config) {
    console.log(`\n[+] Deploying Relay Node: moscow (${data.ip})`);
    if (!data.ssh_pass) {
         console.log("   Skipping: No ssh_pass set in config for moscow");
         return;
    }
    
    const conn = await connectSSH(data.ip, data.ssh_user || 'root', data.ssh_pass);
    await installXray(conn);

    const inbounds = [];
    const outbounds = [];
    const routingRules = [];

    // Base Outbounds
    outbounds.push({ tag: "direct", protocol: "freedom" });

    // Loop all Exit Nodes to build tunnels and dokodemo-doors
    const exitNodes = Object.keys(config.servers).filter(k => k !== 'moscow');

    for (const [index, exitKey] of exitNodes.entries()) {
        const exitIP = config.servers[exitKey].ip;
        const tunTag = `tunnel-${exitKey}`;
        
        // Outbound
        outbounds.push({
            tag: tunTag,
            protocol: "vless",
            mux: { enabled: true, concurrency: 8 },
            settings: { vnext: [ { address: exitIP, port: 9443, users: [ { id: config.reality.uuid, encryption: "none", flow: "" } ] } ] },
            streamSettings: {
                network: "tcp",
                security: "reality",
                realitySettings: {
                    serverName: "vk.com",
                    fingerprint: "chrome",
                    publicKey: config.reality.public_key,
                    shortId: config.reality.short_id
                }
            }
        });

        // 3X-UI Traffic (Dynamic mapping based on endpoints)
        const inTags = [];
        
        // Find all relay endpoints for this exit node
        const relayPrefix = `${exitKey}_msk_`;
        const relayEndpoints = config.endpoints.filter(e => e.name.startsWith(relayPrefix));
        
        for (const rEp of relayEndpoints) {
            const transportType = rEp.name.replace(relayPrefix, ''); // e.g. "tcp", "warp", "grpc"
            const directEpName = `${exitKey}_${transportType}`;
            
            // Find corresponding direct endpoint to know the target port on Finland
            const directEp = config.endpoints.find(e => e.name === directEpName);
            if (!directEp) continue;

            const moscowPort = rEp.port;
            const targetExitPort = directEp.port;
            
            const tag = `in-${exitKey}-${transportType}`;
            inTags.push(tag);
            inbounds.push({ port: moscowPort, protocol: "dokodemo-door", settings: { address: exitIP, port: targetExitPort, network: "tcp,udp" }, tag });
        }

        if (inTags.length > 0) {
            routingRules.push({ type: "field", inboundTag: inTags, outboundTag: tunTag });
        }

        // MTProto Traffic
        if (config.mtproto[exitKey]) {
            const mtPort = config.mtproto[exitKey].port; // Note: MTProto client config sets this port for Moscow
            const mtTag = `mt-${exitKey}`;
            // MTProto docker is deployed on port 8888 on exit nodes
            inbounds.push({ port: mtPort, protocol: "dokodemo-door", settings: { address: exitIP, port: 8888, network: "tcp" }, tag: mtTag });
            routingRules.push({ type: "field", inboundTag: [mtTag], outboundTag: tunTag });
        }
    }

    const moscowConfig = {
        log: { loglevel: "warning" },
        inbounds,
        outbounds,
        routing: { domainStrategy: "AsIs", rules: routingRules }
    };

    console.log("   Pushing Xray Relay config...");
    await sftpWrite(conn, "/tmp/config.json", JSON.stringify(moscowConfig, null, 2));
    await sshExec(conn, "sudo mkdir -p /usr/local/etc/xray && sudo cp /tmp/config.json /usr/local/etc/xray/config.json");
    await sshExec(conn, "sudo systemctl restart xray");

    console.log("   Relay Node deployed!");
    conn.end();
}

async function main() {
    const args = process.argv.slice(2);
    const cmd = args[0] || 'help';

    if (cmd === 'deploy') {
        const config = loadConfig();
        console.log("Starting VPN4Friends Automated Deployment...");
        
        // 1. Deploy Exit Nodes
        const exitNodes = Object.keys(config.servers).filter(k => k !== 'moscow');
        for (const name of exitNodes) {
           try {
               await deployExitNode(name, config.servers[name], config);
           } catch(e) {
               console.error(`[-] Failed on ${name}: ${e.message}`);
           }
        }

        // 2. Deploy Moscow Relay
        if (config.servers.moscow) {
            try {
                await deployRelayNode(config.servers.moscow, config);
            } catch(e) {
                console.error(`[-] Failed on moscow: ${e.message}`);
            }
        }
        
        console.log("\n[✓] Deployment Complete!");
        console.log("Reminder: This script deployed the network tunnels.");
        console.log("To deploy the Bot & Fastapi on Moscow, use your GitHub Action, or run standard docker-compose on the relay.");
    } else {
        console.log("Usage: node manager.js deploy");
    }
}

main();
