"""User keyboards."""

from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.config import settings


def get_user_main_kb(has_vpn: bool, has_pending: bool = False) -> InlineKeyboardMarkup:
    """Get main keyboard for user based on their status."""
    builder = InlineKeyboardBuilder()

    if has_vpn:
        builder.button(text="🔗 Моя ссылка", callback_data="my_link")
        builder.button(text="📊 Статистика", callback_data="my_stats")
        builder.button(text="🌐 Выбрать сервер", callback_data="choose_server")
        # MTProto Proxy button for Telegram
        mtproto_link = (
            f"tg://proxy?server={settings.mtproto_proxy_host}"
            f"&port={settings.mtproto_proxy_port}"
            f"&secret={settings.mtproto_proxy_secret}"
        )
        builder.button(text="📡 Telegram Proxy", url=mtproto_link)
        if settings.miniapp_url:
            builder.button(
                text="⚙️ Настройки",
                web_app=WebAppInfo(url=settings.miniapp_url),
            )
        builder.button(text="✉️ Написать Дане", callback_data="contact_admin")
        builder.adjust(2, 1, 1, 2)
    elif has_pending:
        builder.button(text="⏳ Заявка на рассмотрении", callback_data="pending_info")
        builder.button(text="✉️ Написать Дане", callback_data="contact_admin")
        builder.adjust(1, 1)
    else:
        builder.button(text="🔑 Попросить VPN", callback_data="request_vpn")
        builder.adjust(1)

    return builder.as_markup()


def get_back_kb() -> InlineKeyboardMarkup:
    """Get back to menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Меню", callback_data="back_to_menu")
    return builder.as_markup()


def get_stats_kb() -> InlineKeyboardMarkup:
    """Get keyboard for stats page with refresh button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="refresh_stats")
    builder.button(text="⬅️ Меню", callback_data="back_to_menu")
    builder.adjust(2)
    return builder.as_markup()


def get_confirm_delete_kb() -> InlineKeyboardMarkup:
    """Get confirmation keyboard for VPN deletion."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data="confirm_delete_vpn")
    builder.button(text="❌ Нет", callback_data="back_to_menu")
    builder.adjust(2)
    return builder.as_markup()


def get_link_kb() -> InlineKeyboardMarkup:
    """Get keyboard for link page."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="refresh_link")
    builder.button(text="🏠 Меню", callback_data="back_to_menu_new")
    if settings.miniapp_url:
        builder.button(
            text="⚙️ Настройки",
            web_app=WebAppInfo(url=settings.miniapp_url),
        )
    builder.adjust(2, 1)
    return builder.as_markup()
