#!/bin/bash

# VPN4Friends Node Bootstrapper
# One-click script for new VPS nodes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== VPN4Friends Node Bootstrapper ===${NC}"

# Check for root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

# Detect OS
OS=$(lsb_release -si || grep "^ID=" /etc/os-release | cut -d= -f2 | tr -d '"')
echo -e "${GREEN}Detected OS: $OS${NC}"

# 1. Update system and install basic tools
echo -e "${YELLOW}1/5 Updating system and installing basic tools...${NC}"
apt-get update && apt-get install -y curl wget git jq sqlite3 ufw

# 2. Install Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}2/5 Installing Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
else
    echo -e "${GREEN}Docker already installed${NC}"
fi

# 3. Install 3x-ui (MHSanaei version)
echo -e "${YELLOW}3/5 Installing 3x-ui...${NC}"
# Use the official install script for host-based install (default for Finland-style)
# Or recommend Docker if preferred. This script uses host-based by default.
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh) <<EOF
y
admin
vpn4friends
2053
EOF

# 4. Patch Database (Drop UNIQUE constraint on email)
echo -e "${YELLOW}4/5 Patching 3x-ui Database...${NC}"
DB_PATH="/etc/x-ui/x-ui.db"

if [ -f "$DB_PATH" ]; then
    echo -e "${YELLOW}Found database at $DB_PATH, applying patch...${NC}"
    
    # Backup
    cp "$DB_PATH" "${DB_PATH}.bak"
    
    # Migration to drop UNIQUE constraint
    sqlite3 "$DB_PATH" "
    BEGIN TRANSACTION;
    CREATE TABLE IF NOT EXISTS client_traffics_new (
        id integer PRIMARY KEY AUTOINCREMENT,
        inbound_id integer,
        enable numeric,
        email text,
        up integer,
        down integer,
        all_time integer,
        expiry_time integer,
        total integer,
        reset integer DEFAULT 0,
        last_online integer DEFAULT 0,
        CONSTRAINT fk_inbounds_client_stats FOREIGN KEY (inbound_id) REFERENCES inbounds(id)
    );
    INSERT INTO client_traffics_new SELECT id, inbound_id, enable, email, up, down, all_time, expiry_time, total, reset, last_online FROM client_traffics;
    DROP TABLE client_traffics;
    ALTER TABLE client_traffics_new RENAME TO client_traffics;
    COMMIT;
    "
    echo -e "${GREEN}Database patch applied successfully!${NC}"
else
    echo -e "${RED}Error: 3x-ui database not found at $DB_PATH${NC}"
fi

# 5. Optional: WARP Setup via wireproxy
# NOTE: Xray's native WireGuard outbound does NOT work in Docker containers
# (kernel TUN fails). We use wireproxy as a userspace WireGuard→SOCKS5 bridge.
# Architecture: xray → socks5://127.0.0.1:40000 → wireproxy → Cloudflare WARP
read -p "Do you want to install Cloudflare WARP (via wireproxy)? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}5/6 Installing WARP via wireproxy...${NC}"

    # Install wireguard-tools (for key generation)
    apt-get install -y wireguard-tools

    # Install wireproxy (userspace WireGuard → SOCKS5)
    WIREPROXY_VER="1.0.9"
    curl -sL "https://github.com/pufferffish/wireproxy/releases/download/v${WIREPROXY_VER}/wireproxy_linux_amd64.tar.gz" \
        | tar xz -C /usr/local/bin/
    echo -e "${GREEN}wireproxy $(wireproxy --version) installed${NC}"

    # Generate WireGuard keys and register with Cloudflare WARP
    PRIVKEY=$(wg genkey)
    PUBKEY=$(echo "$PRIVKEY" | wg pubkey)

    WARP_RESPONSE=$(curl -s 'https://api.cloudflareclient.com/v0a2158/reg' \
        -H 'Content-Type: application/json' \
        -d "{\"key\":\"${PUBKEY}\",\"install_id\":\"\",\"fcm_token\":\"\",\"tos\":\"2024-01-01T00:00:00.000+00:00\",\"model\":\"Linux\",\"locale\":\"en_US\"}")

    WARP_V4=$(echo "$WARP_RESPONSE" | jq -r '.config.interface.addresses.v4')
    WARP_V6=$(echo "$WARP_RESPONSE" | jq -r '.config.interface.addresses.v6')
    echo -e "${GREEN}WARP registered: ${WARP_V4}, ${WARP_V6}${NC}"

    # Create wireproxy config
    cat > /etc/wireproxy.conf << WARPEOF
[Interface]
PrivateKey = ${PRIVKEY}
Address = ${WARP_V4}/32
MTU = 1280
DNS = 1.1.1.1

[Peer]
PublicKey = bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=
Endpoint = engage.cloudflareclient.com:2408
AllowedIPs = 0.0.0.0/0, ::/0

[Socks5]
BindAddress = 127.0.0.1:40000
WARPEOF

    # Create systemd service
    cat > /etc/systemd/system/wireproxy-warp.service << 'SVCEOF'
[Unit]
Description=WireProxy WARP SOCKS5 Proxy
After=network.target

[Service]
ExecStart=/usr/local/bin/wireproxy -c /etc/wireproxy.conf
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable wireproxy-warp
    systemctl start wireproxy-warp

    # Verify
    sleep 2
    HTTP_CODE=$(curl -x socks5://127.0.0.1:40000 http://cp.cloudflare.com/ --max-time 5 -s -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "204" ]; then
        echo -e "${GREEN}WARP is working! (socks5://127.0.0.1:40000)${NC}"
    else
        echo -e "${RED}WARP test failed (HTTP $HTTP_CODE). Check: journalctl -u wireproxy-warp${NC}"
    fi

    echo -e "${YELLOW}Configure xray WARP outbound as socks5 proxy:${NC}"
    echo -e '  {"tag":"warp","protocol":"socks","settings":{"servers":[{"address":"127.0.0.1","port":40000}]}}'
fi

# 6. Firewall setup
echo -e "${YELLOW}6/6 Configuring firewall...${NC}"
ufw allow 22/tcp
ufw allow 2053/tcp       # 3x-ui panel
ufw allow 80/tcp
ufw allow 443/tcp        # VLESS Reality (main)
ufw allow 8443:8449/tcp  # VPN inbound ports (direct, warp, grpc, xhttp)
ufw allow 4443/tcp       # MTProto proxy
ufw allow 1080/tcp       # SOCKS5 proxy (Telegram)
ufw --force enable

echo -e "${GREEN}=== Bootstrapping Complete! ===${NC}"
echo -e "Panel URL: http://$(curl -s ifconfig.me):2053"
echo -e "Login: admin / vpn4friends"
echo -e "${YELLOW}Important: Change your password immediately!${NC}"
echo -e ""
echo -e "${YELLOW}Port allocation:${NC}"
echo -e "  443   — VLESS TCP Reality (Fast/Direct)"
echo -e "  8443  — VLESS TCP Reality (Direct, alt)"
echo -e "  8446  — VLESS TCP Reality → WARP"
echo -e "  8447  — VLESS gRPC Reality (Stealth)"
echo -e "  8448  — VLESS xHTTP Reality → WARP (Stealth)"
echo -e "  4443  — MTProto Proxy (Telegram)"
echo -e "  1080  — SOCKS5 Proxy (Telegram)"
