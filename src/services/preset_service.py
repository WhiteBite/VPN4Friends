"""Preset service for business logic."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ConnectionPreset, User
from src.database.repositories import PresetRepository, UserRepository
from src.services.url_generator import generate_vpn_link

logger = logging.getLogger(__name__)


class PresetService:
    """Service for preset-related business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.preset_repo = PresetRepository(session)

    async def create_preset(
        self, user: User, name: str, app_type: str, format: str, options: dict | None = None
    ) -> ConnectionPreset | None:
        """Create a new connection preset for the user's active profile."""
        active_profile = user.active_profile
        if not active_profile:
            logger.warning(f"User {user.telegram_id} has no active profile to create a preset for.")
            return None

        preset = await self.preset_repo.create(
            user=user,
            profile=active_profile,
            name=name,
            app_type=app_type,
            format=format,
            options=options,
        )
        logger.info(f"Created preset {preset.id} for user {user.telegram_id}")
        return preset

    async def get_user_presets(self, user: User) -> list[ConnectionPreset]:
        """Get all presets for a user."""
        return await self.preset_repo.get_by_user(user)

    async def delete_preset(self, user: User, preset_id: int) -> bool:
        """Delete a preset if it belongs to the user."""
        preset = await self.preset_repo.get_by_id(preset_id)
        if not preset or preset.user_id != user.id:
            return False

        await self.preset_repo.delete(preset)
        logger.info(f"Deleted preset {preset_id} for user {user.telegram_id}")
        return True

    async def get_preset_for_user(self, user: User, preset_id: int) -> ConnectionPreset | None:
        """Get a preset by ID only if it belongs to the given user."""
        preset = await self.preset_repo.get_by_id(preset_id)
        if not preset or preset.user_id != user.id:
            return None
        return preset

    async def generate_config(self, preset: ConnectionPreset) -> dict[str, str] | None:
        """Generate the final config for a preset."""
        profile = preset.profile
        if not profile:
            # This should ideally not happen if DB constraints are set up
            logger.error(f"Preset {preset.id} has no associated profile.")
            return None

        # Combine profile data with user-specific overrides from profile.settings
        full_profile_data = profile.profile_data

        # TODO: Add logic to handle different formats (e.g., YAML for Clash/Hiddify)
        if preset.format.endswith("_uri"):
            link = generate_vpn_link(profile.protocol_name, full_profile_data, profile.settings)
            if link:
                return {"type": "uri", "value": link}

        logger.warning(f"Unsupported format '{preset.format}' for preset {preset.id}")
        return None
