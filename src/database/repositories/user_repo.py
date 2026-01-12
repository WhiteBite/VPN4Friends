"""User repository for database operations."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import User, VpnProfile


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID with profiles eagerly loaded."""
        result = await self.session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.profiles))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        full_name: str,
        username: str | None = None,
        is_admin: bool = False,
    ) -> User:
        """Create new user."""
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            is_admin=is_admin,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """Update existing user."""
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_or_create(
        self,
        telegram_id: int,
        full_name: str,
        username: str | None = None,
        is_admin: bool = False,
    ) -> tuple[User, bool]:
        """Get existing user or create new one. Returns (user, created)."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            # Update info if changed
            changed = False
            if user.full_name != full_name:
                user.full_name = full_name
                changed = True
            if user.username != username:
                user.username = username
                changed = True
            if changed:
                await self.update(user)
            return user, False

        user = await self.create(telegram_id, full_name, username, is_admin)
        return user, True

    async def get_all_with_vpn(self) -> list[User]:
        """Get all users with an active VPN profile."""
        result = await self.session.execute(
            select(User).where(User.profiles.any(VpnProfile.is_active == True))
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[User]:
        """Get all users."""
        result = await self.session.execute(select(User))
        return list(result.scalars().all())

    async def create_vpn_profile(
        self, user: User, protocol_name: str, profile_data: dict
    ) -> VpnProfile:
        """Create a new VPN profile for a user."""
        # Deactivate other profiles first
        await self.deactivate_all_profiles(user)

        new_profile = VpnProfile(
            user=user,
            protocol_name=protocol_name,
            profile_data=profile_data,
            is_active=True,
        )
        self.session.add(new_profile)
        await self.session.commit()
        await self.session.refresh(new_profile)
        return new_profile

    async def deactivate_all_profiles(self, user: User) -> None:
        """Set is_active=False for all of a user's profiles."""
        await self.session.execute(
            update(VpnProfile)
            .where(VpnProfile.user_id == user.id)
            .values(is_active=False)
        )
        await self.session.commit()

    async def delete_active_profile(self, user: User) -> None:
        """Delete the active profile for a user."""
        active_profile = user.active_profile
        if active_profile:
            await self.session.delete(active_profile)
            await self.session.commit()
