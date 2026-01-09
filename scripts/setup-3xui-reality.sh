#!/bin/bash
set -e

echo "=== Setting up 3X-UI Reality VPN ==="

# Generate Reality keypair
echo "1. Generating Reality keypair..."
KEYS=$(docker exec 3x-ui /app/bin/xray-linux-amd64 x25519)
PRIVATE_KEY=$(echo "$KEYS" | grep "PrivateKey:" | awk '{print $2}')
PUBLIC_KEY=$(echo "$KEYS" | grep "Password:" | awk '{print $2}')

echo ""
echo "Generated keys:"
echo "Private Key: $PRIVATE_KEY"
echo "Public Key:  $PUBLIC_KEY"
echo ""

# Generate short IDs
SHORT_ID1=$(openssl rand -hex 8)
SHORT_ID2=$(openssl rand -hex 3)

echo "Generated Short IDs:"
echo "Short ID 1: $SHORT_ID1"
echo "Short ID 2: $SHORT_ID2"
echo ""

# Save to file for later use
cat > /root/reality-keys.txt <<EOF
# Reality VPN Configuration
# Generated: $(date)

PRIVATE_KEY=$PRIVATE_KEY
PUBLIC_KEY=$PUBLIC_KEY
SHORT_ID_1=$SHORT_ID1
SHORT_ID_2=$SHORT_ID2

# Recommended settings:
SNI=google.com
FINGERPRINT=chrome
SPIDER_X=/
FLOW=xtls-rprx-vision
EOF

echo "✅ Keys saved to /root/reality-keys.txt"
echo ""
echo "=== Manual Configuration Required ==="
echo ""
echo "1. Open 3X-UI panel: http://YOUR_SERVER_IP:2053"
echo "2. Go to Inbounds → Add Inbound"
echo "3. Configure:"
echo "   - Protocol: VLESS"
echo "   - Port: 443"
echo "   - Network: TCP"
echo "   - Security: Reality"
echo "   - Private Key: $PRIVATE_KEY"
echo "   - Public Key: $PUBLIC_KEY"
echo "   - Short IDs: $SHORT_ID1, $SHORT_ID2"
echo "   - SNI: google.com"
echo "   - Fingerprint: chrome"
echo "   - Spider X: /"
echo "   - Flow: xtls-rprx-vision"
echo ""
echo "4. Add clients through the panel"
echo ""
