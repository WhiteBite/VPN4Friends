#!/bin/bash
set -e

# Apply database migrations
echo "Applying database migrations..."
python -m alembic upgrade head

echo "Starting Telegram bot..."
exec python -m src.bot.app
