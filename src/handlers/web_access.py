"""Admin handlers for web access requests."""

import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import create_access_token
from src.bot.config import settings
from src.bot.middlewares.admin import AdminFilter
from src.database.models import WebAccessRequest, WebAccessStatus
from src.database.repositories import UserRepository

logger = logging.getLogger(__name__)
router = Router(name="web_access")

# Apply admin filter
router.message.filter(AdminFilter(settings.admin_ids))
router.callback_query.filter(AdminFilter(settings.admin_ids))


@router.callback_query(F.data.startswith("web_access:approve:"))
async def approve_web_access(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """Approve browser login request via inline button."""
    request_id = int(callback.data.split(":")[-1])

    result = await session.execute(
        select(WebAccessRequest).where(WebAccessRequest.id == request_id)
    )
    req = result.scalar_one_or_none()

    if not req:
        await callback.answer("❌ Запрос не найден", show_alert=True)
        return

    if req.status != WebAccessStatus.PENDING:
        await callback.answer(f"⚠️ Этот запрос уже {req.status.value}", show_alert=True)
        return

    # Create JWT
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(req.user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    create_access_token(user.telegram_id)  # validates token can be created
    name = user.display_name

    await callback.message.edit_text(
        f"✅ <b>Вход разрешён</b>\n\n"
        f"Пользователь: {name}\n"
        f"Статус: Одобрено\n\n"
        f"Браузер пользователя сейчас автоматически войдет в систему.",
        parse_mode="HTML",
    )
    await callback.answer("Вход успешно разрешён!")


@router.callback_query(F.data.startswith("web_access:reject:"))
async def reject_web_access(callback: CallbackQuery, session: AsyncSession) -> None:
    """Reject browser login request."""
    request_id = int(callback.data.split(":")[-1])

    result = await session.execute(
        select(WebAccessRequest).where(WebAccessRequest.id == request_id)
    )
    req = result.scalar_one_or_none()

    if not req:
        await callback.answer("❌ Запрос не найден", show_alert=True)
        return

    if req.status != WebAccessStatus.PENDING:
        await callback.answer(f"⚠️ Этот запрос уже {req.status.value}", show_alert=True)
        return

    req.status = WebAccessStatus.REJECTED
    req.processed_at = datetime.now()
    await session.commit()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(req.user_id)
    name = user.display_name if user else f"@{req.username}"

    await callback.message.edit_text(
        f"❌ <b>Вход отклонён</b>\n\n" f"Пользователь: {name}\n" f"Статус: Отклонено",
        parse_mode="HTML",
    )
    await callback.answer()
