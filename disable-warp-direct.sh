#!/bin/bash
# Disable WARP and use direct outbound for 3x-ui
# Run on 62Yun server

set -e

echo "=== Disabling WARP, enabling direct outbound ==="
echo ""

CONTAINER="3x-ui"
CONFIG_FILE="/app/bin/config.json"

# Backup current config
echo "[1/4] Backing up current config..."
docker exec $CONTAINER cp $CONFIG_FILE ${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"
echo ""

# Check current outbounds
echo "[2/4] Current outbounds:"
docker exec $CONTAINER python3 -c "
import json
with open('$CONFIG_FILE') as f:
    config = json.load(f)
    outbounds = config.get('outbounds', [])
    for i, ob in enumerate(outbounds):
        print(f\"  {i}. {ob.get('tag')}: {ob.get('protocol')}\")
"
echo ""

# Modify config to use direct as default
echo "[3/4] Modifying config to use direct outbound..."
docker exec $CONTAINER python3 << 'PYTHON'
import json

config_file = "/app/bin/config.json"

with open(config_file, 'r') as f:
    config = json.load(f)

# Find and modify routing rules
routing = config.get('routing', {})
rules = routing.get('rules', [])

# Ensure first rule uses 'direct' for non-blocked traffic
new_rules = []
for rule in rules:
    if rule.get('outboundTag') == 'warp':
        rule['outboundTag'] = 'direct'
    new_rules.append(rule)

# Add default direct rule if not exists
has_default = any(rule.get('type') == 'field' and not rule.get('outboundTag') for rule in rules)
if not has_default:
    new_rules.append({
        "type": "field",
        "network": "tcp,udp",
        "outboundTag": "direct"
    })

routing['rules'] = new_rules
config['routing'] = routing

# Remove WARP outbound if exists (optional - keep it for fallback)
# outbounds = [ob for ob in config['outbounds'] if ob.get('tag') != 'warp']
# config['outbounds'] = outbounds

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print("✅ Config updated - WARP replaced with direct")
PYTHON
echo ""

# Restart 3x-ui
echo "[4/4] Restarting 3x-ui container..."
docker restart $CONTAINER
sleep 5
echo "✅ 3x-ui restarted"
echo ""

# Verify
echo "=== Verification ==="
docker logs $CONTAINER 2>&1 | grep -E "started|error" | tail -5
echo ""

echo "=== Test your speed now ==="
echo "Use speedtest website or app"
echo ""
echo "Expected improvement: 10-100x faster"
echo ""
