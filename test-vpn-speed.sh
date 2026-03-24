#!/bin/bash
# VPN Speed Test and Optimization Script
# Run on 62Yun server: curl -sS [URL_REMOVED] | bash

set -e

echo "=== VPN Speed Test & Optimization ==="
echo ""

# Test 1: Server speed test
echo "[1/4] Testing server internet speed..."
if command -v speedtest &> /dev/null; then
    speedtest --simple
elif command -v speedtest-cli &> /dev/null; then
    speedtest-cli --simple
else
    curl -s https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py | python3 -
fi
echo ""

# Test 2: Check if WARP is being used
echo "[2/4] Checking outbound configuration..."
if docker ps | grep -q 3x-ui; then
    WARP_USED=$(docker exec 3x-ui cat /app/bin/config.json 2>/dev/null | grep -c '"tag": "warp"' || echo "0")
    if [ "$WARP_USED" -gt 0 ]; then
        echo "⚠️  WARNING: WARP outbound is configured!"
        echo "    This may slow down your connection."
        echo "    Consider using 'direct' outbound instead."
    else
        echo "✅ No WARP outbound detected"
    fi
else
    echo "⚠️  3x-ui container not found"
fi
echo ""

# Test 3: Check CPU/RAM
echo "[3/4] System resources..."
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4 "% used"}'
echo "RAM Usage:"
free -m | awk 'NR==2{printf "%sMB used (%.1f%%)\n", $3, $3*100/$2}'
echo ""

# Test 4: Check active connections
echo "[4/4] Active VPN connections..."
if docker ps | grep -q 3x-ui; then
    CONN_COUNT=$(docker exec 3x-ui ss -tnp 2>/dev/null | grep -c ESTAB || echo "0")
    echo "Active connections: $CONN_COUNT"
else
    echo "3x-ui not running"
fi
echo ""

# Optimization recommendations
echo "=== Recommendations ==="
echo ""

# Check Reality config
if docker ps | grep -q 3x-ui; then
    REALITY_CONFIG=$(docker exec 3x-ui cat /app/bin/config.json 2>/dev/null | grep -c '"realitySettings"' || echo "0")
    if [ "$REALITY_CONFIG" -gt 0 ]; then
        echo "✅ Reality protocol is configured"
        echo "   Verify serverName matches your config (should be: speed.cloudflare.com)"
    fi
    
    # Check for gRPC deprecation warning
    GRPC_WARNING=$(docker logs 3x-ui 2>&1 | grep -c "gRPC.*deprecated" || echo "0")
    if [ "$GRPC_WARNING" -gt 0 ]; then
        echo "⚠️  gRPC transport is deprecated"
        echo "   Consider switching to VLESS+TCP+Reality"
    fi
fi

echo ""
echo "=== Quick Fixes ==="
echo ""
echo "1. Restart 3x-ui container:"
echo "   docker restart 3x-ui"
echo ""
echo "2. Check 3x-ui logs:"
echo "   docker logs 3x-ui | tail -50"
echo ""
echo "3. Test different protocol (Shadowsocks vs VLESS)"
echo ""
echo "4. Verify client config matches server Reality settings"
echo ""

echo "=== Expected Speeds ==="
echo "VPS with 1 Gbps port should give:"
echo "  Download: 100-500 Mbps"
echo "  Upload: 100-500 Mbps"
echo "  Ping: 30-80 ms"
echo ""
echo "Your reported speed: 2.44 Mbps down ❌"
echo ""
