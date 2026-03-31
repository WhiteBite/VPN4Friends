"""Web access router — allows browser login by Telegram username.

Flow:
1. User has VPN → instant JWT
2. User exists but no VPN → create VPNRequest, return poll_token
3. User not found → create User (fake tg_id), create VPNRequest, return poll_token

Frontend polls /api/auth/poll-status to wait for admin approval.
"""

import contextlib
import logging
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import create_access_token
from src.database.models import RequestStatus, User, VPNRequest, WebAccessRequest, WebAccessStatus
from src.database.repositories import RequestRepository, UserRepository
from src.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

# Simple in-memory rate limiter: IP -> list of timestamps
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10  # max requests per window


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
    poll_token: str | None = None


@router.post("/request-access", response_model=WebAccessResponse)
async def request_web_access(
    payload: WebAccessRequestPayload,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Request web access by Telegram username.

    - User exists + has VPN → instant JWT
    - User exists + no VPN → create VPN request, return poll_token for polling
    - User not found → create user + VPN request, return poll_token
    """
    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток. Подождите минуту.",
        )

    username = payload.username
    user_repo = UserRepository(session)
    user = await user_repo.get_by_username(username)

    # --- Case A: User exists and has VPN → instant login ---
    if user and user.has_vpn:
        token = create_access_token(user.telegram_id)
        return WebAccessResponse(
            status="approved",
            token=token,
            message="Доступ подтверждён.",
        )

    # --- Cases B & C: need admin approval ---

    # Case C: user not found → create with fake telegram_id
    if not user:
        fake_tg_id = -int(time.time() * 1000)  # negative millisecond timestamp
        user = await user_repo.create(
            telegram_id=fake_tg_id,
            full_name=f"@{username}",
            username=username,
        )
        logger.info(f"Created browser-only user @{username} with fake tg_id={fake_tg_id}")

    # Check for existing pending request
    req_repo = RequestRepository(session)
    existing_pending = await req_repo.get_pending_by_user(user)

    if existing_pending:
        # Already has pending request — find or create poll token
        poll_wa = await _get_or_create_poll_token(session, user, existing_pending)
        return WebAccessResponse(
            status="pending",
            request_id=existing_pending.id,
            poll_token=str(poll_wa.id),
            message="Ваша заявка уже на рассмотрении. Ожидайте одобрения администратором.",
        )

    # Create new VPN request
    vpn_request = await req_repo.create(
        user,
        user_comment=f"Заявка из браузера (@{username})",
    )

    # Create poll token (WebAccessRequest row)
    poll_wa = WebAccessRequest(
        username=username,
        user_id=user.id,
        status=WebAccessStatus.PENDING,
        otp_code=None,
    )
    session.add(poll_wa)
    await session.commit()
    await session.refresh(poll_wa)

    # Notify admins via Telegram
    await _notify_admins_new_request(user, vpn_request)

    return WebAccessResponse(
        status="pending",
        request_id=vpn_request.id,
        poll_token=str(poll_wa.id),
        message="Заявка отправлена! Ожидайте одобрения администратором.",
    )


async def _get_or_create_poll_token(
    session: AsyncSession, user: User, vpn_request: VPNRequest
) -> WebAccessRequest:
    """Get existing or create new WebAccessRequest for polling."""
    result = await session.execute(
        select(WebAccessRequest)
        .where(
            WebAccessRequest.user_id == user.id,
            WebAccessRequest.status == WebAccessStatus.PENDING,
        )
        .order_by(WebAccessRequest.created_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    wa = WebAccessRequest(
        username=user.username or "",
        user_id=user.id,
        status=WebAccessStatus.PENDING,
    )
    session.add(wa)
    await session.commit()
    await session.refresh(wa)
    return wa


async def _notify_admins_new_request(user: User, vpn_request: VPNRequest) -> None:
    """Send notifications to admins about new VPN request."""
    from src.api.bot_utils import create_bot
    from src.api.ws import manager as ws_manager
    from src.bot.config import settings
    from src.keyboards.admin_kb import get_request_action_kb

    display_name = f"@{user.username}" if user.username else user.full_name
    msg_text = (
        f"🔔 <b>Новая заявка (из браузера)!</b>\n\n"
        f"👤 {display_name}\n"
        f"🆔 <code>{user.telegram_id}</code>"
    )
    if vpn_request.user_comment:
        msg_text += f"\n💬 <b>Комментарий:</b> {vpn_request.user_comment}"

    # Telegram notification
    with contextlib.suppress(Exception):
        async with create_bot() as bot:
            for admin_id in settings.admin_ids:
                with contextlib.suppress(Exception):
                    await bot.send_message(
                        admin_id,
                        msg_text,
                        reply_markup=get_request_action_kb(vpn_request),
                        parse_mode="HTML",
                    )

    # WebSocket notification
    with contextlib.suppress(Exception):
        await ws_manager.broadcast_to_admins(
            {
                "type": "NEW_REQUEST",
                "request_id": vpn_request.id,
                "user_id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "comment": vpn_request.user_comment,
            }
        )


# ---- Poll endpoint ----


class PollStatusResponse(BaseModel):
    status: str  # "pending" | "approved" | "rejected"
    token: str | None = None
    message: str


@router.get("/poll-status", response_model=PollStatusResponse)
async def poll_status(
    poll_token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Poll the status of a web access request.
    Returns JWT when the VPN request has been approved.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком частые запросы.",
        )

    try:
        wa_id = int(poll_token)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid poll token") from None

    result = await session.execute(select(WebAccessRequest).where(WebAccessRequest.id == wa_id))
    wa = result.scalar_one_or_none()
    if not wa:
        raise HTTPException(status_code=404, detail="Poll token not found")

    # If we already issued a JWT for this poll token, return it
    if wa.status == WebAccessStatus.APPROVED and wa.jwt_token:
        return PollStatusResponse(
            status="approved",
            token=wa.jwt_token,
            message="Доступ одобрен!",
        )

    if wa.status == WebAccessStatus.REJECTED:
        return PollStatusResponse(
            status="rejected",
            message="Заявка отклонена администратором.",
        )

    # Check if the user now has VPN (admin approved the VPNRequest)
    if wa.user_id:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(wa.user_id)

        if user and user.has_vpn:
            # User got VPN! Issue JWT and mark WebAccessRequest as approved
            token = create_access_token(user.telegram_id)
            wa.status = WebAccessStatus.APPROVED
            wa.jwt_token = token
            await session.commit()

            return PollStatusResponse(
                status="approved",
                token=token,
                message="Доступ одобрен!",
            )

        # Also check if the latest VPNRequest was rejected
        latest_req_result = await session.execute(
            select(VPNRequest)
            .where(VPNRequest.user_id == wa.user_id)
            .order_by(VPNRequest.created_at.desc())
            .limit(1)
        )
        latest_req = latest_req_result.scalar_one_or_none()
        if latest_req and latest_req.status == RequestStatus.REJECTED:
            wa.status = WebAccessStatus.REJECTED
            await session.commit()
            return PollStatusResponse(
                status="rejected",
                message="Заявка отклонена администратором.",
            )

    return PollStatusResponse(
        status="pending",
        message="Ожидание одобрения администратором...",
    )
