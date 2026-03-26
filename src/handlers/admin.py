"""Admin handlers for VPN bot."""

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.bot.middlewares.admin import AdminFilter
from src.database.repositories import RequestRepository, UserRepository
from src.keyboards.admin_kb import (
    USERS_PER_PAGE,
    get_admin_main_kb,
    get_back_to_admin_kb,
    get_compact_requests_kb,
    get_compact_users_kb,
    get_protocol_select_kb,
    get_user_detail_kb,
)
from src.keyboards.callbacks import AdminPage, RequestAction, UserAction
from src.services.vpn_service import VPNService
from src.utils.formatters import format_traffic

logger = logging.getLogger(__name__)
router = Router(name="admin")

# Apply admin filter to all handlers in this router
router.message.filter(AdminFilter(settings.admin_ids))
router.callback_query.filter(AdminFilter(settings.admin_ids))


# ============ HELPERS ============


async def _send_mass_notification(bot: Bot, users: list, text: str) -> tuple[int, int]:
    """Send a message to multiple users with flood control.

    Returns (success_count, failed_count).
    """
    success = 0
    failed = 0
    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                text,
                parse_mode="HTML",
            )
            success += 1
        except Exception as e:
            logger.warning(f"Notify {user.telegram_id} failed: {e}")
            failed += 1
        await asyncio.sleep(0.05)  # Telegram flood control
    return success, failed


async def _get_counts(session: AsyncSession) -> tuple[int, int]:
    """Get pending requests count and VPN users count."""
    request_repo = RequestRepository(session)
    user_repo = UserRepository(session)
    pending = await request_repo.get_all_pending()
    vpn_users = await user_repo.get_all_with_vpn()
    return len(pending), len(vpn_users)


# ============ ADMIN MENU ============


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    """Handle /admin command."""
    pending_count, vpn_count = await _get_counts(session)
    await message.answer(
        "⚙️ Админ-панель",
        reply_markup=get_admin_main_kb(pending_count, vpn_count),
    )


@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show admin menu."""
    await callback.answer()
    pending_count, vpn_count = await _get_counts(session)
    await callback.message.edit_text(
        "⚙️ Админ-панель",
        reply_markup=get_admin_main_kb(pending_count, vpn_count),
    )


@router.callback_query(F.data == "close_admin")
async def close_admin(callback: CallbackQuery) -> None:
    """Close admin panel."""
    await callback.answer()
    await callback.message.delete()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    """No-op for pagination counter button."""
    await callback.answer()


# ============ DASHBOARD ============


@router.callback_query(F.data == "admin_dashboard")
async def admin_dashboard(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show dashboard with server status and stats."""
    await callback.answer()

    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    all_users = await user_repo.get_all()
    vpn_users = await user_repo.get_all_with_vpn()
    pending = await request_repo.get_all_pending()

    # Try to get server stats
    server_line = "📶 Сервер: ⏳ Проверяю..."
    online_line = ""
    traffic_line = ""

    try:
        from src.services.xui_api import XUIApi

        async with XUIApi() as api:
            status = await api.get_server_status()
            online_clients = await api.get_online_clients()

        online_count = len(online_clients) if online_clients else 0
        total_traffic = format_traffic(status["upload"] + status["download"])

        server_line = "📶 Сервер: ✅ Онлайн"
        online_line = f"\n🟢 Онлайн: {online_count}/{len(vpn_users)}"
        traffic_line = f"\n📈 Трафик: {total_traffic}"
    except Exception as e:
        logger.warning(f"Dashboard server check failed: {e}")
        server_line = "📶 Сервер: ❌ Недоступен"

    text = (
        f"📊 <b>Дашборд VPN4Friends</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{server_line}{online_line}{traffic_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Всего юзеров: {len(all_users)}\n"
        f"🔑 С VPN: {len(vpn_users)}\n"
        f"⏳ Заявок: {len(pending)}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_admin_kb(),
        parse_mode="HTML",
    )


# ============ REQUESTS (compact) ============


@router.callback_query(F.data == "admin_requests")
async def admin_requests(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show pending VPN requests as compact list."""
    await callback.answer()

    vpn_service = VPNService(session)
    requests = await vpn_service.get_pending_requests()

    if not requests:
        await callback.message.edit_text(
            "📋 Нет заявок на рассмотрении.",
            reply_markup=get_back_to_admin_kb(),
        )
        return

    # Build compact list
    lines = [f"📋 <b>Заявки ({len(requests)})</b>\n"]
    for i, req in enumerate(requests, 1):
        name = req.user.display_name
        date = req.created_at.strftime("%d.%m %H:%M")
        lines.append(f"{i}. {name} — {date}")

    text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=get_compact_requests_kb(requests),
        parse_mode="HTML",
    )


@router.callback_query(RequestAction.filter(F.action == "approve"))
async def approve_request(
    callback: CallbackQuery, callback_data: RequestAction, session: AsyncSession
) -> None:
    """Handle approve — auto-select if single protocol, else show selector."""
    await callback.answer()

    if len(settings.protocols) == 1:
        # Auto-approve with the only protocol
        proto = settings.protocols[0]
        vpn_service = VPNService(session)
        success, result = await vpn_service.approve_request(
            request_id=callback_data.request_id, protocol_name=proto.name
        )

        if not success:
            await callback.message.edit_text(
                f"❌ {result}",
                reply_markup=get_back_to_admin_kb(),
            )
            return

        # Notify user
        request_repo = RequestRepository(session)
        request = await request_repo.get_by_id(callback_data.request_id)
        await _notify_user_approved(callback, request, result, proto.name)
    else:
        await callback.message.edit_text(
            "Выбери протокол:",
            reply_markup=get_protocol_select_kb(callback_data.request_id),
        )


@router.callback_query(RequestAction.filter(F.action == "select_protocol"))
async def approve_with_protocol(
    callback: CallbackQuery,
    callback_data: RequestAction,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Approve VPN request with the selected protocol."""
    await callback.answer()

    if not callback_data.protocol_name:
        await callback.message.edit_text("❌ Протокол не выбран.")
        return

    vpn_service = VPNService(session)
    success, result = await vpn_service.approve_request(
        request_id=callback_data.request_id, protocol_name=callback_data.protocol_name
    )

    if not success:
        await callback.message.edit_text(
            f"❌ {result}",
            reply_markup=get_back_to_admin_kb(),
        )
        return

    request_repo = RequestRepository(session)
    request = await request_repo.get_by_id(callback_data.request_id)
    await _notify_user_approved(callback, request, result, callback_data.protocol_name)


async def _notify_user_approved(callback, request, vpn_link, protocol_name):
    """Send approval notification to user and update admin message."""
    bot = callback.bot
    proto_upper = protocol_name.upper()

    await callback.message.edit_text(
        f"✅ Одобрено!\n\n👤 {request.user.display_name}\n⚡ {proto_upper}",
        reply_markup=get_back_to_admin_kb(),
    )

    try:
        from aiogram.types import BufferedInputFile
        from src.utils.qr_generator import generate_qr_code

        qr_buffer = generate_qr_code(vpn_link)
        qr_photo = BufferedInputFile(qr_buffer.read(), filename="vpn_qr.png")

        await bot.send_photo(
            request.user.telegram_id,
            photo=qr_photo,
            caption=(
                f"🎉 <b>VPN одобрен!</b>\n\n"
                f"Твоя {proto_upper} ссылка:\n\n"
                f"<code>{vpn_link}</code>\n\n"
                f"📷 Или отсканируй QR-код выше\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📱 <b>Скачай приложение:</b>\n"
                f"• iPhone → <a href='https://apps.apple.com/app/v2raytun/id6476628951'>V2RayTun</a>\n"
                f"• Android → <a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>V2RayNG</a>\n"
                f"• Windows/Mac → <a href='https://github.com/hiddify/hiddify-app/releases'>Hiddify</a>\n\n"
                f"👉 Скопируй ссылку → Открой приложение → Добавь профиль"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Failed to notify user: {e}")


@router.callback_query(RequestAction.filter(F.action == "reject"))
async def reject_request(
    callback: CallbackQuery,
    callback_data: RequestAction,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Reject VPN request."""
    await callback.answer()

    request_repo = RequestRepository(session)
    request = await request_repo.get_by_id(callback_data.request_id)

    if not request:
        await callback.message.edit_text("❌ Заявка не найдена")
        return

    user_telegram_id = request.user.telegram_id
    user_name = request.user.display_name

    vpn_service = VPNService(session)
    success = await vpn_service.reject_request(callback_data.request_id)

    if not success:
        await callback.message.edit_text("❌ Ошибка при отклонении заявки")
        return

    await callback.message.edit_text(
        f"❌ Заявка отклонена.\n\n👤 {user_name}",
        reply_markup=get_back_to_admin_kb(),
    )

    try:
        await bot.send_message(
            user_telegram_id,
            "😔 Заявка отклонена.\n\nЕсли считаешь, что это ошибка — напиши /support",
        )
    except Exception as e:
        logger.warning(f"Failed to notify user: {e}")


# ============ USERS (compact + pagination) ============


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show paginated user list."""
    await callback.answer()
    await _show_users_page(callback, session, page=0)


@router.callback_query(AdminPage.filter(F.section == "users"))
async def admin_users_page(
    callback: CallbackQuery, callback_data: AdminPage, session: AsyncSession
) -> None:
    """Handle user list pagination."""
    await callback.answer()
    await _show_users_page(callback, session, page=callback_data.page)


async def _show_users_page(callback, session, page=0):
    """Render paginated users list."""
    vpn_service = VPNService(session)
    users = await vpn_service.get_all_users_with_vpn()

    if not users:
        await callback.message.edit_text(
            "👥 Нет юзеров с VPN.",
            reply_markup=get_back_to_admin_kb(),
        )
        return

    # Build compact list
    start = page * USERS_PER_PAGE
    page_users = users[start : start + USERS_PER_PAGE]

    lines = [f"👥 <b>Юзеры с VPN ({len(users)})</b>\n"]
    for i, user in enumerate(page_users, start + 1):
        proto = ""
        if user.active_profile:
            proto = f" • {user.active_profile.protocol_name.upper()}"
        lines.append(f"{i}. {user.display_name}{proto}")

    text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=get_compact_users_kb(users, page),
        parse_mode="HTML",
    )


@router.callback_query(UserAction.filter(F.action == "detail"))
async def user_detail(
    callback: CallbackQuery,
    callback_data: UserAction,
    session: AsyncSession,
) -> None:
    """Show detailed view for a single user."""
    await callback.answer()

    from sqlalchemy import select
    from src.database.models import User

    result = await session.execute(select(User).where(User.id == callback_data.user_id))
    user = result.scalar_one_or_none()

    if not user:
        await callback.message.edit_text("❌ Юзер не найден")
        return

    proto = ""
    if user.active_profile:
        proto = f"\n⚡ Протокол: {user.active_profile.protocol_name.upper()}"

    await callback.message.edit_text(
        f"👤 <b>{user.display_name}</b>\n🆔 <code>{user.telegram_id}</code>{proto}",
        reply_markup=get_user_detail_kb(user),
        parse_mode="HTML",
    )


@router.callback_query(UserAction.filter(F.action == "stats"))
async def user_stats(
    callback: CallbackQuery,
    callback_data: UserAction,
    session: AsyncSession,
) -> None:
    """Show user statistics."""
    await callback.answer()

    from sqlalchemy import select
    from src.database.models import User

    result = await session.execute(select(User).where(User.id == callback_data.user_id))
    user = result.scalar_one_or_none()

    if not user:
        await callback.message.edit_text("❌ Юзер не найден")
        return

    vpn_service = VPNService(session)
    stats = await vpn_service.get_user_stats(user)

    if not stats:
        await callback.message.edit_text(
            f"👤 {user.display_name}\n\n❌ Статистика недоступна",
            reply_markup=get_user_detail_kb(user),
        )
        return

    upload = format_traffic(stats["upload"])
    download = format_traffic(stats["download"])

    await callback.message.edit_text(
        f"👤 {user.display_name}\n\n📊 Статистика:\n🔼 Upload: {upload}\n🔽 Download: {download}",
        reply_markup=get_user_detail_kb(user),
    )


@router.callback_query(UserAction.filter(F.action == "revoke"))
async def revoke_user_vpn(
    callback: CallbackQuery,
    callback_data: UserAction,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Revoke user's VPN access."""
    await callback.answer()

    from sqlalchemy import select
    from src.database.models import User

    result = await session.execute(select(User).where(User.id == callback_data.user_id))
    user = result.scalar_one_or_none()

    if not user:
        await callback.message.edit_text("❌ Юзер не найден")
        return

    vpn_service = VPNService(session)
    success = await vpn_service.revoke_vpn(user)

    if success:
        await callback.message.edit_text(
            f"✅ VPN отозван у {user.display_name}",
            reply_markup=get_back_to_admin_kb(),
        )
        try:
            await bot.send_message(
                user.telegram_id,
                "⚠️ Твой VPN был отозван.\n\nХочешь получить снова — отправь заявку.",
            )
        except Exception as e:
            logger.warning(f"Failed to notify user: {e}")
    else:
        await callback.message.edit_text(
            f"❌ Не удалось отозвать VPN у {user.display_name}",
            reply_markup=get_back_to_admin_kb(),
        )


# ============ STATS (kept as fallback command) ============


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    """Redirect old stats button to dashboard."""
    await admin_dashboard(callback, session)


# ============ BROADCAST / NOTIFY ============


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    """Handle /broadcast command — start broadcast flow."""
    from src.handlers.messaging import BroadcastStates
    from src.keyboards.messaging_kb import get_broadcast_target_kb

    await state.set_state(BroadcastStates.select_target)
    await message.answer(
        "📢 Рассылка\n\nВыбери, кому отправить:",
        reply_markup=get_broadcast_target_kb(),
    )


@router.message(Command("notify_update"))
async def cmd_notify_update(message: Message, session: AsyncSession, bot: Bot) -> None:
    """Notify all VPN users about config update."""
    user_repo = UserRepository(session)
    users = await user_repo.get_all_with_vpn()

    if not users:
        await message.answer("👥 Нет юзеров с VPN.")
        return

    await message.answer(f"📤 Отправляю {len(users)} юзерам...")

    notify_text = (
        "⚠️ <b>Обновление!</b>\n\n"
        "Конфигурация VPN обновлена.\n"
        "Твоя старая ссылка не работает.\n\n"
        "👉 Нажми /link чтобы получить новую."
    )
    success, failed = await _send_mass_notification(bot, users, notify_text)

    await message.answer(f"✅ Отправлено!\n\n📨 Доставлено: {success}\n❌ Ошибок: {failed}")


@router.callback_query(F.data == "admin_notify_update")
async def admin_notify_update_btn(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """Notify update via button — removed, redirect to broadcast."""
    # Use the general broadcast flow instead
    from src.handlers.messaging import BroadcastStates
    from src.keyboards.messaging_kb import get_broadcast_target_kb

    await callback.answer()
    # We'll use FSM from the callback context
    state = callback.bot.get("fsm_context")
    await callback.message.edit_text(
        "📢 Для рассылки используй /broadcast",
        reply_markup=get_back_to_admin_kb(),
    )


@router.message(Command("users"))
async def cmd_users(message: Message, session: AsyncSession) -> None:
    """Handle /users command."""
    vpn_service = VPNService(session)
    users = await vpn_service.get_all_users_with_vpn()

    if not users:
        await message.answer("👥 Нет юзеров с VPN.")
        return

    lines = [f"👥 <b>Юзеры с VPN ({len(users)})</b>\n"]
    for i, user in enumerate(users, 1):
        proto = ""
        if user.active_profile:
            proto = f" • {user.active_profile.protocol_name.upper()}"
        lines.append(f"{i}. {user.display_name}{proto}")

    await message.answer(
        "\n".join(lines),
        reply_markup=get_back_to_admin_kb(),
        parse_mode="HTML",
    )
