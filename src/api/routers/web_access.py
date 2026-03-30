"""Web access router — allows browser login by Telegram username."""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.bot_utils import create_bot
from src.bot.config import settings
from src.database.models import WebAccessRequest, WebAccessStatus
from src.database.repositories import UserRepository
from src.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


class WebAccessRequestPayload(BaseModel):
    """Request body for web access."""

    username: str

    @field_validator("username")
    @classmethod
    def clean_username(cls, v: str) -> str:
        """Normalize username: strip @, t.me/ prefix, whitespace."""
        v = v.strip()
        # Handle t.me/username and @username formats
        v = re.sub(r"^(https?://)?(t\.me/|@)", "", v, flags=re.IGNORECASE)
        v = v.strip("/").strip()
        if not v or len(v) < 2:
            raise ValueError("Введите корректный @username")
        return v


class WebAccessResponse(BaseModel):
    request_id: int
    status: str
    message: str


class WebAccessStatusResponse(BaseModel):
    status: str
    token: str | None = None


@router.post("/request-access", response_model=WebAccessResponse)
async def request_web_access(
    payload: WebAccessRequestPayload,
    session: AsyncSession = Depends(get_session),
):
    """
    Request web access by Telegram username.
    Creates a pending request and notifies admin via bot.
    """
    username = payload.username

    # Check if user exists in our database
    user_repo = UserRepository(session)
    user = await user_repo.get_by_username(username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь @{username} не найден. Сначала напишите боту @whitebite_vpn_bot",
        )

    if not user.has_vpn:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"У @{username} ещё нет VPN-доступа. Запросите доступ через бота.",
        )

    # Check for existing pending request
    existing = await session.execute(
        select(WebAccessRequest).where(
            WebAccessRequest.user_id == user.id,
            WebAccessRequest.status == WebAccessStatus.PENDING,
        )
    )
    existing_req = existing.scalar_one_or_none()
    if existing_req:
        return WebAccessResponse(
            request_id=existing_req.id,
            status="pending",
            message="Запрос уже отправлен. Ожидайте подтверждения.",
        )

    # Check for existing approved request (auto-login)
    approved = await session.execute(
        select(WebAccessRequest).where(
            WebAccessRequest.user_id == user.id,
            WebAccessRequest.status == WebAccessStatus.APPROVED,
            WebAccessRequest.jwt_token.isnot(None),
        )
    )
    approved_req = approved.scalar_one_or_none()
    if approved_req:
        return WebAccessResponse(
            request_id=approved_req.id,
            status="approved",
            message="Доступ уже подтверждён.",
        )

    # Create new request
    req = WebAccessRequest(
        username=username,
        user_id=user.id,
        status=WebAccessStatus.PENDING,
    )
    session.add(req)
    await session.commit()
    await session.refresh(req)

    # Notify admin via bot
    try:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Одобрить",
                        callback_data=f"web_access:approve:{req.id}",
                    ),
                    InlineKeyboardButton(
                        text="❌ Отклонить",
                        callback_data=f"web_access:reject:{req.id}",
                    ),
                ]
            ]
        )

        async with create_bot() as bot:
            for admin_id in settings.admin_ids:
                try:
                    await bot.send_message(
                        admin_id,
                        f"🌐 <b>Запрос веб-доступа</b>\n\n"
                        f"Пользователь <b>@{username}</b> ({user.full_name})\n"
                        f"запрашивает вход через браузер.\n\n"
                        f"ID запроса: #{req.id}",
                        reply_markup=kb,
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning(f"Failed to notify admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")

    return WebAccessResponse(
        request_id=req.id,
        status="pending",
        message="Запрос отправлен! Ожидайте подтверждения от администратора.",
    )


@router.get("/access-status/{request_id}", response_model=WebAccessStatusResponse)
async def check_web_access_status(
    request_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Poll the status of a web access request."""
    result = await session.execute(
        select(WebAccessRequest).where(WebAccessRequest.id == request_id)
    )
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(status_code=404, detail="Запрос не найден")

    if req.status == WebAccessStatus.APPROVED and req.jwt_token:
        return WebAccessStatusResponse(status="approved", token=req.jwt_token)
    elif req.status == WebAccessStatus.REJECTED:
        return WebAccessStatusResponse(status="rejected")
    else:
        return WebAccessStatusResponse(status="pending")
