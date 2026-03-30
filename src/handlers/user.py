"""User handlers for VPN bot."""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import create_access_token
from src.bot.config import settings
from src.database.repositories import RequestRepository, UserRepository
from src.keyboards.admin_kb import get_request_action_kb
from src.keyboards.messaging_kb import get_cancel_kb
from src.keyboards.user_kb import (
    get_back_kb,
    get_confirm_delete_kb,
    get_link_kb,
    get_locations_kb,
    get_stats_kb,
    get_user_main_kb,
)
from src.services.vpn_service import VPNService
from src.services.xui_api import XUIApi
from src.utils.formatters import format_traffic, get_dns_instructions
from src.utils.messaging import send_smart_message
from src.utils.qr_generator import generate_qr_code

logger = logging.getLogger(__name__)
router = Router(name="user")


# App download links
APP_LINKS = (
    "📱 <b>Приложения:</b>\n"
    "• iPhone → <a href='https://apps.apple.com/app/v2raytun/id6476628951'>V2RayTun</a>\n"
    "• Android → <a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>V2RayNG</a>\n"
    "• Windows/Mac → <a href='https://github.com/hiddify/hiddify-app/releases'>Hiddify</a>"
)


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

    has_pending = await request_repo.has_pending(user)

    if created:
        # New user — clean onboarding
        await message.answer(
            f"🌍 <b>VPN4Friends Premium</b>\n\n"
            f"Привет, <b>{user.full_name}</b>! 👋\n\n"
            f"Это персональный высокоскоростной VPN с обходом блокировок.\n"
            f"Нажми кнопку ниже, чтобы запросить доступ.",
            reply_markup=get_user_main_kb(user.has_vpn, has_pending),
            parse_mode="HTML",
        )
        return

    # Returning user without VPN or with VPN
    status_emoji = "🟢 Подписка активна" if user.has_vpn else "👋 С возвращением"
    await message.answer(
        f"<b>VPN4Friends</b>\n\n{status_emoji}, <b>{user.full_name}</b>!",
        reply_markup=get_user_main_kb(user.has_vpn, has_pending),
        parse_mode="HTML",
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession) -> None:
    """Handle /menu command."""
    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Нажми /start")
        return

    has_pending = await request_repo.has_pending(user)
    status_emoji = "🟢 Подписка активна" if user.has_vpn else "🔴 Нет профиля"
    await message.answer(
        f"<b>Меню управления</b>\nСтатус: {status_emoji}",
        reply_markup=get_user_main_kb(user.has_vpn, has_pending),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "📖 <b>Справка</b>\n\n"
        "Бот для бесплатного VPN от Дани.\n\n"
        "<b>Как подключиться:</b>\n"
        "1. Скачай приложение из списка ниже\n"
        "2. Скопируй ссылку из бота\n"
        "3. Вставь в приложение → Подключись\n\n"
        f"{APP_LINKS}\n\n"
        "<b>Команды:</b>\n"
        "/start — главное меню\n"
        "/link — получить ссылку\n"
        "/stats — статистика\n"
        "/help — эта справка",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Handle /status command."""
    await message.answer("⏳ Проверяю...")

    try:
        async with XUIApi() as api:
            status = await api.get_server_status()
            online_clients = await api.get_online_clients()

        online_count = len(online_clients) if online_clients else 0
        total_traffic = format_traffic(status["upload"] + status["download"])

        await message.answer(
            f"📶 Сервер: ✅ Онлайн\n"
            f"👥 Клиентов: {status['clients']}\n"
            f"🟢 Онлайн: {online_count}\n"
            f"📊 Трафик: {total_traffic}",
        )
    except Exception as e:
        logger.error(f"Server status failed: {e}")
        await message.answer("📶 Сервер: ❌ Недоступен\n\nПопробуй позже.")


@router.message(Command("link"))
async def cmd_link(message: Message, session: AsyncSession) -> None:
    """Handle /link command."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or not user.active_profile:
        await message.answer("❌ Нет VPN. Отправь заявку через /start")
        return

    # For MTProto, we just generate URL without hitting any DB info
    # For VLESS/Shadowsocks, it relies on User profile_data
    from src.services.url_generator import generate_vpn_link

    messages: list[str] = [
        f"🔗 <b>Пакет ваших ссылок ({user.active_profile.protocol_name.upper()}):</b>\n\n"
        "<i>Нажмите на любую ссылку, чтобы её скопировать. "
        "Для получения QR-кода используйте кнопки ниже.</i>\n"
    ]

    for ep in settings.endpoints:
        try:
            vpn_link = generate_vpn_link(
                protocol_name=user.active_profile.protocol_name,
                profile_data=user.active_profile.profile_data,
                settings_overrides=user.active_profile.settings,
                endpoint=ep,
            )
        except Exception as e:
            logger.error(f"Error generating link for {ep.name}: {e}")
            continue

        if vpn_link:
            proto = getattr(ep, "protocol", user.active_profile.protocol_name).upper()
            icon = "✈️" if proto == "MTPROTO" else "🌍"
            messages.append(f"{icon} <b>{ep.label} ({proto})</b>\n<code>{vpn_link}</code>\n")

    full_text = "\n".join(messages)

    await send_smart_message(
        message,
        full_text,
        reply_markup=get_locations_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(Command("subscription"))
async def cmd_subscription(message: Message, session: AsyncSession) -> None:
    """Handle /subscription command."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or not user.active_profile:
        await message.answer("❌ У вас нет активного VPN-профиля.")
        return

    client_id = user.active_profile.profile_data.get("client_id")
    if not client_id:
        await message.answer("❌ Ошибка профиля. Обратитесь в поддержку.")
        return

    sub_link = f"https://vpn4friends-api.whitebite.ru/api/sub/{client_id}"

    await message.answer(
        f"📡 <b>Ваша Авто-Подписка</b>\n\n"
        f"Скопируйте ссылку ниже и вставьте её в приложение (Throne, v2rayNG или Hiddify):\n\n"
        f"<code>{sub_link}</code>\n\n"
        f"<i>Все серверы добавятся и будут обновляться автоматически.</i>",
        parse_mode="HTML",
        reply_markup=get_back_kb(),
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    """Handle /stats command."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or not user.active_profile:
        await message.answer("❌ Нет VPN.")
        return

    vpn_service = VPNService(session)
    stats = await vpn_service.get_user_stats(user)

    if not stats:
        await message.answer("❌ Статистика недоступна.")
        return

    upload = format_traffic(stats["upload"])
    download = format_traffic(stats["download"])

    await message.answer(
        f"📊 Статистика:\n\n🔼 Upload: {upload}\n🔽 Download: {download}",
        reply_markup=get_stats_kb(),
    )


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext) -> None:
    """Handle /support command."""
    from src.handlers.messaging import FeedbackStates

    await state.set_state(FeedbackStates.waiting_for_message)
    await message.answer(
        "✉️ Напиши сообщение для Дани:",
        reply_markup=get_cancel_kb(),
    )


@router.message(Command("web"))
async def cmd_web(message: Message, session: AsyncSession) -> None:
    """Handle /web command - generate magic link for browser access."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("Нажми /start")
        return

    token = create_access_token(user.telegram_id)
    web_url = f"{settings.miniapp_url}/?token={token}"

    await message.answer(
        "🌐 <b>Вход через браузер</b>\n\n"
        "Эта ссылка позволит вам пользоваться VPN через обычный браузер (на ПК или другом устройстве) без Telegram.\n\n"
        "⚠️ <b>Внимание:</b> не передавайте эту ссылку посторонним!\n\n"
        f"🔗 <a href='{web_url}'>Ваша ссылка для входа</a>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ============ CALLBACKS ============


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
    status_emoji = "🟢 Подписка активна" if user.has_vpn else "🔴 Нет профиля"
    await callback.message.edit_text(
        f"<b>Меню управления</b>\nСтатус: {status_emoji}",
        reply_markup=get_user_main_kb(user.has_vpn, has_pending),
        parse_mode="HTML",
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
            "⚠️ У тебя уже есть VPN или заявка.",
            reply_markup=get_back_kb(),
        )
        return

    await callback.message.edit_text(
        "✅ Заявка отправлена!\n\nДаня получит уведомление. Обычно одобряю быстро ⚡",
        reply_markup=get_back_kb(),
    )

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 <b>Новая заявка!</b>\n\n"
                f"👤 {user.display_name}\n"
                f"🆔 <code>{user.telegram_id}</code>",
                reply_markup=get_request_action_kb(request),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")


@router.callback_query(F.data == "pending_info")
async def pending_info(callback: CallbackQuery) -> None:
    """Handle pending request info."""
    await callback.answer(
        "Заявка на рассмотрении. Обычно одобряю быстро ⚡",
        show_alert=True,
    )


@router.callback_query(F.data == "my_sub")
async def my_sub(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show user's auto-subscription link."""
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user or not user.active_profile:
        await callback.message.edit_text(
            "❌ У вас нет активного VPN-профиля.", reply_markup=get_back_kb()
        )
        return

    client_id = user.active_profile.profile_data.get("client_id")
    if not client_id:
        await callback.message.edit_text(
            "❌ Ошибка профиля. Обратитесь в поддержку.", reply_markup=get_back_kb()
        )
        return

    sub_link = f"https://vpn4friends-api.whitebite.ru/api/sub/{client_id}"

    await callback.message.edit_text(
        f"📡 <b>Ваша Авто-Подписка</b>\n\n"
        f"Скопируйте ссылку ниже и вставьте её в приложение (Throne, v2rayNG или Hiddify):\n\n"
        f"<code>{sub_link}</code>\n\n"
        f"<i>Все серверы добавятся и будут обновляться автоматически.</i>",
        parse_mode="HTML",
        reply_markup=get_back_kb(),
    )


@router.callback_query(F.data == "my_link")
async def my_link(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show user's VPN link with QR code."""
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user or not user.active_profile:
        await callback.message.edit_text("❌ Нет VPN.", reply_markup=get_back_kb())
        return

    await callback.answer("⏳ Собираю ссылки...")

    # For MTProto, we just generate URL without hitting any DB info
    # For VLESS/Shadowsocks, it relies on User profile_data
    from src.services.url_generator import generate_vpn_link

    messages: list[str] = [
        f"🔗 <b>Пакет ваших ссылок ({user.active_profile.protocol_name.upper()}):</b>\n\n"
        "<i>Нажмите на любую ссылку, чтобы её скопировать. "
        "Для получения QR-кода используйте кнопки ниже.</i>\n"
    ]

    for ep in settings.endpoints:
        try:
            vpn_link = generate_vpn_link(
                protocol_name=user.active_profile.protocol_name,
                profile_data=user.active_profile.profile_data,
                settings_overrides=user.active_profile.settings,
                endpoint=ep,
            )
        except Exception as e:
            logger.error(f"Error generating link for {ep.name}: {e}")
            continue

        if vpn_link:
            proto = getattr(ep, "protocol", user.active_profile.protocol_name).upper()
            icon = "✈️" if proto == "MTPROTO" else "🌍"
            messages.append(f"{icon} <b>{ep.label} ({proto})</b>\n<code>{vpn_link}</code>\n")

    full_text = "\n".join(messages)

    await send_smart_message(
        callback.message,
        full_text,
        reply_markup=get_locations_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.callback_query(F.data.startswith("get_link:"))
async def generate_specific_link(callback: CallbackQuery, session: AsyncSession) -> None:
    """Generate link and QR code for a specific server location."""
    endpoint_name = callback.data.split(":")[1]

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(
        callback.fromuser.id if hasattr(callback, "fromuser") else callback.from_user.id
    )
    if not user or not user.active_profile:
        await callback.answer("❌ Нет профиля.", show_alert=True)
        return

    endpoint = settings.get_endpoint(endpoint_name)
    if not endpoint:
        await callback.answer("❌ Сервер не найден.", show_alert=True)
        return

    await callback.answer("⏳ Создаю ссылку...")

    # For MTProto, we just generate URL without hitting any DB info
    # For VLESS/Shadowsocks, it relies on User profile_data
    from src.services.url_generator import generate_vpn_link

    try:
        vpn_link = generate_vpn_link(
            protocol_name=user.active_profile.protocol_name,
            profile_data=user.active_profile.profile_data,
            settings_overrides=user.active_profile.settings,
            endpoint=endpoint,
        )
    except Exception as e:
        logger.error(f"Error generating link for {endpoint.name}: {e}")
        vpn_link = None

    if not vpn_link:
        await callback.message.edit_text("❌ Ошибка генерации ссылки.", reply_markup=get_back_kb())
        return

    qr_buffer = generate_qr_code(vpn_link)
    qr_photo = BufferedInputFile(qr_buffer.read(), filename="vpn_qr.png")
    proto = getattr(endpoint, "protocol", user.active_profile.protocol_name).upper()

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=qr_photo,
        caption=(
            f"🔗 <b>{endpoint.label} ({proto})</b>\n\n"
            f"<code>{vpn_link}</code>\n\n"
            f"📷 Или отсканируй QR выше"
            f"{get_dns_instructions()}\n\n"
            f"{APP_LINKS}"
        ),
        reply_markup=get_link_kb(endpoint.name),
        parse_mode="HTML",
    )


@router.callback_query(F.data.in_(["my_stats", "refresh_stats"]))
async def my_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show user's traffic statistics."""
    if callback.data == "refresh_stats":
        await callback.answer("🔄 Обновляю...")
    else:
        await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user or not user.active_profile:
        await callback.message.edit_text("❌ Нет VPN.", reply_markup=get_back_kb())
        return

    vpn_service = VPNService(session)
    stats = await vpn_service.get_user_stats(user)

    if not stats:
        await callback.message.edit_text("❌ Статистика недоступна.", reply_markup=get_back_kb())
        return

    upload = format_traffic(stats["upload"])
    download = format_traffic(stats["download"])

    await callback.message.edit_text(
        f"📊 Статистика:\n\n🔼 Upload: {upload}\n🔽 Download: {download}",
        reply_markup=get_stats_kb(),
    )


@router.callback_query(F.data == "delete_vpn")
async def delete_vpn(callback: CallbackQuery) -> None:
    """Confirm VPN deletion."""
    await callback.answer()
    await callback.message.edit_text(
        "⚠️ Удалить VPN?\n\nПридётся заново отправлять заявку.",
        reply_markup=get_confirm_delete_kb(),
    )


@router.callback_query(F.data == "confirm_delete_vpn")
async def confirm_delete_vpn(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle VPN deletion."""
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    vpn_service = VPNService(session)
    success = await vpn_service.revoke_vpn(user)

    if success:
        await callback.message.edit_text(
            "✅ VPN удалён.\n\nМожешь отправить новую заявку.",
            reply_markup=get_user_main_kb(has_vpn=False),
        )
    else:
        await callback.message.edit_text("❌ Ошибка.", reply_markup=get_back_kb())


@router.callback_query(F.data.startswith("refresh_link:"))
async def refresh_link(callback: CallbackQuery, session: AsyncSession) -> None:
    """Refresh VPN link."""
    await callback.answer("🔄 Обновляю...")

    endpoint_name = callback.data.split(":")[1]

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user or not user.active_profile:
        await callback.message.delete()
        await callback.message.answer("❌ Нет VPN.", reply_markup=get_back_kb())
        return

    endpoint = (
        settings.get_endpoint(endpoint_name)
        if endpoint_name and endpoint_name != "default"
        else None
    )

    if not endpoint:
        # Fallback to general menu if endpoint not found
        await callback.message.delete()
        await callback.message.answer(
            "🌍 <b>Выберите локацию для подключения:</b>",
            reply_markup=get_locations_kb(),
            parse_mode="HTML",
        )
        return

    from src.services.url_generator import generate_vpn_link

    try:
        vpn_link = generate_vpn_link(
            protocol_name=user.active_profile.protocol_name,
            profile_data=user.active_profile.profile_data,
            settings_overrides=user.active_profile.settings,
            endpoint=endpoint,
        )
    except Exception as e:
        logger.error(f"Error refreshing link for {endpoint.name}: {e}")
        vpn_link = None

    if not vpn_link:
        await callback.message.delete()
        await callback.message.answer("❌ Ошибка.", reply_markup=get_back_kb())
        return

    qr_buffer = generate_qr_code(vpn_link)
    qr_photo = BufferedInputFile(qr_buffer.read(), filename="vpn_qr.png")
    proto = getattr(endpoint, "protocol", user.active_profile.protocol_name).upper()

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=qr_photo,
        caption=(
            f"🔗 <b>{endpoint.label} ({proto})</b>\n\n"
            f"<code>{vpn_link}</code>\n\n"
            f"📷 Или отсканируй QR выше\n\n"
            f"{APP_LINKS}"
        ),
        reply_markup=get_link_kb(endpoint.name),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_to_menu_new")
async def back_to_menu_new(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle back to menu from photo message."""
    await callback.answer()

    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    has_pending = await request_repo.has_pending(user)
    await callback.message.delete()
    await callback.message.answer(
        "🏠 Меню",
        reply_markup=get_user_main_kb(user.has_vpn, has_pending),
    )
