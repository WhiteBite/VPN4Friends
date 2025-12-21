"""VPN service for business logic."""

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, VPNRequest
from src.database.repositories import RequestRepository, UserRepository
from src.services.xui_api import XUIApi, generate_client_name, generate_vless_url

logger = logging.getLogger(__name__)


class VPNService:
    """Service for VPN-related business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.request_repo = RequestRepository(session)

    async def create_request(self, user: User) -> VPNRequest | None:
        """Create VPN access request if user doesn't have one pending."""
        if user.has_vpn:
            logger.info(f"User {user.telegram_id} already has VPN")
            return None

        if await self.request_repo.has_pending(user):
            logger.info(f"User {user.telegram_id} already has pending request")
            return None

        request = await self.request_repo.create(user)
        logger.info(f"Created VPN request {request.id} for user {user.telegram_id}")
        return request

    async def approve_request(self, request_id: int) -> tuple[bool, str]:
        """
        Approve VPN request and create profile.

        Returns:
            Tuple of (success, message/vless_url)
        """
        request = await self.request_repo.get_by_id(request_id)
        if not request:
            return False, "Заявка не найдена"

        if request.status.value != "pending":
            return False, "Заявка уже обработана"

        user = request.user

        # Create VPN profile in 3X-UI
        async with XUIApi() as api:
            client_name = generate_client_name(user.username, user.telegram_id)
            profile_data = await api.create_client(client_name)

            if not profile_data:
                return False, "Ошибка создания профиля в 3X-UI"

        # Save profile to user
        await self.user_repo.set_vpn_profile(user, json.dumps(profile_data))

        # Mark request as approved
        await self.request_repo.approve(request)

        vless_url = generate_vless_url(profile_data)
        logger.info(f"Approved request {request_id} for user {user.telegram_id}")

        return True, vless_url

    async def reject_request(self, request_id: int, comment: str | None = None) -> bool:
        """Reject VPN request."""
        request = await self.request_repo.get_by_id(request_id)
        if not request or request.status.value != "pending":
            return False

        await self.request_repo.reject(request, comment)
        logger.info(f"Rejected request {request_id}")
        return True

    async def revoke_vpn(self, user: User) -> bool:
        """Revoke user's VPN access."""
        if not user.vless_profile_data:
            return False

        profile_data = json.loads(user.vless_profile_data)
        email = profile_data.get("email")

        if email:
            async with XUIApi() as api:
                await api.delete_client(email)

        await self.user_repo.set_vpn_profile(user, None)
        logger.info(f"Revoked VPN for user {user.telegram_id}")
        return True

    async def get_user_stats(self, user: User) -> dict[str, int] | None:
        """Get traffic statistics for user."""
        if not user.vless_profile_data:
            return None

        profile_data = json.loads(user.vless_profile_data)
        email = profile_data.get("email")

        if not email:
            return None

        async with XUIApi() as api:
            return await api.get_client_traffic(email)

    async def get_vless_url(self, user: User) -> str | None:
        """Get VLESS URL for user with current Reality settings from panel."""
        if not user.vless_profile_data:
            return None

        profile_data = json.loads(user.vless_profile_data)

        # Fetch current Reality settings from panel
        async with XUIApi() as api:
            reality = await api.get_reality_settings()
            profile_data["reality"] = reality
            profile_data["port"] = reality["port"]
            profile_data["remark"] = reality["remark"]

        return generate_vless_url(profile_data)

    async def get_pending_requests(self) -> list[VPNRequest]:
        """Get all pending VPN requests."""
        return await self.request_repo.get_all_pending()

    async def get_all_users_with_vpn(self) -> list[User]:
        """Get all users with active VPN."""
        return await self.user_repo.get_all_with_vpn()
