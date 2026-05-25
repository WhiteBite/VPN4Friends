"""Keyboards for messaging functionality."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_broadcast_target_kb() -> InlineKeyboardMarkup:
    """Get keyboard for selecting broadcast target."""
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Всем", callback_data="broadcast_all")
    builder.button(text="🔑 С VPN", callback_data="broadcast_vpn")
    builder.button(text="🚫 Без VPN", callback_data="broadcast_no_vpn")
    builder.button(text="📡 Конфиги VPN-юзерам", callback_data="broadcast_configs")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(3, 1, 1)
    return builder.as_markup()


def get_cancel_kb() -> InlineKeyboardMarkup:
    """Get cancel keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    return builder.as_markup()


def get_contact_admin_kb(user_id: int) -> InlineKeyboardMarkup:
    """Get keyboard for admin to reply to user."""
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Ответить", callback_data=f"reply_to_{user_id}")
    return builder.as_markup()


def get_continue_chat_kb(user_id: int) -> InlineKeyboardMarkup:
    """Get keyboard to continue chat with user."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Написать ещё", callback_data=f"reply_to_{user_id}")
    return builder.as_markup()


def get_broadcast_confirm_kb() -> InlineKeyboardMarkup:
    """Get keyboard to confirm or cancel broadcast."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data="broadcast_confirm")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(2)
    return builder.as_markup()
