#!/bin/bash
set -e

echo "=== Configuring Reality VPN ==="
echo ""

# Generate Reality keypair
echo "1. Generating Reality keypair..."
KEYS=$(docker exec 3x-ui /app/bin/xray-linux-amd64 x25519)
PRIVATE_KEY=$(echo "$KEYS" | grep "PrivateKey:" | awk '{print $2}')
PUBLIC_KEY=$(echo "$KEYS" | grep "Password:" | awk '{print $2}')

echo ""
echo "✅ Generated keys:"
echo "Private Key: $PRIVATE_KEY"
echo "Public Key:  $PUBLIC_KEY"
echo ""

# Generate short IDs
SHORT_ID1=$(openssl rand -hex 8)
SHORT_ID2=$(openssl rand -hex 3)

echo "✅ Generated Short IDs:"
echo "Short ID 1: $SHORT_ID1"
echo "Short ID 2: $SHORT_ID2"
echo ""

# Save configuration
cat > /root/reality-config.env << EOF
# Reality VPN Configuration
# Generated: $(date)
# Server: 185.23.238.162

REALITY_PRIVATE_KEY=$PRIVATE_KEY
REALITY_PUBLIC_KEY=$PUBLIC_KEY
REALITY_SHORT_ID_1=$SHORT_ID1
REALITY_SHORT_ID_2=$SHORT_ID2
REALITY_SNI=google.com
REALITY_FINGERPRINT=chrome
REALITY_SPIDER_X=/
REALITY_FLOW=xtls-rprx-vision
EOF

echo "✅ Configuration saved to /root/reality-config.env"
echo ""
echo "=== Manual Steps Required ==="
echo ""
echo "1. Open 3X-UI panel: http://185.23.238.162:2053"
echo "2. Login: admin / admin (change password!)"
echo "3. Go to: Inbounds → Add Inbound"
echo ""
echo "4. Configure inbound:"
echo "   Protocol: VLESS"
echo "   Port: 443"
echo "   Network: TCP"
echo "   Security: Reality"
echo ""
echo "5. Reality Settings:"
echo "   Private Key: $PRIVATE_KEY"
echo "   Public Key: $PUBLIC_KEY"
echo "   Short IDs: $SHORT_ID1,$SHORT_ID2"
echo "   Dest (SNI): google.com:443"
echo "   Server Names: google.com"
echo "   Fingerprint: chrome"
echo "   Spider X: /"
echo ""
echo "6. Flow Control:"
echo "   Flow: xtls-rprx-vision"
echo ""
echo "7. Add clients and test connection"
echo ""
