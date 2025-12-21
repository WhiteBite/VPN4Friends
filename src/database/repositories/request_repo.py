"""VPN Request repository for database operations."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database.models import RequestStatus, User, VPNRequest


class RequestRepository:
    """Repository for VPNRequest model operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User) -> VPNRequest:
        """Create new VPN request."""
        request = VPNRequest(user_id=user.id)
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def get_pending_by_user(self, user: User) -> VPNRequest | None:
        """Get pending request for user."""
        result = await self.session.execute(
            select(VPNRequest).where(
                VPNRequest.user_id == user.id,
                VPNRequest.status == RequestStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, request_id: int) -> VPNRequest | None:
        """Get request by ID with user loaded."""
        result = await self.session.execute(
            select(VPNRequest)
            .options(joinedload(VPNRequest.user))
            .where(VPNRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def approve(self, request: VPNRequest, comment: str | None = None) -> None:
        """Approve VPN request."""
        request.status = RequestStatus.APPROVED
        request.processed_at = datetime.utcnow()
        request.admin_comment = comment
        await self.session.commit()

    async def reject(self, request: VPNRequest, comment: str | None = None) -> None:
        """Reject VPN request."""
        request.status = RequestStatus.REJECTED
        request.processed_at = datetime.utcnow()
        request.admin_comment = comment
        await self.session.commit()

    async def get_all_pending(self) -> list[VPNRequest]:
        """Get all pending requests with users loaded."""
        result = await self.session.execute(
            select(VPNRequest)
            .options(joinedload(VPNRequest.user))
            .where(VPNRequest.status == RequestStatus.PENDING)
            .order_by(VPNRequest.created_at)
        )
        return list(result.scalars().all())

    async def has_pending(self, user: User) -> bool:
        """Check if user has pending request."""
        return await self.get_pending_by_user(user) is not None
