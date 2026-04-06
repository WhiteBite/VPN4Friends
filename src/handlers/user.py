import contextlib

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import create_access_token
from src.bot.config import settings
from src.bot.messages import HELP_TEXT, ONBOARDING_TEXT
from src.database.models import UIMode
from src.database.repositories import RequestRepository, UserRepository
from src.handlers.messaging import FeedbackStates
from src.keyboards.admin_kb import get_request_action_kb
from src.keyboards.messaging_kb import get_cancel_kb
from src.keyboards.onboarding_kb import (
    get_android_onboarding_kb,
    get_iphone_onboarding_kb,
    get_onboarding_kb,
)
from src.keyboards.user_kb import (
    get_back_kb,
    get_confirm_delete_kb,
    get_ui_selection_kb,
    get_user_main_kb,
)
from src.services.ui_service import UIService
from src.services.vpn_service import VPNService

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

    # NEW: If UI mode is not set, force selection
    if user.ui_mode == UIMode.NONE:
        await message.answer(
            f"🌍 <b>VPN4Friends</b>\n\n"
            f"Привет, <b>{user.full_name}</b>! 👋\n\n"
            f"Выберите, как вам удобнее пользоваться нашим сервисом:\n\n"
            f"🚀 <b>Mini App</b> — современный интерфейс в одно касание (Рекомендуется)\n"
            f"🤖 <b>Чат-бот</b> — классическое управление через сообщения\n\n"
            f"<i>Вы всегда сможете сменить режим в настройках.</i>",
            reply_markup=get_ui_selection_kb(),
            parse_mode="HTML",
        )
        return

    # Existing user with selected UI mode
    ui_service = UIService(session, bot)
    await ui_service.set_user_ui_mode(user, user.ui_mode)

    has_vpn = user.has_vpn
    has_pending = await request_repo.has_pending(user)

    status_text = "🟢 <b>Подписка активна</b>" if has_vpn else "👋 <b>С возвращением</b>"
    await message.answer(
        f"<b>VPN4Friends</b>\n\n{status_text}\nПривет, <b>{user.full_name}</b>!",
        reply_markup=get_user_main_kb(has_vpn=has_vpn, has_pending=has_pending),
        parse_mode="HTML",
    )


@router.message(Command("app"))
async def cmd_switch_mode(message: Message, session: AsyncSession, bot: Bot) -> None:
    """Show UI mode selection."""
    await message.answer(
        "🌍 <b>VPN4Friends</b>\n\nВыберите режим интерфейса:\n\n"
        "🚀 <b>Mini App</b> — современный интерфейс (Рекомендуется)\n"
        "🤖 <b>Чат-бот</b> — классическое управление через сообщения",
        reply_markup=get_ui_selection_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("set_ui_mode:"))
async def set_ui_mode(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """Set preferred UI mode and show main menu."""
    mode_str = callback.data.split(":")[1]
    mode = UIMode.MINIAPP if mode_str == "miniapp" else UIMode.BOT

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer("Ошибка: пользователь не найден. Пропишите /start")
        return

    ui_service = UIService(session, bot)
    await ui_service.set_user_ui_mode(user, mode)

    request_repo = RequestRepository(session)
    has_pending = await request_repo.has_pending(user)
    has_vpn = user.has_vpn

    if mode == UIMode.BOT:
        await callback.message.edit_text(
            "🤖 <b>Режим чат-бота активирован!</b>\n\n"
            "Теперь вы можете управлять своим VPN через сообщения.\n"
            "Используйте кнопки меню ниже:",
            parse_mode="HTML",
        )
        # Explicitly send main menu to show it's working
        await callback.message.answer(
            "📱 <b>Главное меню (Чат-бот)</b>",
            reply_markup=get_user_main_kb(has_vpn=has_vpn, has_pending=has_pending),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "🚀 <b>Режим Mini App активирован!</b>\n\n"
            "Используйте кнопку <b>🚀 Открыть</b> в меню для доступа к кабинету (она появится через момент).",
            reply_markup=get_user_main_kb(has_vpn=has_vpn, has_pending=has_pending),
            parse_mode="HTML",
        )

    await callback.answer("Режим изменен!")


@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession) -> None:
    """Handle /menu command."""
    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Нажми /start")
        return

    if user.ui_mode == UIMode.NONE:
        return await cmd_start(message, session, None)

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
        HELP_TEXT,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext) -> None:
    """Handle /support command."""
    await state.set_state(FeedbackStates.waiting_for_message)
    await message.answer(
        "✉️ Напиши сообщение для Дани:",
        reply_markup=get_cancel_kb(),
    )


@router.message(Command("link"))
async def cmd_link(message: Message, session: AsyncSession) -> None:
    """Handle /link command - show VPN link immediately."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or not user.has_vpn:
        await message.answer("У вас нет активного VPN. Получите доступ через /start")
        return

    msg = await message.answer("Загрузка...")
    vpn_service = VPNService(session)
    links = await vpn_service.get_all_active_vpn_links(user)

    if links:
        lines = ["🔗 <b>Твои персональные ссылки для подключения:</b>\n"]

        # Add subscription link at the top
        client_id = user.active_profile.client_id if user.active_profile else ""
        if client_id:
            sub_url = f"{settings.miniapp_url}/api/sub/{client_id}"
            lines.append(f"📦 <b>АВТО-ПОДПИСКА (Рекомендуется)</b>:\n<code>{sub_url}</code>\n")

        for label, link in links:
            if link.startswith("tg://"):
                lines.append(f"• <b>{label}</b>: <a href='{link}'>Нажми для подключения</a>\n")
            else:
                lines.append(f"• <b>{label}</b>:\n<code>{link}</code>\n")

        lines.append(
            "Просто скопируй нужную ссылку (нажми на текст) и добавь в приложение <b>v2rayNG</b> (Android) или <b>V2RayTun / V2Box</b> (iPhone)."
        )

        lines.append(
            "\n🤝 <b>Хочешь поделиться с друзьями?</b>\n"
            "Если у них пока нет VPN, просто отправь им ссылку на наш кабинет:\n"
            f"🔗 {settings.miniapp_url}\n"
            "Там они смогут оставить заявку и получить доступ!"
        )

        from src.utils.messaging import send_smart_message

        await msg.delete()
        await send_smart_message(
            message,
            "\n".join(lines),
            disable_web_page_preview=True,
        )
    else:
        await msg.edit_text(
            "⚠️ Не удалось сформировать ссылки. Возможно, профиль еще не синхронизирован."
        )


@router.message(F.text, ~F.text.startswith("/"))
async def miniapp_mode_responder(message: Message, ui_mode: UIMode) -> None:
    """Politely remind users to use the Mini App button if they are in that mode."""
    if ui_mode != UIMode.MINIAPP:
        return  # Let other handlers (or lack thereof) deal with it

    await message.answer(
        "👋 <b>Вы в режиме Mini App!</b>\n\n"
        "Бот не реагирует на текстовые сообщения в этом режиме. "
        "Пожалуйста, используйте кнопку <b>'🚀 Открыть'</b> внизу для управления VPN.\n\n"
        "<i>Если хотите вернуться к классическому управлению через чат, введите /start.</i>",
        parse_mode="HTML",
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
        "Ссылка для входа в кабинет без Telegram.\n\n"
        "⚠️ <b>Не передавайте ссылку посторонним!</b>\n\n"
        f"🔗 <a href='{web_url}'>Открыть кабинет в браузере</a>",
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


@router.callback_query(F.data == "back_to_menu_new")
async def back_to_menu_new(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle back to menu from photo message (delete + new msg)."""
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


@router.callback_query(F.data == "show_my_vpn")
async def show_my_vpn(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle request to show the user's VPN link."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user or not user.has_vpn:
        await callback.answer("У вас нет активного VPN.", show_alert=True)
        return

    await callback.answer("Загрузка...")
    vpn_service = VPNService(session)
    links = await vpn_service.get_all_active_vpn_links(user)

    if links:
        lines = ["🔗 <b>Твои персональные ссылки для подключения:</b>\n"]

        # Add subscription link at the top
        client_id = user.active_profile.client_id if user.active_profile else ""
        if client_id:
            sub_url = f"{settings.miniapp_url}/api/sub/{client_id}"
            lines.append(f"📦 <b>АВТО-ПОДПИСКА (Рекомендуется)</b>:\n<code>{sub_url}</code>\n")

        for label, link in links:
            if link.startswith("tg://"):
                lines.append(f"• <b>{label}</b>: <a href='{link}'>Нажми для подключения</a>\n")
            else:
                lines.append(f"• <b>{label}</b>:\n<code>{link}</code>\n")

        lines.append(
            "Просто скопируй нужную ссылку (нажми на текст) и добавь в приложение <b>v2rayNG</b> (Android) или <b>V2RayTun / V2Box</b> (iPhone)."
        )

        from src.utils.messaging import send_smart_message

        await send_smart_message(
            callback.message,
            "\n".join(lines),
            disable_web_page_preview=True,
            reply_markup=get_back_kb(),
            edit=True,
        )

    else:
        await callback.message.edit_text(
            "⚠️ Не удалось сформировать ссылки. Возможно, профиль еще не синхронизирован.",
            reply_markup=get_back_kb(),
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
        if user.username:
            mention = f"<a href='https://t.me/{user.username}'>@{user.username}</a>"
        else:
            mention = f"<b>{user.full_name}</b>"

        msg_text = f"🔔 <b>Новая заявка!</b>\n\n👤 {mention}\n🆔 <code>{user.telegram_id}</code>"
        if request.protocol:
            msg_text += f"\n🔌 <b>Протокол:</b> {request.protocol}"
        if request.location:
            msg_text += f"\n📍 <b>Локация:</b> {request.location}"

        with contextlib.suppress(Exception):
            await bot.send_message(
                admin_id,
                msg_text,
                reply_markup=get_request_action_kb(request),
                parse_mode="HTML",
            )


@router.callback_query(F.data == "pending_info")
async def pending_info(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle pending request info — show date and cancel option."""
    request_repo = RequestRepository(session)
    user_repo = UserRepository(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    pending = await request_repo.get_pending_for_user(user)
    if pending:
        date_str = pending.created_at.strftime("%d.%m.%Y %H:%M")
        await callback.answer(
            f"Заявка подана: {date_str}\nОбычно одобряю быстро ⚡",
            show_alert=True,
        )
    else:
        await callback.answer("Нет активных заявок.", show_alert=True)


@router.callback_query(F.data == "cancel_request")
async def cancel_request(callback: CallbackQuery, session: AsyncSession) -> None:
    """Cancel a pending VPN request."""
    await callback.answer()

    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        return

    cancelled = await request_repo.cancel_pending(user)
    if cancelled:
        await session.commit()
        await callback.message.edit_text(
            "✅ Заявка отменена.\n\nМожешь подать новую в любой момент.",
            reply_markup=get_user_main_kb(has_vpn=False, has_pending=False),
        )
    else:
        await callback.message.edit_text(
            "ℹ️ Нет активных заявок для отмены.",
            reply_markup=get_user_main_kb(has_vpn=False, has_pending=False),
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


# ============ ONBOARDING ============


@router.callback_query(F.data == "how_to_connect")
async def how_to_connect(callback: CallbackQuery) -> None:
    """Show platform choice for instructions."""
    await callback.answer()

    text = (
        "📱 <b>Инструкции по настройке VPN</b>\n\n"
        "Выберите ваше устройство, чтобы получить подробную пошаговую инструкцию:"
    )

    if callback.message.content_type == "photo":
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_onboarding_kb(), parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=get_onboarding_kb(), parse_mode="HTML")


@router.callback_query(F.data.in_({"how_to_iphone", "how_to_android", "how_to_desktop"}))
async def show_onboarding(callback: CallbackQuery) -> None:
    """Show specific visual guide for chosen platform."""
    await callback.answer("Загружаю инструкцию...")

    platform = callback.data.split("_")[2]
    media_path = f"src/bot/media/{platform}_onboarding.png"

    kb_map = {
        "iphone": get_iphone_onboarding_kb(),
        "android": get_android_onboarding_kb(),
        "desktop": get_onboarding_kb(),
    }

    import os

    if os.path.exists(media_path):
        photo = FSInputFile(media_path)
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photo,
            caption=ONBOARDING_TEXT[platform],
            reply_markup=kb_map[platform],
            parse_mode="HTML",
        )
    elif callback.message.content_type == "text":
        await callback.message.edit_text(
            ONBOARDING_TEXT[platform], reply_markup=kb_map[platform], parse_mode="HTML"
        )
    else:
        await callback.message.delete()
        await callback.message.answer(
            ONBOARDING_TEXT[platform], reply_markup=kb_map[platform], parse_mode="HTML"
        )
