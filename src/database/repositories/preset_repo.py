"""Connection Preset repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ConnectionPreset, User, VpnProfile


class PresetRepository:
    """Repository for ConnectionPreset model operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, user: User, profile: VpnProfile, name: str, app_type: str, format: str, options: dict | None = None
    ) -> ConnectionPreset:
        """Create a new connection preset."""
        preset = ConnectionPreset(
            user_id=user.id,
            profile_id=profile.id,
            name=name,
            app_type=app_type,
            format=format,
            options=options,
        )
        self.session.add(preset)
        await self.session.commit()
        await self.session.refresh(preset)
        return preset

    async def get_by_id(self, preset_id: int) -> ConnectionPreset | None:
        """Get a preset by its ID."""
        result = await self.session.execute(
            select(ConnectionPreset).where(ConnectionPreset.id == preset_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user: User) -> list[ConnectionPreset]:
        """Get all presets for a user."""
        result = await self.session.execute(
            select(ConnectionPreset).where(ConnectionPreset.user_id == user.id)
        )
        return list(result.scalars().all())

    async def delete(self, preset: ConnectionPreset) -> None:
        """Delete a connection preset."""
        await self.session.delete(preset)
        await self.session.commit()
