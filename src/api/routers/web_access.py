"""Web access router — allows browser login by Telegram username.

Simplified: if user exists and has VPN, issue JWT immediately.
No admin approval needed.
"""

import logging
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import create_access_token
from src.database.repositories import UserRepository
from src.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

# Simple in-memory rate limiter: IP -> list of timestamps
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 5  # max requests per window


def _check_rate_limit(client_ip: str) -> bool:
    """Check if client IP is within rate limit. Returns True if allowed."""
    now = time.time()
    timestamps = _rate_limit_store.get(client_ip, [])
    # Remove expired entries
    timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(timestamps) >= RATE_LIMIT_MAX:
        _rate_limit_store[client_ip] = timestamps
        return False
    timestamps.append(now)
    _rate_limit_store[client_ip] = timestamps
    return True


class WebAccessRequestPayload(BaseModel):
    """Request body for web access."""

    username: str

    @field_validator("username")
    @classmethod
    def clean_username(cls, v: str) -> str:
        """Normalize username: strip @, t.me/ prefix, whitespace."""
        v = v.strip()
        v = re.sub(r"^(https?://)?(t\.me/|@)", "", v, flags=re.IGNORECASE)
        v = v.strip("/").strip()
        if not v or len(v) < 2:
            raise ValueError("Введите корректный @username")
        return v


class WebAccessResponse(BaseModel):
    request_id: int | None = None
    status: str
    token: str | None = None
    message: str


@router.post("/request-access", response_model=WebAccessResponse)
async def request_web_access(
    payload: WebAccessRequestPayload,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Request web access by Telegram username.
    If user exists and has VPN — issue JWT immediately.
    No admin approval needed.
    """
    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток. Подождите минуту.",
        )

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

    # Issue JWT immediately
    token = create_access_token(user.telegram_id)

    return WebAccessResponse(
        status="approved",
        token=token,
        message="Доступ подтверждён.",
    )
