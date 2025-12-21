"""User repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
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
        """Get all users with active VPN profile."""
        result = await self.session.execute(select(User).where(User.vless_profile_data.isnot(None)))
        return list(result.scalars().all())

    async def get_all(self) -> list[User]:
        """Get all users."""
        result = await self.session.execute(select(User))
        return list(result.scalars().all())

    async def set_vpn_profile(self, user: User, profile_data: str | None) -> None:
        """Set or clear VPN profile data."""
        user.vless_profile_data = profile_data
        await self.session.commit()
