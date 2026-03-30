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


@router.message(Command("sync_all"))
async def cmd_sync_all(message: Message, session: AsyncSession) -> None:
    """Force sync all users with VPN to all configured panels."""
    await message.answer("🔄 Запуск глобальной синхронизации всех пользователей...")

    user_repo = UserRepository(session)
    vpn_service = VPNService(session)

    users = await user_repo.get_all_with_vpn()
    if not users:
        await message.answer("ℹ️ Нет пользователей с активным VPN для синхронизации.")
        return

    success_count = 0
    fail_count = 0

    progress_msg = await message.answer(f"⏳ Синхронизация... 0/{len(users)}")

    for i, user in enumerate(users):
        profile = user.active_profile
        if not profile or not profile.profile_data:
            fail_count += 1
            continue

        email = profile.profile_data.get("email")
        # Use client_id from column (new flow) or fallback to JSON
        client_id = profile.client_id or profile.profile_data.get("client_id")
        protocol = profile.protocol_name

        if not email or not client_id:
            fail_count += 1
            continue

        try:
            # Broadcast to all panels
            res = await vpn_service.sync_client_to_all_panels(email, client_id, protocol)
            if res:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f"Sync failed for {email}: {e}")
            fail_count += 1

        # Update progress every 5 users
        if (i + 1) % 5 == 0:
            await progress_msg.edit_text(f"⏳ Синхронизация... {i + 1}/{len(users)}")
            await asyncio.sleep(0.5)

    await progress_msg.delete()
    await message.answer(
        f"✅ <b>Синхронизация завершена!</b>\n\n"
        f"🚀 Успешно: {success_count}\n"
        f"❌ Ошибок: {fail_count}\n"
        f"👥 Всего обработано: {len(users)}\n\n"
        f"<i>Все пользователи теперь имеют доступ ко всем серверам из конфига.</i>",
        parse_mode="HTML",
    )


# Dashboard moved to Mini App admin tab


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
    """Handle approve — auto-approve with vless and notify user."""
    await callback.answer("Одобряем и создаем профили...")

    from src.services.vpn_service import VPNService

    vpn_service = VPNService(session)
    # Provision global access - user will be synced to all available panels/inbounds
    success, result = await vpn_service.approve_request(request_id=callback_data.request_id)

    if not success:
        await callback.message.edit_text(
            f"❌ Ошибка: {result}",
            reply_markup=get_back_to_admin_kb(),
        )
        return

    # Notify user
    request_repo = RequestRepository(session)
    request = await request_repo.get_by_id(callback_data.request_id)
    await _notify_user_approved(callback, request)


async def _notify_user_approved(callback, request):
    """Send step-by-step onboarding after approval."""
    bot = callback.bot

    await callback.message.edit_text(
        f"✅ Заявка одобрена!\n\n👤 {request.user.display_name}",
        reply_markup=get_back_to_admin_kb(),
    )

    try:
        from src.keyboards.user_kb import get_approval_onboarding_kb

        await bot.send_message(
            request.user.telegram_id,
            "🎉 <b>Доступ к VPN активирован!</b>\n\n"
            "<b>Что дальше:</b>\n"
            "1️⃣ Скачай приложение для своего устройства (кнопки ниже)\n"
            "2️⃣ Открой <b>Кабинет</b> → скопируй ссылку подписки\n"
            "3️⃣ Вставь ссылку в приложение → Подключись! 🚀\n\n"
            "<i>Подписка содержит все серверы и обновляется автоматически.</i>",
            reply_markup=get_approval_onboarding_kb(),
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


# ============ BROADCAST ============


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


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_btn(callback: CallbackQuery, state: FSMContext) -> None:
    """Start broadcast flow from admin panel button."""
    await callback.answer()
    from src.handlers.messaging import BroadcastStates
    from src.keyboards.messaging_kb import get_broadcast_target_kb

    await state.set_state(BroadcastStates.select_target)
    await callback.message.edit_text(
        "📢 Рассылка\n\nВыбери, кому отправить:",
        reply_markup=get_broadcast_target_kb(),
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
