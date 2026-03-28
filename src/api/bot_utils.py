"""Shared Telegram Bot utilities for the API layer.

Provides a context manager to safely create and dispose of Bot instances
without leaking aiohttp sessions.
"""

import contextlib
import logging
from collections.abc import AsyncIterator

from src.bot.config import settings

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def create_bot() -> AsyncIterator:
    """Context manager that creates a Bot and ensures its session is closed.

    Usage::

        async with create_bot() as bot:
            await bot.send_message(chat_id, text)
    """
    from aiogram import Bot

    bot = Bot(token=settings.bot_token)
    try:
        yield bot
    finally:
        await bot.session.close()


async def notify_admins(text: str, **kwargs) -> int:
    """Send a message to all configured admin IDs.

    Returns the number of successfully delivered messages.
    """
    if not settings.admin_ids:
        return 0

    sent = 0
    async with create_bot() as bot:
        for admin_id in settings.admin_ids:
            with contextlib.suppress(Exception):
                await bot.send_message(admin_id, text, **kwargs)
                sent += 1
    return sent


async def notify_user(telegram_id: int, text: str, **kwargs) -> bool:
    """Send a message to a specific user. Returns True on success."""
    try:
        async with create_bot() as bot:
            await bot.send_message(telegram_id, text, **kwargs)
        return True
    except Exception as e:
        logger.warning(f"Failed to notify user {telegram_id}: {e}")
        return False
