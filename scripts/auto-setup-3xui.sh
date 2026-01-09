#!/bin/bash
# Автоматическая установка 3X-UI после установки Docker

echo "Waiting for Docker installation to complete..."

# Wait for Docker
while ! command -v docker &> /dev/null; do
    echo "Docker not ready, waiting..."
    sleep 10
done

echo "✅ Docker is ready!"
docker --version

# Start Docker service
systemctl start docker
systemctl enable docker

# Create directories
echo "Creating directories..."
mkdir -p /opt/3x-ui/db
mkdir -p /opt/3x-ui/cert

# Create docker-compose.yml
echo "Creating docker-compose.yml..."
cat > /root/docker-compose.yml << 'EOF'
version: '3.8'

services:
  3x-ui:
    image: ghcr.io/mhsanaei/3x-ui:v2.8.7
    container_name: 3x-ui
    restart: unless-stopped
    network_mode: host
    volumes:
      - /opt/3x-ui/db:/etc/x-ui
      - /opt/3x-ui/cert:/root/cert
    environment:
      - XRAY_VMESS_AEAD_FORCED=false
    tty: true
EOF

# Start 3X-UI
echo "Starting 3X-UI..."
cd /root
docker compose up -d

# Wait for container
sleep 10

# Check status
echo ""
echo "=== Status ==="
docker ps | grep 3x-ui

echo ""
echo "=== 3X-UI Installation Complete ==="
echo ""
echo "Access panel: http://185.23.238.162:2053"
echo "Login: admin / admin"
echo ""
echo "Next: Configure Reality VPN"
echo "Run: bash /root/VPN4Friends/scripts/configure-reality.sh"
