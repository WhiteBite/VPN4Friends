"""Admin handlers for web access requests."""

import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import WebAccessRequest, WebAccessStatus
from src.database.repositories import UserRepository

logger = logging.getLogger(__name__)
router = Router(name="web_access")


@router.callback_query(F.data.startswith("web_access:approve_self:"))
async def approve_self_web_access(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
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

    # Security check: Make sure the person clicking is the actual user
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user or user.id != req.user_id:
        await callback.answer("❌ Это не ваш запрос", show_alert=True)
        return

    # Create JWT
    from src.api.dependencies import create_access_token

    token = create_access_token(req.user_id)

    req.status = WebAccessStatus.APPROVED
    req.jwt_token = token
    req.processed_at = datetime.now()
    await session.commit()

    await callback.message.edit_text(
        "✅ <b>Вход подтверждён</b>\n\n" "Браузер автоматически загрузит личный кабинет."
    )
    await callback.answer("Вход успешно разрешён!")
