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

# 5. Optional: WARP Setup
read -p "Do you want to install Cloudflare WARP? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}5/5 Installing Cloudflare WARP...${NC}"
    # Install warp-cli
    curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/cloudflare-client.list
    apt-get update && apt-get install -y cloudflare-warp
    
    # Registration (manual intervention usually needed here if using CLI)
    echo -e "${YELLOW}WARP installed. Run 'warp-cli registration new' to register.${NC}"
fi

# 6. Firewall setup
echo -e "${YELLOW}6/6 Configuring firewall...${NC}"
ufw allow 22/tcp
ufw allow 2053/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo -e "${GREEN}=== Bootstrapping Complete! ===${NC}"
echo -e "Panel URL: http://$(curl -s ifconfig.me):2053"
echo -e "Login: admin / vpn4friends"
echo -e "${YELLOW}Important: Change your password immediately!${NC}"
