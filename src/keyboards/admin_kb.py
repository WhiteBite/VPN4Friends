"""Admin keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.models import User, VPNRequest
from src.keyboards.callbacks import AdminPage, RequestAction, UserAction

USERS_PER_PAGE = 5


def get_admin_main_kb(pending_count: int = 0, vpn_count: int = 0) -> InlineKeyboardMarkup:
    """Get main admin panel keyboard with counters."""
    builder = InlineKeyboardBuilder()

    req_label = f"📋 Заявки ({pending_count})" if pending_count else "📋 Заявки"
    usr_label = f"👥 Юзеры ({vpn_count})" if vpn_count else "👥 Юзеры"

    builder.button(text=req_label, callback_data="admin_requests")
    builder.button(text=usr_label, callback_data="admin_users")
    builder.button(text="📊 Дашборд", callback_data="admin_dashboard")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="✉️ Написать", callback_data="admin_dm")
    builder.button(text="❌ Закрыть", callback_data="close_admin")
    builder.adjust(2, 2, 2)
    return builder.as_markup()


def get_compact_requests_kb(requests: list[VPNRequest]) -> InlineKeyboardMarkup:
    """Compact inline approve/reject for each request."""
    builder = InlineKeyboardBuilder()
    for req in requests:
        name = req.user.full_name.split()[0] if req.user.full_name else f"#{req.id}"
        builder.button(
            text=f"✅ {name}",
            callback_data=RequestAction(action="approve", request_id=req.id).pack(),
        )
    if len(requests) > 1:
        # Two per row for approve buttons
        builder.adjust(2)
    builder.button(text="⬅️ Админ-панель", callback_data="admin_menu")
    return builder.as_markup()


def get_request_action_kb(request: VPNRequest) -> InlineKeyboardMarkup:
    """Get action keyboard for a single VPN request (fallback)."""
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


def get_compact_users_kb(users: list[User], page: int = 0) -> InlineKeyboardMarkup:
    """Compact user list with pagination and detail buttons."""
    builder = InlineKeyboardBuilder()

    total_pages = max(1, (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    start = page * USERS_PER_PAGE
    page_users = users[start : start + USERS_PER_PAGE]

    # Detail button for each user on this page
    for user in page_users:
        builder.button(
            text=f"👤 {user.full_name.split()[0]}",
            callback_data=UserAction(action="detail", user_id=user.id).pack(),
        )
    builder.adjust(3)

    # Pagination row
    if total_pages > 1:
        nav = InlineKeyboardBuilder()
        if page > 0:
            nav.button(
                text="← Назад",
                callback_data=AdminPage(section="users", page=page - 1).pack(),
            )
        nav.button(text=f"{page + 1}/{total_pages}", callback_data="noop")
        if page < total_pages - 1:
            nav.button(
                text="Вперёд →",
                callback_data=AdminPage(section="users", page=page + 1).pack(),
            )
        builder.attach(nav)

    builder.row()
    builder.button(text="⬅️ Админ-панель", callback_data="admin_menu")
    return builder.as_markup()


def get_user_detail_kb(user: User) -> InlineKeyboardMarkup:
    """Detail view for a single user with management actions."""
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


# Keep for backward compat
get_user_manage_kb = get_user_detail_kb


def get_back_to_admin_kb() -> InlineKeyboardMarkup:
    """Get back to admin panel keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Админ-панель", callback_data="admin_menu")
    return builder.as_markup()
