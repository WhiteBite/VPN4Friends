#!/bin/bash
# VPN4Friends Mini App Build Script
# This script ensures the frontend is built correctly before deployment

set -e

# Change to miniapp directory
cd "$(dirname "$0")/../miniapp"

echo "🚀 Building VPN4Friends Mini App..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run build
npm run build

echo "✅ Build completed! The 'dist' folder is ready."
echo "🔔 Reminder: Restart your Docker containers to apply changes if using volumes."
