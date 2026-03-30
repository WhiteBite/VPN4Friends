#!/bin/bash
# 🚀 Remote Deployment Script for VPN4Friends
# This script is designed to run on the production server (Ubuntu).

set -e

PROJECT_ROOT="/home/ubuntu/VPN4Friends"
CONFIG_FILE="$PROJECT_ROOT/vpn-config.json"
ENV_FILE="$PROJECT_ROOT/.env"

cd "$PROJECT_ROOT"

echo "📥 Verifying dependencies (jq)..."
if ! command -v jq &> /dev/null; then
  sudo apt-get update && sudo apt-get install -y jq
fi

echo "🔐 Generating .env from local vpn-config.json..."
if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ Error: vpn-config.json not found in $PROJECT_ROOT"
  exit 1
fi

# Replicate the logic from ci.yml to generate .env
# We use the current vpn-config.json as the source of truth
cat "$CONFIG_FILE" | jq -r '
  # Bot
  "BOT_TOKEN=\(.bot.token)",
  "ADMIN_IDS=\(.bot.admin_ids | join(","))",
  "MINIAPP_URL=\(.bot.miniapp_url // "")",
  
  # API Public Domain
  "API_PUBLIC_DOMAIN=vpn4friends-api.whitebite.ru",
  
  # Finland Panel
  "XUI_FINLAND_URL=\(.servers.finland.panel_url)",
  "XUI_FINLAND_LOGIN=\(.servers.finland.login)",
  "XUI_FINLAND_PASSWORD=\(.servers.finland.password)",
  "XUI_FINLAND_PORT=9211",
  "XUI_API_URL=\(.servers.finland.panel_url)",
  "XUI_USERNAME=\(.servers.finland.login)",
  "XUI_PASSWORD=\(.servers.finland.password)",
  "XUI_HOST=\(.servers.finland.ip)",
  
  # Reality
  "REALITY_UUID=\(.reality.uuid)",
  "REALITY_PRIVATE_KEY=\(.reality.private_key)",
  "REALITY_PUBLIC_KEY=\(.reality.public_key)",
  "REALITY_SHORT_ID=\(.reality.short_id)",
  
  # MTProto
  "MTPROTO_PROXY_HOST=\(.mtproto.finland.host)",
  "MTPROTO_PROXY_PORT=\(.mtproto.finland.port)",
  "MTPROTO_PROXY_SECRET=\(.mtproto.finland.secret)",
  
  # Endpoints (JSON array)
  "ENDPOINTS_CONFIG=\(.endpoints | @json)",
  
  # Nodes topology
  "NODES_CONFIG_RAW=\(.nodes // {} | @json)",
  
  # Database
  "DATABASE_URL=sqlite+aiosqlite:////app/data/vpn_bot.db"
' > "$ENV_FILE"

# Keep essential secrets if they already exist, otherwise use placeholders
# (In a real scenario, you might want to preserve them better)
grep "CLOUDFLARE_TUNNEL_TOKEN=" "$ENV_FILE.bak" >> "$ENV_FILE" 2>/dev/null || true
grep "JWT_SECRET=" "$ENV_FILE.bak" >> "$ENV_FILE" 2>/dev/null || true

echo "🏗 Building Mini App..."
docker run --rm -v $(pwd)/miniapp:/app -w /app node:20-alpine sh -c "
  npm install && \
  VITE_API_BASE_URL=/api npm run build
"

echo "🐳 Building and restarting containers..."
docker compose up -d --build

echo "🧹 Cleaning up images..."
docker image prune -f

echo "✅ Deployment complete on $(hostname)!"
