"""Repository for managing SupportMessage models."""

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import SupportMessage, User


class SupportRepository:
    """Repository for support messages operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_message(
        self, user_id: int, text: str, is_from_admin: bool = False
    ) -> SupportMessage:
        """Create and save a new support message."""
        msg = SupportMessage(user_id=user_id, text=text, is_from_admin=is_from_admin)
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_all_chats(self) -> list[dict]:
        """Get unique users who have a support history along with their last message."""
        # Find the latest message id per user
        subq = (
            select(
                SupportMessage.user_id, func.max(SupportMessage.created_at).label("last_activity")
            )
            .group_by(SupportMessage.user_id)
            .subquery()
        )

        query = (
            select(User, SupportMessage)
            .join(subq, User.id == subq.c.user_id)
            .join(
                SupportMessage,
                and_(
                    SupportMessage.user_id == User.id,
                    SupportMessage.created_at == subq.c.last_activity,
                ),
            )
            .order_by(SupportMessage.created_at.desc())
        )

        result = await self.session.execute(query)
        rows = result.all()

        chats = []
        for user, last_msg in rows:
            chats.append({"user": user, "last_message": last_msg})
        return chats

    async def get_user_chat_history(self, user_id: int) -> list[SupportMessage]:
        """Get all messages for a specific user."""
        query = (
            select(SupportMessage)
            .where(SupportMessage.user_id == user_id)
            .order_by(SupportMessage.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(self, user_id: int) -> None:
        """Mark unread messages from a user as read."""
        # Optional helper for unread counts
        pass
