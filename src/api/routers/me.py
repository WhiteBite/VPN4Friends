import contextlib
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.bot_utils import create_bot
from src.api.dependencies import get_current_user
from src.api.schemas import (
    GenericResponse,
    LinkResponse,
    MeResponse,
    PresetSchema,
    ProfileSchema,
    RequestVPNSchema,
    SelectEndpointRequest,
    StatsResponse,
    SwitchProtocolRequest,
    SwitchProtocolResponse,
    UserSchema,
)
from src.api.ws import manager as ws_manager
from src.bot.config import settings
from src.database.models import User, VPNRequest
from src.database.repositories import RequestRepository, UserRepository
from src.database.session import get_session
from src.services import PresetService, VPNService
from src.services.url_generator import generate_vpn_link

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["Me"])


def format_bytes(b: int) -> str:
    """Format bytes into a human-readable string."""
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PiB"


@router.get("", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    """Get consolidated state for the current user."""

    preset_service = PresetService(session)

    user_schema = UserSchema(
        full_name=user.full_name,
        username=user.username,
        is_admin=user.is_admin,
    )


    # Get profile info
    active_profile = user.active_profile
    if active_profile:
        # Determine current endpoint (default or from settings)
        endpoint_name = (active_profile.settings or {}).get("endpoint") or "finland_tcp"
        endpoint = settings.get_endpoint(endpoint_name)

        # Fallback if endpoint not found
        if not endpoint:
            for ep in settings.endpoints:
                if ep.protocol == "vless":
                    endpoint = ep
                    break

        # Self-healing: if client_id column is empty but present in profile_data, fix it
        db_client_id = active_profile.client_id
        if not db_client_id and active_profile.profile_data:
            db_client_id = active_profile.profile_data.get(
                "client_id"
            ) or active_profile.profile_data.get("id")
            if db_client_id:
                active_profile.client_id = db_client_id
                user_repo = UserRepository(session)
                await user_repo.update_vpn_profile(active_profile)

        profile_schema = ProfileSchema(
            has_profile=True,
            request_status="approved",
            protocol=active_profile.protocol_name,
            label=endpoint.label if endpoint else active_profile.label,
            client_id=db_client_id,
            sni=endpoint.sni if endpoint else None,
        )
    else:
        req = await session.execute(
            select(VPNRequest)
            .where(VPNRequest.user_id == user.id)
            .order_by(VPNRequest.created_at.desc())
            .limit(1)
        )
        latest_req = req.scalar_one_or_none()
        request_status = latest_req.status.value if latest_req else None

        profile_schema = ProfileSchema(has_profile=False, request_status=request_status)

    # Get presets info
    presets = await preset_service.get_user_presets(user)
    presets_schema = [
        PresetSchema(id=p.id, name=p.name, app_type=p.app_type, format=p.format) for p in presets
    ]

    # Build subscription URL if user has active profile
    subscription_url = None
    if active_profile:
        cid = active_profile.client_id or active_profile.profile_data.get("client_id")
        if cid:
            # Origin resolution for full URL (important for MiniApp)
            subscription_url = f"/api/sub/{cid}"

    return MeResponse(
        user=user_schema,
        profile=profile_schema,
        presets=presets_schema,
        subscription_url=subscription_url,
    )


@router.post("/protocol", response_model=SwitchProtocolResponse)
async def switch_protocol(
    payload: SwitchProtocolRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SwitchProtocolResponse:
    """Switch the user's active VPN protocol.

    Creates a new profile for the requested protocol and returns a fresh link.
    """
    vpn_service = VPNService(session)
    success, result = await vpn_service.switch_protocol(user, payload.protocol)

    if not success:
        return SwitchProtocolResponse(success=False, message=result)

    return SwitchProtocolResponse(
        success=True,
        message="Протокол успешно переключён.",
        protocol=payload.protocol,
        link=result,
    )



@router.get("/link", response_model=LinkResponse)
async def get_link(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LinkResponse:
    """Get the VPN connection link for the user's active profile."""
    active_profile = user.active_profile
    if not active_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет активного VPN-профиля.",
        )

    endpoint_name = (active_profile.settings or {}).get("endpoint")
    endpoint = settings.get_endpoint(endpoint_name) if endpoint_name else None

    link = generate_vpn_link(
        active_profile.protocol_name,
        active_profile.profile_data,
        active_profile.settings,
        endpoint=endpoint,
    )

    if not link:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сгенерировать VPN-ссылку.",
        )

    return LinkResponse(
        link=link,
        protocol=active_profile.protocol_name,
        endpoint=endpoint_name,
    )


@router.delete("/revoke", response_model=GenericResponse)
async def revoke_vpn(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Revoke user's VPN access (delete profile)."""
    if not user.active_profile:
        return GenericResponse(
            success=False,
            message="У вас нет активного VPN-профиля.",
        )

    vpn_service = VPNService(session)
    success = await vpn_service.revoke_vpn(user)

    if not success:
        return GenericResponse(
            success=False,
            message="Не удалось отозвать VPN. Попробуйте позже.",
        )

    return GenericResponse(
        success=True,
        message="Ваш VPN успешно удален.",
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StatsResponse:
    """Get traffic statistics for the user's active VPN profile."""
    vpn_service = VPNService(session)
    stats = await vpn_service.get_user_stats(user)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет активного VPN-профиля или нет данных.",
        )

    upload = stats.get("upload", 0)
    download = stats.get("download", 0)

    return StatsResponse(
        protocol=stats.get("protocol", "unknown"),
        upload=upload,
        download=download,
        upload_formatted=format_bytes(upload),
        download_formatted=format_bytes(download),
    )


@router.post("/endpoint", response_model=GenericResponse)
async def select_endpoint_route(
    payload: SelectEndpointRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Select a server endpoint for the user's VPN link generation."""
    endpoint = settings.get_endpoint(payload.endpoint)
    if not endpoint:
        return GenericResponse(
            success=False,
            message=f"Точка входа '{payload.endpoint}' не найдена.",
        )

    active_profile = user.active_profile
    if not active_profile:
        return GenericResponse(
            success=False,
            message="Нет активного VPN-профиля.",
        )

    new_settings = dict(active_profile.settings or {})
    new_settings["endpoint"] = payload.endpoint
    active_profile.settings = new_settings

    user_repo = UserRepository(session)
    await user_repo.update_vpn_profile(active_profile)

    return GenericResponse(
        success=True,
        message=f"Точка входа изменена на '{endpoint.label}'.",
    )


@router.post("/request", response_model=GenericResponse)
async def request_vpn_endpoint(
    payload: RequestVPNSchema,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Submit a new VPN request for the current user."""
    from src.keyboards.admin_kb import get_request_action_kb

    req_repo = RequestRepository(session)
    if await req_repo.has_pending(user):
        return GenericResponse(
            success=False,
            message="Ваша заявка уже на рассмотрении.",
        )

    if user.has_vpn:
        return GenericResponse(
            success=False,
            message="У вас уже есть активный VPN профиль.",
        )

    request = await req_repo.create(user, user_comment=payload.comment)

    # Notify admins via Telegram
    display_name = f"@{user.username}" if user.username else user.full_name
    msg_text = (
        f"🔔 <b>Новая заявка (из WebApp)!</b>\n\n"
        f"👤 {display_name}\n"
        f"🆔 <code>{user.telegram_id}</code>"
    )
    if payload.comment:
        msg_text += f"\n💬 <b>Комментарий:</b> {payload.comment}"

    async with create_bot() as bot:
        for admin_id in settings.admin_ids:
            with contextlib.suppress(Exception):
                await bot.send_message(
                    admin_id,
                    msg_text,
                    reply_markup=get_request_action_kb(request),
                    parse_mode="HTML",
                )

    # Notify admins via WebSocket
    await ws_manager.broadcast_to_admins(
        {
            "type": "NEW_REQUEST",
            "request_id": request.id,
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "comment": payload.comment,
        }
    )

    return GenericResponse(
        success=True,
        message="Заявка успешно отправлена!",
    )
