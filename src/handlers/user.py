"""User handlers for VPN bot."""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.database.repositories import RequestRepository, UserRepository
from src.keyboards.admin_kb import get_request_action_kb
from src.keyboards.messaging_kb import get_cancel_kb
from src.keyboards.user_kb import (
    get_back_kb,
    get_confirm_delete_kb,
    get_link_kb,
    get_stats_kb,
    get_user_main_kb,
)
from src.services.vpn_service import VPNService
from src.services.xui_api import XUIApi
from src.utils.formatters import format_traffic
from src.utils.qr_generator import generate_qr_code

logger = logging.getLogger(__name__)
router = Router(name="user")


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, bot: Bot) -> None:
    """Handle /start command."""
    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    is_admin = message.from_user.id in settings.admin_ids
    user, created = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
        is_admin=is_admin,
    )

    if created:
        await message.answer(
            f"👋 Привет, {user.full_name}!\n\n"
            "Это бот для получения VPN от Дани.\n"
            "Нажми кнопку ниже, чтобы отправить заявку."
        )
    else:
        await message.answer(f"👋 С возвращением, {user.full_name}!")

    has_pending = await request_repo.has_pending(user)
    await message.answer(
        "Главное меню:",
        reply_markup=get_user_main_kb(user.has_vpn, has_pending),
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession) -> None:
    """Handle /menu command."""
    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start")
        return

    has_pending = await request_repo.has_pending(user)
    await message.answer(
        "Главное меню:",
        reply_markup=get_user_main_kb(user.has_vpn, has_pending),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    help_text = (
        "📖 <b>Справка по боту</b>\n\n"
        "Этот бот позволяет получить VPN от Дани.\n\n"
        "<b>🔹 Как получить VPN:</b>\n"
        "1. Нажми «Попросить VPN у Дани»\n"
        "2. Дождись одобрения заявки\n"
        "3. Скопируй ссылку и вставь в приложение\n\n"
        "<b>🔹 Приложения для подключения:</b>\n"
        "• iOS: V2RayTun, Shadowrocket\n"
        "• Android: V2RayNG, NekoBox\n"
        "• Windows: V2RayN, Nekoray, Hiddify\n"
        "• macOS: V2RayU, Hiddify\n\n"
        "<b>🔹 Команды:</b>\n"
        "/start — начать работу\n"
        "/menu — главное меню\n"
        "/status — статус сервера\n"
        "/link — получить ссылку VPN\n"
        "/stats — статистика трафика\n"
        "/support — написать админу\n"
        "/help — эта справка\n\n"
        "❓ Вопросы? Напиши /support"
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Handle /status command - show server status banner."""
    await message.answer("⏳ Проверяю статус сервера...")

    try:
        async with XUIApi() as api:
            status = await api.get_server_status()
            online_clients = await api.get_online_clients()

        online_count = len(online_clients) if online_clients else 0
        total_traffic = format_traffic(status["upload"] + status["download"])

        # Build status banner
        banner = (
            "🌐 <b>VPN4Friends</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📶 Сервер: ✅ Онлайн\n"
            f"⚡ Скорость: ~85 Мбит/с\n"
            f"👥 Клиентов: {status['clients']}\n"
            f"🟢 Онлайн сейчас: {online_count}\n"
            f"📊 Трафик: {total_traffic}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )

        await message.answer(banner, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Failed to get server status: {e}")
        banner = (
            "🌐 <b>VPN4Friends</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📶 Сервер: ❌ Недоступен\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Попробуй позже или напиши /support"
        )
        await message.answer(banner, parse_mode="HTML")


@router.message(Command("link"))
async def cmd_link(message: Message, session: AsyncSession) -> None:
    """Handle /link command - quick access to VPN link."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Сначала нажми /start")
        return

    if not user.has_vpn:
        await message.answer("❌ У тебя нет активного VPN. Отправь заявку через /menu")
        return

    vpn_service = VPNService(session)
    vless_url = await vpn_service.get_vless_url(user)

    # Generate QR code
    qr_buffer = generate_qr_code(vless_url)
    qr_photo = BufferedInputFile(qr_buffer.read(), filename="vpn_qr.png")

    await message.answer_photo(
        photo=qr_photo,
        caption=f"🔗 Твоя ссылка:\n\n`{vless_url}`",
        parse_mode="Markdown",
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    """Handle /stats command - quick access to traffic stats."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Сначала нажми /start")
        return

    if not user.has_vpn:
        await message.answer("❌ У тебя нет активного VPN.")
        return

    vpn_service = VPNService(session)
    stats = await vpn_service.get_user_stats(user)

    if not stats:
        await message.answer("❌ Не удалось получить статистику.")
        return

    upload = format_traffic(stats["upload"])
    download = format_traffic(stats["download"])

    await message.answer(
        f"📊 Твоя статистика:\n\n🔼 Загружено: {upload}\n🔽 Скачано: {download}",
        reply_markup=get_stats_kb(),
    )


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext) -> None:
    """Handle /support command - contact admin."""
    from src.handlers.messaging import FeedbackStates

    await state.set_state(FeedbackStates.waiting_for_message)
    await message.answer(
        "✉️ Напиши сообщение для Дани.\n\nМожешь задать вопрос или сообщить о проблеме.",
        reply_markup=get_cancel_kb(),
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle back to menu callback."""
    await callback.answer()

    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    has_pending = await request_repo.has_pending(user)
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=get_user_main_kb(user.has_vpn, has_pending),
    )


@router.callback_query(F.data == "request_vpn")
async def request_vpn(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """Handle VPN request callback."""
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    vpn_service = VPNService(session)
    request = await vpn_service.create_request(user)

    if not request:
        await callback.message.edit_text(
            "⚠️ У тебя уже есть VPN или заявка на рассмотрении.",
            reply_markup=get_back_kb(),
        )
        return

    await callback.message.edit_text(
        "✅ Заявка отправлена!\n\n"
        "Даня получит уведомление и скоро рассмотрит твой запрос.\n"
        "Жди ответа в этом чате.",
        reply_markup=get_back_kb(),
    )

    # Notify admins
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 Новая заявка на VPN!\n\n👤 {user.display_name}\n🆔 `{user.telegram_id}`",
                reply_markup=get_request_action_kb(request),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")


@router.callback_query(F.data == "pending_info")
async def pending_info(callback: CallbackQuery) -> None:
    """Handle pending request info callback."""
    await callback.answer(
        "Твоя заявка на рассмотрении. Даня скоро ответит!",
        show_alert=True,
    )


@router.callback_query(F.data == "my_link")
async def my_link(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show user's VLESS link with QR code."""
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user or not user.has_vpn:
        await callback.message.edit_text(
            "❌ У тебя нет активного VPN.",
            reply_markup=get_back_kb(),
        )
        return

    vpn_service = VPNService(session)
    vless_url = await vpn_service.get_vless_url(user)

    # Generate QR code
    qr_buffer = generate_qr_code(vless_url)
    qr_photo = BufferedInputFile(qr_buffer.read(), filename="vpn_qr.png")

    # Delete old message and send new with photo
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=qr_photo,
        caption=(
            f"🔗 <b>Твоя ссылка для подключения:</b>\n\n"
            f"<code>{vless_url}</code>\n\n"
            f"📷 Или отсканируй QR-код выше\n\n"
            f"📱 <b>Приложения:</b>\n"
            f"• iOS: V2RayTun, Shadowrocket\n"
            f"• Android: V2RayNG, NekoBox\n"
            f"• Windows/macOS/Linux: Hiddify, Nekoray"
        ),
        reply_markup=get_link_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.in_(["my_stats", "refresh_stats"]))
async def my_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show user's traffic statistics."""
    is_refresh = callback.data == "refresh_stats"

    if is_refresh:
        await callback.answer("🔄 Обновляю...")
    else:
        await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user or not user.has_vpn:
        await callback.message.edit_text(
            "❌ У тебя нет активного VPN.",
            reply_markup=get_back_kb(),
        )
        return

    vpn_service = VPNService(session)
    stats = await vpn_service.get_user_stats(user)

    if not stats:
        await callback.message.edit_text(
            "❌ Не удалось получить статистику.",
            reply_markup=get_back_kb(),
        )
        return

    upload = format_traffic(stats["upload"])
    download = format_traffic(stats["download"])

    await callback.message.edit_text(
        f"📊 Твоя статистика:\n\n🔼 Загружено: {upload}\n🔽 Скачано: {download}",
        reply_markup=get_stats_kb(),
    )


@router.callback_query(F.data == "delete_vpn")
async def delete_vpn(callback: CallbackQuery) -> None:
    """Confirm VPN deletion."""
    await callback.answer()
    await callback.message.edit_text(
        "⚠️ Ты уверен, что хочешь удалить свой VPN?\n\nТебе придётся заново отправлять заявку.",
        reply_markup=get_confirm_delete_kb(),
    )


@router.callback_query(F.data == "confirm_delete_vpn")
async def confirm_delete_vpn(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle VPN deletion confirmation."""
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    vpn_service = VPNService(session)
    success = await vpn_service.revoke_vpn(user)

    if success:
        await callback.message.edit_text(
            "✅ VPN удалён.\n\nМожешь отправить новую заявку, когда захочешь.",
            reply_markup=get_user_main_kb(has_vpn=False),
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось удалить VPN.",
            reply_markup=get_back_kb(),
        )


@router.callback_query(F.data == "refresh_link")
async def refresh_link(callback: CallbackQuery, session: AsyncSession) -> None:
    """Refresh VPN link (re-fetch from panel)."""
    await callback.answer("🔄 Обновляю...")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user or not user.has_vpn:
        await callback.message.delete()
        await callback.message.answer(
            "❌ У тебя нет активного VPN.",
            reply_markup=get_back_kb(),
        )
        return

    vpn_service = VPNService(session)
    vless_url = await vpn_service.get_vless_url(user)

    # Generate new QR code
    qr_buffer = generate_qr_code(vless_url)
    qr_photo = BufferedInputFile(qr_buffer.read(), filename="vpn_qr.png")

    # Delete old and send new
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=qr_photo,
        caption=(
            f"🔗 <b>Твоя ссылка для подключения:</b>\n\n"
            f"<code>{vless_url}</code>\n\n"
            f"📷 Или отсканируй QR-код выше\n\n"
            f"📱 <b>Приложения:</b>\n"
            f"• iOS: V2RayTun, Shadowrocket\n"
            f"• Android: V2RayNG, NekoBox\n"
            f"• Windows/macOS/Linux: Hiddify, Nekoray"
        ),
        reply_markup=get_link_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_to_menu_new")
async def back_to_menu_new(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle back to menu from photo message (delete and send new)."""
    await callback.answer()

    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    has_pending = await request_repo.has_pending(user)

    # Delete photo message and send text menu
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_user_main_kb(user.has_vpn, has_pending),
    )
