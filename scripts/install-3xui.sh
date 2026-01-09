#!/bin/bash
set -e

echo "=== Installing 3X-UI v2.8.7 ==="

# Update system
echo "1. Updating system..."
apt-get update
apt-get upgrade -y

# Install dependencies
echo "2. Installing dependencies..."
apt-get install -y curl wget git

# Download and install 3x-ui
echo "3. Installing 3X-UI v2.8.7..."
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh) v2.8.7

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Access panel: http://YOUR_SERVER_IP:2053"
echo "2. Default login: admin / admin"
echo "3. Change password immediately!"
echo ""
