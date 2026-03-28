"""User keyboards."""

import os

from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.config import settings

# MTProto settings (loaded directly from env vars)
MTPROTO_HOST = os.getenv("MTPROTO_PROXY_HOST", settings.mtproto_proxy_host)
MTPROTO_PORT = os.getenv("MTPROTO_PROXY_PORT", str(settings.mtproto_proxy_port))
MTPROTO_SECRET = os.getenv("MTPROTO_PROXY_SECRET", settings.mtproto_proxy_secret)


def get_user_main_kb(has_vpn: bool, has_pending: bool = False) -> InlineKeyboardMarkup:
    """Get main keyboard for user based on their status."""
    builder = InlineKeyboardBuilder()

    if has_vpn:
        # User clicks this to see all available VPN options (VLESS nodes, MTProto, etc)
        builder.button(text="🔗 Мой VPN", callback_data="my_link")
        builder.button(text="📊 Статистика", callback_data="my_stats")

        if settings.miniapp_url:
            builder.button(
                text="⚙️ Настройки",
                web_app=WebAppInfo(url=settings.miniapp_url),
            )
        builder.button(text="✉️ Написать Дане", callback_data="contact_admin")
        builder.adjust(2, 1, 1)
    elif has_pending:
        builder.button(text="⏳ Заявка на рассмотрении", callback_data="pending_info")
        if settings.miniapp_url:
            builder.button(
                text="🚀 Мой Кабинет",
                web_app=WebAppInfo(url=settings.miniapp_url),
            )
        builder.button(text="✉️ Написать Дане", callback_data="contact_admin")
        builder.adjust(1, 1, 1)
    else:
        builder.button(text="🔑 Попросить VPN", callback_data="request_vpn")
        if settings.miniapp_url:
            builder.button(
                text="🚀 Открыть Приложение",
                web_app=WebAppInfo(url=settings.miniapp_url),
            )
        builder.adjust(1, 1)

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


def get_link_kb(endpoint_name: str | None = None) -> InlineKeyboardMarkup:
    """Get keyboard for link page."""
    builder = InlineKeyboardBuilder()

    refresh_data = f"refresh_link:{endpoint_name}" if endpoint_name else "refresh_link:default"
    builder.button(text="🔄 Обновить", callback_data=refresh_data)

    builder.button(text="🏠 Меню", callback_data="back_to_menu_new")
    if settings.miniapp_url:
        builder.button(
            text="⚙️ Настройки",
            web_app=WebAppInfo(url=settings.miniapp_url),
        )
    builder.adjust(2, 1)
    return builder.as_markup()


def get_locations_kb() -> InlineKeyboardMarkup:
    """Get keyboard with all available server locations."""
    builder = InlineKeyboardBuilder()

    for endpoint in settings.endpoints:
        builder.button(
            text=endpoint.label,
            callback_data=f"get_link:{endpoint.name}",
        )

    # We construct the MTProto proxy link button inside user.py, or we can just make it part of endpoints if it has name="finland_mtproto" etc.
    # Since MTProto endpoints are already in settings.endpoints, the loop above naturally handles them!

    builder.button(text="⬅️ Опции и другие протоколы", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()
