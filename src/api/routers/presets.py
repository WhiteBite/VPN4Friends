from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.schemas import (
    CreatePresetRequest,
    GenericResponse,
    PresetConfigResponse,
    PresetSchema,
)
from src.database.models import User
from src.database.session import get_session
from src.services import PresetService

router = APIRouter(prefix="/presets", tags=["Presets"])


@router.get("", response_model=list[PresetSchema])
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


@router.post("", response_model=PresetSchema)
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


@router.delete("/{preset_id}", response_model=GenericResponse)
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


@router.get("/{preset_id}/config", response_model=PresetConfigResponse)
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
