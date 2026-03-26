"""Server selection handlers for VPN bot."""

import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.database.repositories import UserRepository
from src.keyboards.server_kb import (
    get_back_to_servers_kb,
    get_finland_options_kb,
    get_mtproto_options_kb,
    get_netherlands_options_kb,
    get_server_list_kb,
)
from src.keyboards.user_kb import get_back_kb
from src.services.vpn_service import VPNService

logger = logging.getLogger(__name__)
router = Router(name="server_selection")


@router.callback_query(F.data == "choose_server")
async def choose_server(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show server selection menu."""
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.message.answer("❌ Пользователь не найден")
        return

    await callback.message.edit_text(
        "🌍 <b>Выбор сервера</b>\n\nВыберите локацию для подключения:",
        reply_markup=get_server_list_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "region_finland")
async def region_finland(callback: CallbackQuery) -> None:
    """Show Finland connection options."""
    await callback.answer()

    await callback.message.edit_text(
        "🇫🇮 <b>Финляндия</b>\n\n"
        "Выберите способ подключения:\n\n"
        "⚡ <b>xHTTP via Moscow</b> — рекомендуется для РФ\n"
        "📦 <b>gRPC via Moscow</b> — альтернативный\n"
        "🔗 <b>Direct</b> — прямое подключение",
        reply_markup=get_finland_options_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "region_netherlands")
async def region_netherlands(callback: CallbackQuery) -> None:
    """Show Netherlands connection options."""
    await callback.answer()

    await callback.message.edit_text(
        "🇳🇱 <b>Нидерланды</b>\n\nВыберите способ подключения:",
        reply_markup=get_netherlands_options_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "region_mtproto")
async def region_mtproto(callback: CallbackQuery) -> None:
    """Show MTProto options."""
    await callback.answer()

    await callback.message.edit_text(
        "✈️ <b>Telegram Proxy</b>\n\n"
        "Нативный прокси для Telegram.\n"
        "Работает только в Telegram (не для всего трафика).\n\n"
        "Выберите сервер:",
        reply_markup=get_mtproto_options_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("endpoint_"))
async def select_endpoint(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """Handle endpoint selection."""
    await callback.answer()

    endpoint_name = callback.data.split("endpoint_")[1]
    endpoint = settings.get_endpoint(endpoint_name)

    if not endpoint:
        await callback.message.answer("❌ Сервер не найден")
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.message.answer("❌ Пользователь не найден")
        return

    # For MTProto - just show the link
    if endpoint.protocol == "mtproto":
        mtproto_link = (
            f"tg://proxy?server={endpoint.host}"
            f"&port={endpoint.port}"
            f"&secret={endpoint.panel_config.get('secret', '')}"
        )

        await callback.message.edit_text(
            f"✈️ <b>Telegram Proxy</b>\n\n"
            f"🌐 <b>{endpoint.label}</b>\n\n"
            f"Нажмите на кнопку ниже чтобы подключиться:\n\n"
            f"🔗 <a href='{mtproto_link}'>Подключиться в Telegram</a>\n\n"
            f"<i>Или скопируйте ссылку и вставьте в Telegram</i>",
            reply_markup=get_back_to_servers_kb(),
            parse_mode="HTML",
        )
        return

    # For VLESS - check if user has VPN
    if not user.has_vpn:
        await callback.message.edit_text(
            "❌ <b>Нет VPN доступа</b>\n\nСначала получите доступ через главное меню.",
            reply_markup=get_back_kb(),
            parse_mode="HTML",
        )
        return

    # Switch user's profile to selected endpoint
    # TODO: Implement profile switching logic
    # For now - show message that switching is in development

    await callback.message.edit_text(
        f"⏳ <b>Переключение на {endpoint.label}</b>\n\n"
        f"Функция в разработке...\n\n"
        f"Пока вы можете использовать текущий VPN через главное меню.",
        reply_markup=get_back_to_servers_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back_to_servers")
async def back_to_servers(callback: CallbackQuery, session: AsyncSession) -> None:
    """Back to server selection menu."""
    await callback.answer()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if not user:
        return

    await choose_server(callback, session)
