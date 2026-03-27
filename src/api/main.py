"""Main FastAPI application for the Mini App backend."""

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

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
    SelectEndpointRequest,
    StatsResponse,
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

# Allow Mini App frontend to call this API from the browser.
# For now we allow all origins; this can be restricted later
# to specific domains (e.g. settings.miniapp_url).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    user_schema = UserSchema(full_name=user.full_name, username=user.username)

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
            protocol=active_profile.protocol_name,
            label=active_profile.label,
            sni=active_profile.settings.get("sni") if active_profile.settings else None,
            available_snis=available_snis,
        )
    else:
        profile_schema = ProfileSchema(has_profile=False)

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
        )
        for ep in settings.endpoints
        if getattr(ep, "protocol", "vless") != "mtproto"
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

    if not active_profile.settings:
        active_profile.settings = {}
    active_profile.settings["endpoint"] = payload.endpoint

    from src.database.repositories.user_repo import UserRepository

    user_repo = UserRepository(session)
    await user_repo.update_vpn_profile(active_profile)

    return GenericResponse(
        success=True,
        message=f"Точка входа изменена на '{endpoint.label}'.",
    )
