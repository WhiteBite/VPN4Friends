"""User keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_user_main_kb(has_vpn: bool, has_pending: bool = False) -> InlineKeyboardMarkup:
    """Get main keyboard for user based on their status."""
    builder = InlineKeyboardBuilder()

    if has_vpn:
        builder.button(text="🔗 Моя ссылка", callback_data="my_link")
        builder.button(text="📊 Статистика", callback_data="my_stats")
        builder.button(text="✉️ Написать Дане", callback_data="contact_admin")
        builder.button(text="❌ Удалить VPN", callback_data="delete_vpn")
        builder.adjust(2, 2)
    elif has_pending:
        builder.button(text="⏳ Заявка на рассмотрении", callback_data="pending_info")
        builder.button(text="✉️ Написать Дане", callback_data="contact_admin")
        builder.adjust(1)
    else:
        builder.button(text="🔑 Попросить VPN у Дани", callback_data="request_vpn")
        builder.button(text="✉️ Написать Дане", callback_data="contact_admin")
        builder.adjust(1)

    return builder.as_markup()


def get_back_kb() -> InlineKeyboardMarkup:
    """Get back to menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    return builder.as_markup()


def get_stats_kb() -> InlineKeyboardMarkup:
    """Get keyboard for stats page with refresh button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="refresh_stats")
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    builder.adjust(2)
    return builder.as_markup()


def get_confirm_delete_kb() -> InlineKeyboardMarkup:
    """Get confirmation keyboard for VPN deletion."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data="confirm_delete_vpn")
    builder.button(text="❌ Отмена", callback_data="back_to_menu")
    builder.adjust(2)
    return builder.as_markup()


def get_link_kb() -> InlineKeyboardMarkup:
    """Get keyboard for link page with refresh and menu buttons."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить ссылку", callback_data="refresh_link")
    builder.button(text="🏠 Меню", callback_data="back_to_menu_new")
    builder.adjust(1)
    return builder.as_markup()
