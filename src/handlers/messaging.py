"""Messaging handlers for broadcasts and user feedback."""

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.bot.middlewares.admin import AdminFilter
from src.database.repositories import UserRepository
from src.keyboards.messaging_kb import (
    get_broadcast_target_kb,
    get_cancel_kb,
    get_contact_admin_kb,
    get_continue_chat_kb,
)

logger = logging.getLogger(__name__)

# User router for feedback
user_router = Router(name="user_messaging")

# Admin router for broadcasts
admin_router = Router(name="admin_messaging")
admin_router.message.filter(AdminFilter(settings.admin_ids))
admin_router.callback_query.filter(AdminFilter(settings.admin_ids))


class FeedbackStates(StatesGroup):
    """States for user feedback flow."""

    waiting_for_message = State()


class BroadcastStates(StatesGroup):
    """States for admin broadcast flow."""

    select_target = State()
    waiting_for_message = State()
    waiting_for_user_id = State()
    waiting_for_dm_message = State()


# ============ USER FEEDBACK ============


@user_router.callback_query(F.data == "contact_admin")
async def start_feedback(callback: CallbackQuery, state: FSMContext) -> None:
    """Start feedback flow."""
    await callback.answer()
    await state.set_state(FeedbackStates.waiting_for_message)
    await callback.message.edit_text(
        "✉️ Напиши сообщение для Дани.\n\nМожешь задать вопрос или сообщить о проблеме.",
        reply_markup=get_cancel_kb(),
    )


@user_router.message(FeedbackStates.waiting_for_message)
async def process_feedback(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Process user feedback and send to admin."""
    await state.clear()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("❌ Ошибка. Попробуй /start")
        return

    # Send to all admins
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"📩 Сообщение от пользователя:\n\n"
                f"👤 {user.display_name}\n"
                f"🆔 `{user.telegram_id}`\n\n"
                f"💬 {message.text}",
                parse_mode="Markdown",
                reply_markup=get_contact_admin_kb(user.telegram_id),
            )
        except Exception as e:
            logger.warning(f"Failed to send feedback to admin {admin_id}: {e}")

    await message.answer("✅ Сообщение отправлено!\n\nДаня ответит тебе в этом чате.")


@user_router.callback_query(F.data == "cancel_action")
async def cancel_feedback(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel feedback flow."""
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.delete()


# ============ ADMIN BROADCAST ============


@admin_router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Start broadcast flow."""
    await callback.answer()
    await state.set_state(BroadcastStates.select_target)
    await callback.message.edit_text(
        "📢 Рассылка сообщений\n\nВыбери, кому отправить:",
        reply_markup=get_broadcast_target_kb(),
    )


@admin_router.callback_query(
    BroadcastStates.select_target,
    F.data.in_(["broadcast_all", "broadcast_vpn", "broadcast_no_vpn"]),
)
async def select_broadcast_target(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Select broadcast target audience."""
    await callback.answer()

    target_map = {
        "broadcast_all": "all",
        "broadcast_vpn": "with_vpn",
        "broadcast_no_vpn": "without_vpn",
    }
    target = target_map[callback.data]

    await state.update_data(target=target)
    await state.set_state(BroadcastStates.waiting_for_message)

    target_names = {
        "all": "всем пользователям",
        "with_vpn": "пользователям с VPN",
        "without_vpn": "пользователям без VPN",
    }

    await callback.message.edit_text(
        f"📢 Рассылка {target_names[target]}\n\nНапиши сообщение для отправки:",
        reply_markup=get_cancel_kb(),
    )


@admin_router.message(BroadcastStates.waiting_for_message)
async def process_broadcast(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Send broadcast message to selected users."""
    data = await state.get_data()
    target = data.get("target", "all")
    await state.clear()

    user_repo = UserRepository(session)

    if target == "all":
        users = await user_repo.get_all()
    elif target == "with_vpn":
        users = await user_repo.get_all_with_vpn()
    else:  # without_vpn
        all_users = await user_repo.get_all()
        users = [u for u in all_users if not u.has_vpn]

    success = 0
    failed = 0

    for user in users:
        if user.telegram_id in settings.admin_ids:
            continue  # Skip admins

        try:
            await bot.send_message(
                user.telegram_id,
                f"📢 Объявление от Дани:\n\n{message.text}",
            )
            success += 1
        except Exception as e:
            logger.warning(f"Failed to send broadcast to {user.telegram_id}: {e}")
            failed += 1

    await message.answer(
        f"✅ Рассылка завершена!\n\n📨 Отправлено: {success}\n❌ Не доставлено: {failed}"
    )


# ============ ADMIN DIRECT MESSAGE ============


@admin_router.callback_query(F.data == "admin_dm")
async def start_dm(callback: CallbackQuery, state: FSMContext) -> None:
    """Start direct message flow."""
    await callback.answer()
    await state.set_state(BroadcastStates.waiting_for_user_id)
    await callback.message.edit_text(
        "✉️ Личное сообщение пользователю\n\nВведи Telegram ID пользователя:",
        reply_markup=get_cancel_kb(),
    )


@admin_router.callback_query(F.data.startswith("reply_to_"))
async def reply_to_user(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Quick reply to user from feedback notification."""
    await callback.answer()

    user_id = int(callback.data.split("_")[-1])

    # Get user info for context
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(user_id)
    user_name = user.display_name if user else f"ID: {user_id}"

    await state.update_data(user_id=user_id, user_name=user_name)
    await state.set_state(BroadcastStates.waiting_for_dm_message)

    await callback.message.answer(
        f"✉️ Ответ пользователю:\n👤 {user_name}\n\nНапиши сообщение:",
        reply_markup=get_cancel_kb(),
        parse_mode="Markdown",
    )


@admin_router.message(BroadcastStates.waiting_for_user_id)
async def process_dm_user_id(message: Message, state: FSMContext) -> None:
    """Process user ID for direct message."""
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный ID. Введи число:")
        return

    await state.update_data(user_id=user_id)
    await state.set_state(BroadcastStates.waiting_for_dm_message)
    await message.answer(
        f"✉️ Сообщение для `{user_id}`\n\nНапиши текст:",
        reply_markup=get_cancel_kb(),
        parse_mode="Markdown",
    )


@admin_router.message(BroadcastStates.waiting_for_dm_message)
async def process_dm_message(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    """Send direct message to user."""
    data = await state.get_data()
    user_id = data.get("user_id")
    user_name = data.get("user_name", f"ID: {user_id}")
    await state.clear()

    if not user_id:
        await message.answer("❌ Ошибка: ID пользователя не найден")
        return

    try:
        from src.keyboards.user_reply_kb import get_reply_to_admin_kb

        await bot.send_message(
            user_id,
            f"💬 Сообщение от Дани:\n\n{message.text}",
            reply_markup=get_reply_to_admin_kb(),
        )
        await message.answer(
            f"✅ Сообщение отправлено!\n👤 {user_name}",
            reply_markup=get_continue_chat_kb(user_id),
        )
    except Exception as e:
        logger.warning(f"Failed to send DM to {user_id}: {e}")
        await message.answer(f"❌ Не удалось отправить сообщение: {e}")


@admin_router.callback_query(
    F.data == "cancel_action",
)
async def cancel_admin_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel admin action."""
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.delete()
