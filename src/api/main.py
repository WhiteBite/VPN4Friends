"""Main FastAPI application for the Mini App backend."""

import contextlib

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.api.admin import router as admin_router
from src.api.dependencies import get_current_user
from src.api.schemas import (
    CreatePresetRequest,
    EndpointSchema,
    GenericResponse,
    LinkResponse,
    MeResponse,
    PresetConfigResponse,
    PresetSchema,
    ProfileSchema,
    ProtocolSchema,
    RequestVPNSchema,
    SelectEndpointRequest,
    StatsResponse,
    SupportMessageRequest,
    SwitchProtocolRequest,
    SwitchProtocolResponse,
    UpdateSNIRequest,
    UpdateSNIResponse,
    UserSchema,
)
from src.bot.config import settings
from src.database.models import User
from src.database.session import get_session
from src.services import PresetService, VPNService, XUIApi
from src.services.url_generator import generate_vpn_link


def format_bytes(b: int) -> str:
    """Format bytes into a human-readable string."""
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PiB"


app = FastAPI(
    title="VPN4Friends Mini App API",
    version="1.0.0",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    headers = getattr(exc, "headers", None) or {}
    headers["Access-Control-Allow-Origin"] = "*"
    headers["Access-Control-Allow-Methods"] = "*"
    headers["Access-Control-Allow-Headers"] = "*"
    return JSONResponse(
        {"detail": exc.detail},
        status_code=exc.status_code,
        headers=headers,
    )


# Allow Mini App frontend to call this API from the browser.
# For now we allow all origins; this can be restricted later
# to specific domains (e.g. settings.miniapp_url).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)


@app.get("/protocols", response_model=list[ProtocolSchema])
async def list_protocols() -> list[ProtocolSchema]:
    """Return available VPN protocols configured on the server.

    This endpoint is used by the Mini App frontend to render protocol
    selection chips instead of relying on hardcoded values.
    """
    # Use endpoints instead of protocols
    protocols = []
    seen = set()
    for ep in settings.endpoints:
        protocol_type = getattr(ep, "protocol", "vless")
        if protocol_type not in seen and protocol_type != "mtproto":
            seen.add(protocol_type)
            protocols.append(
                ProtocolSchema(
                    name=protocol_type,
                    label=protocol_type.upper(),
                    description=f"{protocol_type} protocol",
                    recommended=(protocol_type == "vless"),
                )
            )
    return protocols


@app.get("/me", response_model=MeResponse)
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
        async with XUIApi() as api:
            protocol_settings = await api.get_protocol_settings(
                active_profile.profile_data.get("inbound_id")
            )
            available_snis = protocol_settings.get("reality", {}).get("sni_options", [])

        profile_schema = ProfileSchema(
            has_profile=True,
            request_status="approved",
            protocol=active_profile.protocol_name,
            label=active_profile.label,
            sni=active_profile.settings.get("sni") if active_profile.settings else None,
            available_snis=available_snis,
        )
    else:
        # Check if there is an active request
        from sqlalchemy import select

        from src.database.models import VPNRequest

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

    return MeResponse(
        user=user_schema,
        profile=profile_schema,
        presets=presets_schema,
    )


@app.post("/support", response_model=GenericResponse)
async def send_support_message(
    payload: SupportMessageRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Send a support message to admins."""
    from aiogram import Bot

    from src.bot.config import settings
    from src.database.repositories.support_repo import SupportRepository

    repo = SupportRepository(session)
    await repo.save_message(user.id, payload.text)

    # Notify admins
    bot = Bot(token=settings.bot_token.get_secret_value())
    try:
        if settings.admin_ids:
            for admin_id in settings.admin_ids:
                with contextlib.suppress(Exception):
                    await bot.send_message(
                        admin_id,
                        f"📩 <b>Новое обращение в поддержку (через Mini App)</b>\n"
                        f"👤 {user.full_name} (@{user.username or 'без_юзернейма'})\n\n"
                        f"💬 {payload.text}",
                        parse_mode="HTML",
                    )
    finally:
        await bot.session.close()

    await session.commit()
    return GenericResponse(success=True, message="Сообщение отправлено!")


@app.post("/me/protocol", response_model=SwitchProtocolResponse)
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


@app.post("/me/sni", response_model=UpdateSNIResponse)
async def update_sni(
    payload: UpdateSNIRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UpdateSNIResponse:
    """Update SNI for the user's active VPN profile."""
    # Ensure user has an active profile
    if not user.active_profile:
        return UpdateSNIResponse(
            success=False,
            message="У тебя нет активного VPN-профиля.",
            sni=None,
        )

    vpn_service = VPNService(session)
    success = await vpn_service.update_profile_settings(user, payload.sni)

    if not success:
        return UpdateSNIResponse(
            success=False,
            message=("Не удалось обновить SNI. Возможно, он недопустим для текущего протокола."),
            sni=None,
        )

    return UpdateSNIResponse(
        success=True,
        message="SNI обновлён.",
        sni=payload.sni,
    )


@app.get("/presets", response_model=list[PresetSchema])
async def list_presets(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PresetSchema]:
    """List all presets for the current user."""
    preset_service = PresetService(session)
    presets = await preset_service.get_user_presets(user)
    return [
        PresetSchema(id=p.id, name=p.name, app_type=p.app_type, format=p.format) for p in presets
    ]


@app.post("/presets", response_model=PresetSchema)
async def create_preset(
    payload: CreatePresetRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PresetSchema:
    """Create a new connection preset for the active profile."""
    preset_service = PresetService(session)
    preset = await preset_service.create_preset(
        user=user,
        name=payload.name,
        app_type=payload.app_type,
        format=payload.format,
        options=payload.options,
    )

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет активного VPN-профиля для создания пресета.",
        )

    return PresetSchema(
        id=preset.id,
        name=preset.name,
        app_type=preset.app_type,
        format=preset.format,
    )


@app.delete("/presets/{preset_id}", response_model=GenericResponse)
async def delete_preset(
    preset_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Delete a preset owned by the current user."""
    preset_service = PresetService(session)
    success = await preset_service.delete_preset(user, preset_id)

    if not success:
        return GenericResponse(success=False, message="Пресет не найден.")

    return GenericResponse(success=True, message="Пресет удалён.")


@app.get("/presets/{preset_id}/config", response_model=PresetConfigResponse)
async def get_preset_config(
    preset_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PresetConfigResponse:
    """Get rendered config for a preset (e.g. URI or app-specific format)."""
    preset_service = PresetService(session)
    preset = await preset_service.get_preset_for_user(user, preset_id)
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пресет не найден.",
        )

    config = await preset_service.generate_config(preset)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось сгенерировать конфиг для пресета.",
        )

    return PresetConfigResponse(type=config["type"], value=config["value"])


# ---- New endpoints for Mini App redesign ----


@app.get("/me/link", response_model=LinkResponse)
async def get_link(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LinkResponse:
    """Get the VPN connection link for the user's active profile.

    Returns the link directly — no preset needed.
    """
    active_profile = user.active_profile
    if not active_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет активного VPN-профиля.",
        )

    # Determine endpoint (from user settings or default)
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


@app.get("/me/stats", response_model=StatsResponse)
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


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/ready")
async def ready_check() -> dict:
    """Readiness check endpoint."""
    return {"ready": True}


@app.get("/endpoints", response_model=list[EndpointSchema])
async def list_endpoints() -> list[EndpointSchema]:
    """Return available server endpoints.

    This endpoint is used by the Mini App to show server selection.
    """
    return [
        EndpointSchema(
            name=ep.name,
            label=ep.label,
            host=ep.host,
            port=ep.port,
            is_relay=ep.is_relay,
            description=ep.description,
            category=getattr(ep, "category", "vpn"),
            country=getattr(ep, "country", "Unknown"),
            transport=getattr(ep, "transport", "vless") or "vless",
        )
        for ep in settings.endpoints
    ]


@app.post("/me/endpoint", response_model=GenericResponse)
async def select_endpoint_route(
    payload: SelectEndpointRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Select a server endpoint for the user's VPN link generation."""
    # Validate endpoint exists
    endpoint = settings.get_endpoint(payload.endpoint)
    if not endpoint:
        return GenericResponse(
            success=False,
            message=f"Точка входа '{payload.endpoint}' не найдена.",
        )

    # Store in user's profile settings
    active_profile = user.active_profile
    if not active_profile:
        return GenericResponse(
            success=False,
            message="Нет активного VPN-профиля.",
        )

    # Reassign the dictionary to trigger SQLAlchemy's change detection
    new_settings = dict(active_profile.settings or {})
    new_settings["endpoint"] = payload.endpoint
    active_profile.settings = new_settings

    from src.database.repositories.user_repo import UserRepository

    user_repo = UserRepository(session)
    await user_repo.update_vpn_profile(active_profile)

    return GenericResponse(
        success=True,
        message=f"Точка входа изменена на '{endpoint.label}'.",
    )


@app.post("/me/request", response_model=GenericResponse)
async def request_vpn_endpoint(
    payload: RequestVPNSchema,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Submit a new VPN request for the current user."""
    from aiogram import Bot

    from src.bot.config import settings
    from src.database.repositories import RequestRepository
    from src.keyboards.admin_kb import get_request_action_kb

    req_repo = RequestRepository(session)
    if await req_repo.has_pending(user):
        return GenericResponse(
            success=False,
            message="Ваша заявка уже на рассмотрении.",
        )

    # They might already have a profile
    if user.has_vpn:
        return GenericResponse(
            success=False,
            message="У вас уже есть активный VPN профиль.",
        )

    request = await req_repo.create(user, user_comment=payload.comment)

    # Notify admins
    # Create bot instance just to emit the message
    bot = Bot(token=settings.bot_token.get_secret_value())
    for admin_id in settings.admin_ids:
        try:
            display_name = user.username and f"@{user.username}" or user.full_name
            msg_text = (
                f"🔔 <b>Новая заявка (из WebApp)!</b>\n\n"
                f"👤 {display_name}\n"
                f"🆔 <code>{user.telegram_id}</code>"
            )
            if payload.comment:
                msg_text += f"\n💬 <b>Комментарий:</b> {payload.comment}"

            await bot.send_message(
                admin_id,
                msg_text,
                reply_markup=get_request_action_kb(request),
                parse_mode="HTML",
            )
        except Exception:
            pass  # Fail silently if bot cannot reach admin

    await bot.session.close()

    return GenericResponse(
        success=True,
        message="Заявка успешно отправлена!",
    )
