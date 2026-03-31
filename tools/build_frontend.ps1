# VPN4Friends Mini App Build Script (PowerShell)
# This script ensures the frontend is built correctly before deployment

$ErrorActionPreference = "Stop"

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptDir\..\miniapp"

Write-Host "🚀 Building VPN4Friends Mini App..." -ForegroundColor Cyan

# Check for node_modules
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# Run build
npm run build

Write-Host "✅ Build completed! The 'dist' folder is ready." -ForegroundColor Green
Write-Host "🔔 Reminder: Restart your Docker containers to apply changes if using volumes." -ForegroundColor White
