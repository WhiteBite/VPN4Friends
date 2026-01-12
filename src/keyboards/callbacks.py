"""Callback data classes for inline keyboards."""

from aiogram.filters.callback_data import CallbackData


class RequestAction(CallbackData, prefix="req"):
    """Callback data for VPN request actions."""

    action: str  # approve / reject / select_protocol
    request_id: int
    protocol_name: str | None = None


class UserAction(CallbackData, prefix="user"):
    """Callback data for user management actions."""

    action: str  # revoke / stats
    user_id: int
