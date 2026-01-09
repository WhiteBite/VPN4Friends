#!/bin/bash
set -e

echo "=== Installing 3X-UI on New Server ==="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Waiting for installation to complete..."
    sleep 60
fi

# Check again
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
fi

echo "✅ Docker installed"
docker --version

# Create directories
echo ""
echo "Creating directories..."
mkdir -p /opt/3x-ui/db
mkdir -p /opt/3x-ui/cert

# Copy docker-compose file
echo "Copying docker-compose file..."
cp /root/VPN4Friends/docker-compose-new.yml /root/docker-compose.yml

# Start 3x-ui
echo ""
echo "Starting 3X-UI container..."
cd /root
docker-compose up -d

# Wait for container to start
echo "Waiting for 3X-UI to start..."
sleep 10

# Check status
docker ps | grep 3x-ui

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Access panel: http://185.23.238.162:2053"
echo "Default login: admin / admin"
echo ""
echo "Next: Generate Reality keys and configure inbound"
