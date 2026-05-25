#!/bin/bash
# ============================================
# VPN4Friends - New Server Deployment Script
# ============================================
# Run this on the NEW server as root

set -e

NEW_SERVER_IP="${1:-YOUR_NEW_SERVER_IP}"
DOMAIN="${2:-ger1.whitebite.ru}"
XUI_USER="${3:-***REMOVED***}"
XUI_PASS="${4:-$(openssl rand -base64 16)}"

if [ "$NEW_SERVER_IP" = "YOUR_NEW_SERVER_IP" ]; then
    echo "Usage: $0 <new_server_ip> [domain] [xui_user] [xui_pass]"
    echo "Example: $0 203.0.113.1 ger1.whitebite.ru ***REMOVED*** ***REMOVED***"
    exit 1
fi

echo "=== VPN4Friends New Server Deployment ==="
echo "IP: $NEW_SERVER_IP"
echo "Domain: $DOMAIN"
echo "X-UI User: $XUI_USER"
echo ""

# 1. Update system
echo "[1/10] Updating system..."
apt update && apt upgrade -y
apt install -y curl wget git nginx certbot python3-certbot-nginx ufw

# 2. Install Docker
echo "[2/10] Installing Docker..."
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 3. Install 3X-UI
echo "[3/10] Installing 3X-UI..."
bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh)

# 4. Install MTProto
echo "[4/10] Installing MTProto Proxy..."
wget https://github.com/9seconds/mtg/releases/download/v2.1.7/mtg-2.1.7-linux-amd64.tar.gz
tar xzf mtg-2.1.7-linux-amd64.tar.gz
cp mtg-2.1.7-linux-amd64 /usr/local/bin/mtg
chmod +x /usr/local/bin/mtg
rm -rf mtg-2.1.7-linux-amd64*

# Generate new MTProto secret
MTPROTO_SECRET=$(openssl rand -hex 32)
echo "MTProto Secret: $MTPROTO_SECRET"

# 5. Setup firewall
echo "[5/10] Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8440/tcp   # MTProto
ufw allow 8443/tcp   # VLESS
ufw allow 8444/tcp   # VLESS
ufw allow 8445/tcp   # VLESS
ufw allow 8446/tcp   # VLESS
ufw allow 8447/tcp   # VLESS
ufw allow 8448/tcp   # VLESS
ufw allow 2053/tcp   # X-UI Panel
ufw --force enable

# 6. Setup systemd for xray auto-start
echo "[6/10] Creating systemd service for xray..."
cat > /etc/systemd/system/xray-vpn.service << 'EOF'
[Unit]
Description=Xray VPN Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/usr/local/x-ui
ExecStart=/usr/local/x-ui/bin/xray-linux-amd64 run -config /usr/local/x-ui/bin/config.json
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable xray-vpn

# 7. Setup cron for config auto-fix
echo "[7/10] Setting up cron auto-fix..."
cat > /usr/local/bin/fix-xray-config.py << 'PYEOF'
import json
import sys

def fix_config():
    try:
        with open('/usr/local/x-ui/bin/config.json', 'r') as f:
            config = json.load(f)
        
        modified = False
        if 'inbounds' in config:
            for inbound in config['inbounds']:
                settings = inbound.get('settings')
                if isinstance(settings, str):
                    try:
                        inbound['settings'] = json.loads(settings)
                        modified = True
                    except:
                        pass
        
        if modified:
            with open('/usr/local/x-ui/bin/config.json', 'w') as f:
                json.dump(config, f, indent=2)
            print("Fixed config.json")
            return True
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if fix_config():
        sys.exit(0)
    sys.exit(1)
PYEOF
chmod +x /usr/local/bin/fix-xray-config.py

cat > /etc/cron.d/fix-xray-config << 'EOF'
*/2 * * * * root /usr/bin/python3 /usr/local/bin/fix-xray-config.py > /dev/null 2>&1
EOF
chmod 644 /etc/cron.d/fix-xray-config

# 8. Setup MTProto systemd
echo "[8/10] Creating MTProto service..."
cat > /etc/systemd/system/mtg.service << EOF
[Unit]
Description=MTProto Proxy
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/mtg simple-run 0.0.0.0:8440 ee${MTPROTO_SECRET}***REMOVED***
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable mtg

# 9. Clone project
echo "[9/10] Cloning VPN4Friends..."
cd /root
git clone https://github.com/WhiteBite/VPN4Friends.git
cd VPN4Friends

# 10. Generate new keys
echo "[10/10] Generating new Reality keys..."
REALITY_KEYS=$(docker run --rm -it teddysun/xray xray x25519)
PRIVATE_KEY=$(echo "$REALITY_KEYS" | grep "Private key:" | awk '{print $3}')
PUBLIC_KEY=$(echo "$REALITY_KEYS" | grep "Public key:" | awk '{print $3}')
UUID=$(docker run --rm -it teddysun/xray xray uuid)
SHORT_ID=$(openssl rand -hex 8)

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo ""
echo "New Reality Keys:"
echo "  UUID: $UUID"
echo "  Private Key: $PRIVATE_KEY"
echo "  Public Key: $PUBLIC_KEY"
echo "  Short ID: $SHORT_ID"
echo ""
echo "MTProto Secret: $MTPROTO_SECRET"
echo ""
echo "Next steps:"
echo "1. Update vpn-config.json with new server IP and keys"
echo "2. Update GitHub Secrets:"
echo "   - SERVER_HOST: $NEW_SERVER_IP"
echo "   - VPN_CONFIG: (new config with updated values)"
echo "3. Copy your old config.json from backup:"
echo "   scp backup/config.json root@$NEW_SERVER_IP:/usr/local/x-ui/bin/"
echo "4. Start services: systemctl start xray-vpn mtg"
echo "5. Setup Let's Encrypt: certbot certonly --standalone -d $DOMAIN"
echo ""
