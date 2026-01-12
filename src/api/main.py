"""Main FastAPI application for the Mini App backend."""

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.schemas import (
    CreatePresetRequest,
    GenericResponse,
    MeResponse,
    PresetConfigResponse,
    PresetSchema,
    ProfileSchema,
    ProtocolSchema,
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
    return [
        ProtocolSchema(
            name=p.name,
            label=p.label,
            description=p.description,
            recommended=p.recommended,
        )
        for p in settings.protocols
    ]


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
