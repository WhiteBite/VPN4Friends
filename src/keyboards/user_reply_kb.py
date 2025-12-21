"""Keyboard for user to reply to admin."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_reply_to_admin_kb() -> InlineKeyboardMarkup:
    """Get keyboard for user to reply to admin message."""
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Ответить", callback_data="contact_admin")
    builder.button(text="🏠 Меню", callback_data="back_to_menu")
    builder.adjust(2)
    return builder.as_markup()
