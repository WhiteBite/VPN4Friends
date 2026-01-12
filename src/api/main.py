"""Main FastAPI application for the Mini App backend."""

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.schemas import MeResponse, PresetSchema, ProfileSchema, UserSchema
from src.database.models import User
from src.database.session import get_session
from src.services import PresetService, VPNService, XUIApi

app = FastAPI(
    title="VPN4Friends Mini App API",
    version="1.0.0",
)


@app.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    """Get consolidated state for the current user."""
    vpn_service = VPNService(session)
    preset_service = PresetService(session)

    user_schema = UserSchema(full_name=user.full_name, username=user.username)

    # Get profile info
    active_profile = user.active_profile
    if active_profile:
        async with XUIApi() as api:
            protocol_settings = await api.get_protocol_settings(
                active_profile.profile_data.get("inbound_id")
            )
            available_snis = (
                protocol_settings.get("reality", {}).get("sni_options", [])
            )

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
        PresetSchema(
            id=p.id, name=p.name, app_type=p.app_type, format=p.format
        )
        for p in presets
    ]

    return MeResponse(
        user=user_schema,
        profile=profile_schema,
        presets=presets_schema,
    )
