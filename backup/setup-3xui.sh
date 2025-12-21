#!/bin/bash
# Quick 3X-UI Setup Script
# Run as root on fresh Debian/Ubuntu

set -e

echo "=== Installing Docker ==="
curl -fsSL https://get.docker.com | sh

echo "=== Creating directories ==="
mkdir -p /opt/3x-ui/db /opt/3x-ui/cert
cd /opt/3x-ui

echo "=== Creating docker-compose.yml ==="
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  3x-ui:
    image: ghcr.io/mhsanaei/3x-ui:latest
    container_name: 3x-ui
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./db/:/etc/x-ui/
      - ./cert/:/root/cert/
    environment:
      - XRAY_VMESS_AEAD_FORCED=false
    tty: true
EOF

echo "=== Applying sysctl optimizations ==="
cat >> /etc/sysctl.conf << 'EOF'

# === VPN Optimization ===
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576
net.ipv4.tcp_rmem = 4096 1048576 16777216
net.ipv4.tcp_wmem = 4096 1048576 16777216
net.core.netdev_max_backlog = 65536
net.core.somaxconn = 65535
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_mtu_probing = 1
EOF

sysctl -p

echo "=== Starting 3X-UI ==="
docker compose up -d

echo ""
echo "=== DONE ==="
echo "Panel: http://$(curl -s ifconfig.me):2053/panel/"
echo "Login: admin / admin"
echo ""
echo "IMPORTANT: Change password immediately!"
