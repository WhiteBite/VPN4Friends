"""Admin handlers for VPN bot."""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.bot.middlewares.admin import AdminFilter
from src.database.repositories import UserRepository
from src.keyboards.admin_kb import (
    get_admin_main_kb,
    get_back_to_admin_kb,
    get_request_action_kb,
    get_protocol_select_kb,
    get_user_manage_kb,
)
from src.keyboards.callbacks import RequestAction, UserAction
from src.services.vpn_service import VPNService
from src.utils.formatters import format_traffic

logger = logging.getLogger(__name__)
router = Router(name="admin")

# Apply admin filter to all handlers in this router
router.message.filter(AdminFilter(settings.admin_ids))
router.callback_query.filter(AdminFilter(settings.admin_ids))


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """Handle /admin command."""
    await message.answer(
        "⚙️ Админ-панель",
        reply_markup=get_admin_main_kb(),
    )


@router.message(Command("users"))
async def cmd_users(message: Message, session: AsyncSession) -> None:
    """Handle /users command - show users with VPN."""
    vpn_service = VPNService(session)
    users = await vpn_service.get_all_users_with_vpn()

    if not users:
        await message.answer("👥 Нет пользователей с VPN.")
        return

    text = f"👥 Пользователи с VPN ({len(users)}):\n\n"
    for user in users:
        text += f"• {user.display_name}\n"

    await message.answer(text)

    # Send each user with management buttons
    for user in users:
        await message.answer(
            f"👤 {user.display_name}\n🆔 <code>{user.telegram_id}</code>",
            reply_markup=get_user_manage_kb(user),
            parse_mode="HTML",
        )


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    """Handle /broadcast command - start broadcast flow."""
    from src.handlers.messaging import BroadcastStates
    from src.keyboards.messaging_kb import get_broadcast_target_kb

    await state.set_state(BroadcastStates.select_target)
    await message.answer(
        "📢 Рассылка сообщений\n\nВыбери, кому отправить:",
        reply_markup=get_broadcast_target_kb(),
    )


@router.message(Command("notify_update"))
async def cmd_notify_update(message: Message, session: AsyncSession, bot: Bot) -> None:
    """Notify all VPN users about config update - they need to get new link."""
    user_repo = UserRepository(session)
    users = await user_repo.get_all_with_vpn()

    if not users:
        await message.answer("👥 Нет пользователей с VPN.")
        return

    await message.answer(f"📤 Отправляю уведомления {len(users)} пользователям...")

    success = 0
    failed = 0

    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                "⚠️ <b>Важное обновление!</b>\n\n"
                "Конфигурация VPN была обновлена.\n"
                "Твоя старая ссылка больше не работает.\n\n"
                "👉 Нажми /link или кнопку «Моя ссылка» в меню, "
                "чтобы получить новую ссылку.\n\n"
                "После получения — удали старый профиль "
                "в приложении и добавь новый.",
                parse_mode="HTML",
            )
            success += 1
        except Exception as e:
            logger.warning(f"Failed to notify {user.telegram_id}: {e}")
            failed += 1

    await message.answer(
        f"✅ Уведомления отправлены!\n\n📨 Успешно: {success}\n❌ Не доставлено: {failed}"
    )


@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery) -> None:
    """Show admin menu."""
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Админ-панель",
        reply_markup=get_admin_main_kb(),
    )


@router.callback_query(F.data == "close_admin")
async def close_admin(callback: CallbackQuery) -> None:
    """Close admin panel."""
    await callback.answer()
    await callback.message.delete()


@router.callback_query(F.data == "admin_notify_update")
async def admin_notify_update_btn(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """Notify all VPN users about config update via button."""
    await callback.answer()

    user_repo = UserRepository(session)
    users = await user_repo.get_all_with_vpn()

    if not users:
        await callback.message.edit_text(
            "👥 Нет пользователей с VPN.",
            reply_markup=get_back_to_admin_kb(),
        )
        return

    await callback.message.edit_text(f"📤 Отправляю уведомления {len(users)} пользователям...")

    success = 0
    failed = 0

    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                "⚠️ <b>Важное обновление!</b>\n\n"
                "Конфигурация VPN была обновлена.\n"
                "Твоя старая ссылка больше не работает.\n\n"
                "👉 Нажми /link или кнопку «Моя ссылка» в меню, "
                "чтобы получить новую ссылку.\n\n"
                "После получения — удали старый профиль "
                "в приложении и добавь новый.",
                parse_mode="HTML",
            )
            success += 1
        except Exception as e:
            logger.warning(f"Failed to notify {user.telegram_id}: {e}")
            failed += 1

    await callback.message.edit_text(
        f"✅ Уведомления отправлены!\n\n📨 Успешно: {success}\n❌ Не доставлено: {failed}",
        reply_markup=get_back_to_admin_kb(),
    )


@router.callback_query(F.data == "admin_requests")
async def admin_requests(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show pending VPN requests."""
    await callback.answer()

    vpn_service = VPNService(session)
    requests = await vpn_service.get_pending_requests()

    if not requests:
        await callback.message.edit_text(
            "📋 Нет заявок на рассмотрении.",
            reply_markup=get_back_to_admin_kb(),
        )
        return

    text = f"📋 Заявки ({len(requests)}):\n\n"
    for req in requests:
        text += f"• {req.user.display_name}\n"

    await callback.message.edit_text(text, reply_markup=get_back_to_admin_kb())

    # Send each request with action buttons
    for req in requests:
        await callback.message.answer(
            f"👤 {req.user.display_name}\n"
            f"🆔 <code>{req.user.telegram_id}</code>\n"
            f"📅 {req.created_at.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=get_request_action_kb(req),
            parse_mode="HTML",
        )


@router.callback_query(RequestAction.filter(F.action == "approve"))
async def approve_request_show_protocols(
    callback: CallbackQuery, callback_data: RequestAction
) -> None:
    """Show protocol selection keyboard to the admin."""
    await callback.answer()
    await callback.message.edit_text(
        "Выберите протокол для пользователя:",
        reply_markup=get_protocol_select_kb(callback_data.request_id),
    )


@router.callback_query(RequestAction.filter(F.action == "select_protocol"))
async def approve_request_select_protocol(
    callback: CallbackQuery,
    callback_data: RequestAction,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Approve VPN request with the selected protocol."""
    await callback.answer()

    if not callback_data.protocol_name:
        await callback.message.edit_text("❌ Ошибка: Протокол не выбран.")
        return

    vpn_service = VPNService(session)
    success, result = await vpn_service.approve_request(
        request_id=callback_data.request_id, protocol_name=callback_data.protocol_name
    )

    if not success:
        await callback.message.edit_text(f"❌ Ошибка: {result}")
        return

    # Get request to notify user
    from src.database.repositories import RequestRepository

    request_repo = RequestRepository(session)
    request = await request_repo.get_by_id(callback_data.request_id)

    await callback.message.edit_text(
        f"✅ Заявка одобрена!\n\nПользователь: {request.user.display_name}\nПротокол: {callback_data.protocol_name}"
    )

    # Notify user with QR code
    try:
        from aiogram.types import BufferedInputFile

        from src.utils.qr_generator import generate_qr_code

        qr_buffer = generate_qr_code(result)
        qr_photo = BufferedInputFile(qr_buffer.read(), filename="vpn_qr.png")

        await bot.send_photo(
            request.user.telegram_id,
            photo=qr_photo,
            caption=(
                "🎉 Твоя заявка одобрена!\n\n"
                "Твоя ссылка для подключения:\n\n"
                f"<code>{result}</code>\n\n"
                "📷 Или отсканируй QR-код выше"
            ),
            parse_mode="HTML",
        )

        apps_text = (
            "📱 Приложения для подключения:\n\n"
            "🍏 iOS: V2RayTun, Shadowrocket\n"
            "🤖 Android: V2RayNG, NekoBox\n"
            "🖥️ Windows: V2RayN, Nekoray, Hiddify\n"
            "🍎 macOS: V2RayU, Hiddify\n"
            "🐧 Linux: Nekoray, Hiddify\n\n"
            "Нажми /menu чтобы открыть главное меню."
        )
        await bot.send_message(request.user.telegram_id, apps_text)
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

    # Get request before rejecting
    from src.database.repositories import RequestRepository

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

    await callback.message.edit_text(f"❌ Заявка отклонена.\n\nПользователь: {user_name}")

    # Notify user
    try:
        await bot.send_message(
            user_telegram_id,
            "😔 К сожалению, твоя заявка отклонена.\n\n"
            "Если считаешь, что это ошибка — напиши Дане напрямую.",
        )
    except Exception as e:
        logger.warning(f"Failed to notify user: {e}")


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show users with VPN."""
    await callback.answer()

    vpn_service = VPNService(session)
    users = await vpn_service.get_all_users_with_vpn()

    if not users:
        await callback.message.edit_text(
            "👥 Нет пользователей с VPN.",
            reply_markup=get_back_to_admin_kb(),
        )
        return

    text = f"👥 Пользователи с VPN ({len(users)}):\n\n"
    for user in users:
        text += f"• {user.display_name}\n"

    await callback.message.edit_text(text, reply_markup=get_back_to_admin_kb())

    # Send each user with management buttons
    for user in users:
        await callback.message.answer(
            f"👤 {user.display_name}\n🆔 <code>{user.telegram_id}</code>",
            reply_markup=get_user_manage_kb(user),
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
        await callback.message.edit_text("❌ Пользователь не найден")
        return

    vpn_service = VPNService(session)
    stats = await vpn_service.get_user_stats(user)

    if not stats:
        await callback.message.edit_text(
            f"👤 {user.display_name}\n\n❌ Статистика недоступна",
            reply_markup=get_user_manage_kb(user),
        )
        return

    upload = format_traffic(stats["upload"])
    download = format_traffic(stats["download"])

    await callback.message.edit_text(
        f"👤 {user.display_name}\n\n📊 Статистика:\n🔼 Загружено: {upload}\n🔽 Скачано: {download}",
        reply_markup=get_user_manage_kb(user),
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
        await callback.message.edit_text("❌ Пользователь не найден")
        return

    vpn_service = VPNService(session)
    success = await vpn_service.revoke_vpn(user)

    if success:
        await callback.message.edit_text(
            f"✅ VPN отозван у {user.display_name}",
            reply_markup=get_back_to_admin_kb(),
        )

        # Notify user
        try:
            await bot.send_message(
                user.telegram_id,
                "⚠️ Твой VPN был отозван администратором.\n\n"
                "Если хочешь получить доступ снова — отправь новую заявку.",
            )
        except Exception as e:
            logger.warning(f"Failed to notify user: {e}")
    else:
        await callback.message.edit_text(
            f"❌ Не удалось отозвать VPN у {user.display_name}",
            reply_markup=get_back_to_admin_kb(),
        )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show global statistics."""
    await callback.answer()

    user_repo = UserRepository(session)
    all_users = await user_repo.get_all()
    users_with_vpn = await user_repo.get_all_with_vpn()

    from src.database.repositories import RequestRepository

    request_repo = RequestRepository(session)
    pending = await request_repo.get_all_pending()

    await callback.message.edit_text(
        f"📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {len(all_users)}\n"
        f"🔑 С VPN: {len(users_with_vpn)}\n"
        f"⏳ Заявок на рассмотрении: {len(pending)}",
        reply_markup=get_back_to_admin_kb(),
    )
