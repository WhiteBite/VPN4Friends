"""Keyboards for visual onboarding."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_onboarding_kb() -> InlineKeyboardMarkup:
    """Get keyboard for choosing platform-specific instructions."""
    builder = InlineKeyboardBuilder()

    builder.button(text="🍏 iPhone (V2RayTun)", callback_data="how_to_iphone")
    builder.button(text="🤖 Android (v2rayNG)", callback_data="how_to_android")
    builder.button(text="💻 Desktop / Mac (Hiddify)", callback_data="how_to_desktop")

    builder.button(text="⬅️ Назад в меню", callback_data="back_to_menu")

    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()


def get_iphone_onboarding_kb() -> InlineKeyboardMarkup:
    """Get navigation for iPhone instructions."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📥 Скачать V2RayTun", url="https://apps.apple.com/app/v2raytun/id6476628951"
    )
    builder.button(text="⬅️ Другой выбор", callback_data="how_to_connect")
    builder.adjust(1)
    return builder.as_markup()


def get_android_onboarding_kb() -> InlineKeyboardMarkup:
    """Get navigation for Android instructions."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📥 Скачать v2rayNG", url="https://play.google.com/store/apps/details?id=com.v2ray.ang"
    )
    builder.button(text="⬅️ Другой выбор", callback_data="how_to_connect")
    builder.adjust(1)
    return builder.as_markup()
