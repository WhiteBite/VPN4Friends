#!/bin/bash
set -e

# Apply database migrations
echo "Applying database migrations..."
python -m alembic upgrade head

# Start the FastAPI server in the background, redirecting logs
echo "Starting FastAPI server..."
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > /app/data/api.log 2>&1 &

# Start the bot in the foreground
echo "Starting Telegram bot..."
python -m src.bot.app
