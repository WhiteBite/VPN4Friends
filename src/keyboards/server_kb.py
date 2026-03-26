"""Server selection keyboard for VPN bot."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.config import settings


def get_server_list_kb() -> InlineKeyboardMarkup:
    """Get keyboard with all available servers."""
    builder = InlineKeyboardBuilder()

    # Group endpoints by region
    # Use getattr for protocol since it's optional
    finland_endpoints = [
        ep
        for ep in settings.endpoints
        if "finland" in ep.name.lower() and getattr(ep, "protocol", "vless") != "mtproto"
    ]
    nl_endpoints = [
        ep
        for ep in settings.endpoints
        if "nether" in ep.name.lower()
        or "germany" in ep.name.lower()
        and getattr(ep, "protocol", "vless") != "mtproto"
    ]
    mtproto_endpoints = [
        ep for ep in settings.endpoints if getattr(ep, "protocol", None) == "mtproto"
    ]

    # Finland section
    if finland_endpoints:
        builder.button(text="🇫🇮 Финляндия", callback_data="region_finland")

    # Netherlands/Germany section
    if nl_endpoints:
        builder.button(text="🇩🇪 Германия", callback_data="region_netherlands")

    # MTProto section
    if mtproto_endpoints:
        builder.button(text="✈️ Telegram Proxy", callback_data="region_mtproto")

    builder.adjust(1)
    return builder.as_markup()


def get_finland_options_kb() -> InlineKeyboardMarkup:
    """Get keyboard with Finland connection options."""
    builder = InlineKeyboardBuilder()

    # xHTTP via Moscow (recommended)
    builder.button(text="⚡ xHTTP (via Moscow) ⭐", callback_data="endpoint_finland_xhttp")

    # gRPC via Moscow
    builder.button(text="📦 gRPC (via Moscow)", callback_data="endpoint_finland_grpc")

    # Direct
    builder.button(text="🔗 Direct", callback_data="endpoint_finland_direct")

    builder.button(text="⬅️ Назад", callback_data="back_to_servers")
    builder.adjust(1)
    return builder.as_markup()


def get_netherlands_options_kb() -> InlineKeyboardMarkup:
    """Get keyboard with Netherlands connection options."""
    builder = InlineKeyboardBuilder()

    # Direct
    builder.button(text="🔗 Direct", callback_data="endpoint_netherlands_direct")

    # Via Moscow (if configured)
    builder.button(text="📍 Via Moscow", callback_data="endpoint_netherlands_via_moscow")

    builder.button(text="⬅️ Назад", callback_data="back_to_servers")
    builder.adjust(1)
    return builder.as_markup()


def get_mtproto_options_kb() -> InlineKeyboardMarkup:
    """Get keyboard with MTProto options."""
    builder = InlineKeyboardBuilder()

    mtproto_endpoints = [
        ep for ep in settings.endpoints if getattr(ep, "protocol", None) == "mtproto"
    ]

    for endpoint in mtproto_endpoints:
        flag = "🇫🇮" if "finland" in endpoint.name.lower() else "🇩🇪"
        builder.button(text=f"{flag} {endpoint.label}", callback_data=f"endpoint_{endpoint.name}")

    builder.button(text="⬅️ Назад", callback_data="back_to_servers")
    builder.adjust(1)
    return builder.as_markup()


def get_back_to_servers_kb() -> InlineKeyboardMarkup:
    """Get back to server selection keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 Все серверы", callback_data="back_to_servers")
    return builder.as_markup()
