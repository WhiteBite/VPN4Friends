#!/bin/bash
# Скрипт первоначальной настройки сервера для VPN бота
# Запускать на сервере: bash setup-server.sh

set -e

BOT_DIR="/opt/vpn4friends"
REPO_URL="https://github.com/YOUR_USERNAME/YOUR_REPO.git"

echo "=== vpn4friends Server Setup ==="

# Установка Docker если нет
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
fi

# Установка Docker Compose если нет
if ! command -v docker compose &> /dev/null; then
    echo "Installing Docker Compose..."
    apt-get update && apt-get install -y docker-compose-plugin
fi

# Клонирование репозитория
if [ ! -d "$BOT_DIR" ]; then
    echo "Cloning repository..."
    git clone "$REPO_URL" "$BOT_DIR"
else
    echo "Repository already exists, pulling latest..."
    cd "$BOT_DIR" && git pull
fi

cd "$BOT_DIR"

# Создание .env если нет
if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    echo ""
    echo "!!! IMPORTANT: Edit .env file with your settings !!!"
    echo "nano $BOT_DIR/.env"
    echo ""
fi

# Создание директорий
mkdir -p data logs

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "1. Edit .env file: nano $BOT_DIR/.env"
echo "2. Start bot: cd $BOT_DIR && docker compose up -d vpn-bot"
echo "3. Check logs: docker logs -f vpn-bot"
