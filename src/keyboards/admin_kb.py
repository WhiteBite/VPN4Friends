"""Admin keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.models import User, VPNRequest
from src.keyboards.callbacks import RequestAction, UserAction


def get_admin_main_kb() -> InlineKeyboardMarkup:
    """Get main admin panel keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Заявки", callback_data="admin_requests")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="✉️ Написать юзеру", callback_data="admin_dm")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="🔔 Уведомить об обновлении", callback_data="admin_notify_update")
    builder.button(text="❌ Закрыть", callback_data="close_admin")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def get_request_action_kb(request: VPNRequest) -> InlineKeyboardMarkup:
    """Get action keyboard for VPN request."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Одобрить",
        callback_data=RequestAction(action="approve", request_id=request.id).pack(),
    )
    builder.button(
        text="❌ Отклонить",
        callback_data=RequestAction(action="reject", request_id=request.id).pack(),
    )
    builder.adjust(2)
    return builder.as_markup()


def get_user_manage_kb(user: User) -> InlineKeyboardMarkup:
    """Get management keyboard for user."""
    builder = InlineKeyboardBuilder()

    if user.has_vpn:
        builder.button(
            text="📊 Статистика",
            callback_data=UserAction(action="stats", user_id=user.id).pack(),
        )
        builder.button(
            text="🗑️ Отозвать VPN",
            callback_data=UserAction(action="revoke", user_id=user.id).pack(),
        )
        builder.adjust(2)

    builder.button(text="⬅️ К списку", callback_data="admin_users")
    return builder.as_markup()


def get_back_to_admin_kb() -> InlineKeyboardMarkup:
    """Get back to admin panel keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Админ-панель", callback_data="admin_menu")
    return builder.as_markup()
