"""User keyboards."""

from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.config import settings


def get_user_main_kb(has_vpn: bool, has_pending: bool = False) -> InlineKeyboardMarkup:
    """Get main keyboard for user based on their status.

    - has_vpn: Cabinet + How-to + Support
    - has_pending: Cabinet + Pending (with date) + Cancel
    - new: Cabinet (request VPN inside)
    """
    builder = InlineKeyboardBuilder()

    if has_vpn:
        if settings.miniapp_url:
            builder.button(
                text="🔵 Открыть Кабинет",
                web_app=WebAppInfo(url=settings.miniapp_url),
            )
        builder.button(text="🔗 Показать VPN ссылку", callback_data="show_my_vpn")
        builder.button(text="📱 Как подключиться?", callback_data="how_to_connect")
        builder.button(text="💬 Поддержка", callback_data="contact_admin")
        builder.adjust(1, 1, 2)
    elif has_pending:
        if settings.miniapp_url:
            builder.button(
                text="🔵 Открыть Кабинет",
                web_app=WebAppInfo(url=settings.miniapp_url),
            )
        builder.button(text="⏳ Заявка на рассмотрении", callback_data="pending_info")
        builder.button(text="❌ Отменить заявку", callback_data="cancel_request")
        builder.adjust(1, 1, 1)
    else:
        if settings.miniapp_url:
            builder.button(
                text="🔵 Запросить доступ",
                web_app=WebAppInfo(url=settings.miniapp_url),
            )
        builder.button(text="🔑 Попросить VPN тут", callback_data="request_vpn")
        builder.adjust(1, 1)

    # Always add a switch button for Bot Mode users to go to Mini App
    builder.row(
        InlineKeyboardBuilder()
        .button(text="🚀 Перейти в Mini App", callback_data="set_ui_mode:miniapp")
        .as_button()
    )

    return builder.as_markup()


def get_approval_onboarding_kb() -> InlineKeyboardMarkup:
    """Post-approval keyboard with cabinet + app download links."""
    builder = InlineKeyboardBuilder()

    if settings.miniapp_url:
        builder.button(
            text="🔵 Открыть Кабинет",
            web_app=WebAppInfo(url=settings.miniapp_url),
        )

    builder.button(
        text="🍏 V2RayTun (iPhone)",
        url="https://apps.apple.com/app/v2raytun/id6476628951",
    )
    builder.button(
        text="🤖 v2rayNG (Android)",
        url="https://play.google.com/store/apps/details?id=com.v2ray.ang",
    )
    builder.button(
        text="💻 Hiddify (PC/Mac)",
        url="https://github.com/hiddify/hiddify-app/releases",
    )

    builder.adjust(1, 2, 1)
    return builder.as_markup()


def get_back_kb() -> InlineKeyboardMarkup:
    """Get back to menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Меню", callback_data="back_to_menu")
    return builder.as_markup()


def get_ui_selection_kb() -> InlineKeyboardMarkup:
    """Get keyboard for first-time UI mode selection."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🚀 Mini App (Рекомендуется)",
        callback_data="set_ui_mode:miniapp",
    )
    builder.button(
        text="🤖 Чат-бот (Классика)",
        callback_data="set_ui_mode:bot",
    )
    builder.button(
        text="🌐 Браузер (Без Telegram)",
        url="https://vpn4friends.ru/app",
    )

    builder.adjust(1, 1, 1)
    return builder.as_markup()


def get_confirm_delete_kb() -> InlineKeyboardMarkup:
    """Create a confirmation keyboard for VPN profile deletion."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data="confirm_delete_vpn")
    builder.button(text="❌ Отмена", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()
