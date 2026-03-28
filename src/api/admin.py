"""Admin API routes for managing VPN requests."""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.schemas import (
    AdminRequestSchema,
    BroadcastRequestSchema,
    ChatMessageSchema,
    ChatPreviewSchema,
    GenericResponse,
    SendMessageSchema,
)
from src.database.models import User
from src.database.repositories import RequestRepository, SupportRepository, UserRepository
from src.database.session import get_session
from src.services.vpn_service import VPNService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/staff", tags=["admin"])


async def _send_broadcast_task(message: str, target: str):
    from src.api.bot_utils import create_bot
    from src.database.session import session_factory

    async with create_bot() as bot:
        async with session_factory() as session:
            user_repo = UserRepository(session)
            if target == "all":
                users = await user_repo.get_all()
            elif target == "with_vpn":
                users = await user_repo.get_all_with_vpn()
            else:
                all_users = await user_repo.get_all()
                users = [u for u in all_users if not u.has_vpn]

        success = 0
        for u in users:
            try:
                await bot.send_message(
                    u.telegram_id, f"📢 <b>Объявление:</b>\n\n{message}", parse_mode="HTML"
                )
                success += 1
            except Exception as e:
                logger.warning(f"Failed to broadcast from API to {u.telegram_id}: {e}")
            await asyncio.sleep(0.05)

        logger.info(f"API Broadcast finished. Sent to {success}/{len(users)}")


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency to check if current user is admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin privileges",
        )
    return user


@router.get("/requests", response_model=list[AdminRequestSchema])
async def get_requests(
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[AdminRequestSchema]:
    """Get all pending VPN requests."""
    req_repo = RequestRepository(session)
    requests = await req_repo.get_all_pending()

    return [
        AdminRequestSchema(
            id=req.id,
            user_id=req.user.id,
            telegram_id=req.user.telegram_id,
            full_name=req.user.full_name,
            username=req.user.username,
            status=req.status.value,
            created_at=req.created_at,
            user_comment=req.user_comment,
        )
        for req in requests
    ]


@router.post("/requests/{request_id}/approve", response_model=GenericResponse)
async def approve_request(
    request_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Approve a VPN request."""

    from src.bot.config import settings

    req_repo = RequestRepository(session)
    request = await req_repo.get_by_id(request_id)
    if not request or request.status.value != "pending":
        raise HTTPException(status_code=404, detail="Pending request not found")

    vpn_service = VPNService(session)
    # Use default endpoint name
    default_endpoint = settings.endpoints[0].name if settings.endpoints else "vless"
    success, message = await vpn_service.approve_request(request_id, default_endpoint)

    if not success:
        return GenericResponse(success=False, message=message)

    # Notify user via WebSockets
    from src.api.ws import manager as ws_manager

    await ws_manager.send_personal_message({"type": "REQUEST_APPROVED"}, request.user.id)
    await ws_manager.broadcast_to_admins(
        {"type": "REQUEST_STATUS_CHANGED", "request_id": request.id, "status": "approved"}
    )

    # Notify user via Telegram bot
    from src.api.bot_utils import notify_user

    await notify_user(
        request.user.telegram_id,
        "✅ <b>Заявка одобрена!</b>\n\n"
        "Твой VPN готов. Открой приложение, чтобы получить настройки.",
        parse_mode="HTML",
    )

    return GenericResponse(success=True, message="Заявка одобрена.")


@router.post("/requests/{request_id}/reject", response_model=GenericResponse)
async def reject_request(
    request_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Reject a VPN request."""
    req_repo = RequestRepository(session)
    request = await req_repo.get_by_id(request_id)
    if not request or request.status.value != "pending":
        raise HTTPException(status_code=404, detail="Pending request not found")

    await req_repo.reject(request)

    # Notify user via WebSockets
    from src.api.ws import manager as ws_manager

    await ws_manager.send_personal_message({"type": "REQUEST_REJECTED"}, request.user.id)
    await ws_manager.broadcast_to_admins(
        {"type": "REQUEST_STATUS_CHANGED", "request_id": request.id, "status": "rejected"}
    )

    from src.api.bot_utils import notify_user

    await notify_user(
        request.user.telegram_id,
        "❌ <b>Заявка отклонена.</b>\n\nМодератор отклонил запрос.",
        parse_mode="HTML",
    )

    return GenericResponse(success=True, message="Заявка отклонена.")


@router.post("/broadcast", response_model=GenericResponse)
async def broadcast_message(
    payload: BroadcastRequestSchema,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_admin),
) -> GenericResponse:
    """Trigger a bot broadcast to users from the Mini App."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    background_tasks.add_task(_send_broadcast_task, payload.message, payload.target)
    return GenericResponse(success=True, message="Рассылка началась в фоновом режиме.")


@router.get("/chats", response_model=list[ChatPreviewSchema])
async def get_chats(
    user: User = Depends(require_admin), session: AsyncSession = Depends(get_session)
) -> list[ChatPreviewSchema]:
    support_repo = SupportRepository(session)
    chats = await support_repo.get_all_chats()

    return [
        ChatPreviewSchema(
            user_id=ch["user"].id,
            telegram_id=ch["user"].telegram_id,
            full_name=ch["user"].full_name,
            username=ch["user"].username,
            last_message=ch["last_message"].text,
            last_message_at=ch["last_message"].created_at,
            is_last_from_admin=ch["last_message"].is_from_admin,
        )
        for ch in chats
    ]


@router.get("/chats/{user_id}", response_model=list[ChatMessageSchema])
async def get_chat_history(
    user_id: int, user: User = Depends(require_admin), session: AsyncSession = Depends(get_session)
) -> list[ChatMessageSchema]:
    support_repo = SupportRepository(session)
    messages = await support_repo.get_user_chat_history(user_id)
    return [
        ChatMessageSchema(
            id=m.id, is_from_admin=m.is_from_admin, text=m.text, created_at=m.created_at
        )
        for m in messages
    ]


@router.post("/chats/{user_id}", response_model=ChatMessageSchema)
async def send_chat_message(
    user_id: int,
    payload: SendMessageSchema,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ChatMessageSchema:
    import logging

    from src.keyboards.user_reply_kb import get_reply_to_admin_kb

    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    support_repo = SupportRepository(session)
    saved_msg = await support_repo.save_message(user_id, payload.text, is_from_admin=True)
    await session.commit()

    # Dispatch to Telegram Bot
    from src.api.bot_utils import create_bot

    async with create_bot() as bot:
        try:
            await bot.send_message(
                target_user.telegram_id,
                f"💬 Сообщение от админа:\n\n{payload.text}",
                reply_markup=get_reply_to_admin_kb(),
            )
        except Exception as e:
            logging.warning(f"Failed to send direct message to {target_user.telegram_id}: {e}")

    return ChatMessageSchema(
        id=saved_msg.id,
        is_from_admin=saved_msg.is_from_admin,
        text=saved_msg.text,
        created_at=saved_msg.created_at,
    )
