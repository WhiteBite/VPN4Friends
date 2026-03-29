"""Messaging utilities for handling Telegram message limits."""

import logging

from aiogram.types import InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000  # Leave some buffer from 4096


async def send_smart_message(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
    **kwargs,
) -> None:
    """Send long message by splitting it into smaller chunks."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode, **kwargs)
        return

    # Split logic
    chunks = []
    while text:
        if len(text) <= MAX_MESSAGE_LENGTH:
            chunks.append(text)
            break

        # Try to find the best split point (newline or space)
        split_at = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = text.rfind(" ", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = MAX_MESSAGE_LENGTH

        chunks.append(text[:split_at])
        text = text[split_at:].strip()

    # Send chunks
    for i, chunk in enumerate(chunks):
        # Only add the keyboard to the VERY last chunk
        markup = reply_markup if i == len(chunks) - 1 else None
        try:
            await message.answer(chunk, reply_markup=markup, parse_mode=parse_mode, **kwargs)
        except Exception as e:
            logger.error(f"Failed to send chunk: {e}")
            # Fallback for broken HTML tags in chunks
            await message.answer(chunk, reply_markup=markup, parse_mode=None)
