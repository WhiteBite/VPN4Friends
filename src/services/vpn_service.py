"""VPN service for business logic."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.database.models import User, VPNRequest
from src.database.repositories import RequestRepository, UserRepository
from src.services.url_generator import generate_vpn_link
from src.services.xui_api import XUIApi, generate_client_name

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

    async def approve_request(self, request_id: int, protocol_name: str) -> tuple[bool, str]:
        """
        Approve VPN request and create a profile for the specified protocol.

        Returns:
            Tuple of (success, message/vpn_link)
        """
        request = await self.request_repo.get_by_id(request_id)
        if not request:
            return False, "Заявка не найдена"

        if request.status.value != "pending":
            return False, "Заявка уже обработана"

        user = request.user
        protocol = settings.get_protocol(protocol_name)
        if not protocol:
            return False, f"Протокол '{protocol_name}' не настроен."

        async with XUIApi() as api:
            client_name = generate_client_name(user.username, user.telegram_id)
            # Create client in the corresponding inbound
            client_data = await api.create_client(
                inbound_id=protocol.inbound_id, email=client_name, protocol=protocol.name
            )
            if not client_data:
                return False, "Ошибка создания профиля в 3X-UI"

            # Fetch protocol-specific settings (like Reality, etc.)
            protocol_settings = await api.get_protocol_settings(protocol.inbound_id)

        # Combine client data with protocol settings for the link generator
        full_profile_data = {**client_data, **protocol_settings}

        # Save the new profile to the database
        profile = await self.user_repo.create_vpn_profile(
            user=user, protocol_name=protocol.name, profile_data=full_profile_data
        )

        await self.request_repo.approve(request)

        vpn_link = generate_vpn_link(protocol.name, profile.profile_data, profile.settings)
        if not vpn_link:
            return False, "Не удалось сгенерировать ссылку для VPN."

        logger.info(f"Approved request {request_id} for user {user.telegram_id}")
        return True, vpn_link

    async def reject_request(self, request_id: int, comment: str | None = None) -> bool:
        """Reject VPN request."""
        request = await self.request_repo.get_by_id(request_id)
        if not request or request.status.value != "pending":
            return False

        await self.request_repo.reject(request, comment)
        logger.info(f"Rejected request {request_id}")
        return True

    async def revoke_vpn(self, user: User) -> bool:
        """Revoke user's active VPN access."""
        active_profile = user.active_profile
        if not active_profile:
            return False

        email = active_profile.profile_data.get("email")
        inbound_id = active_profile.profile_data.get("inbound_id")

        if email and inbound_id:
            async with XUIApi() as api:
                await api.delete_client(inbound_id, email)

        await self.user_repo.delete_active_profile(user)
        logger.info(f"Revoked VPN for user {user.telegram_id}")
        return True

    async def get_user_stats(self, user: User) -> dict[str, Any] | None:
        """Get traffic statistics for the user's active profile."""
        active_profile = user.active_profile
        if not active_profile:
            return None

        email = active_profile.profile_data.get("email")
        if not email:
            return None

        async with XUIApi() as api:
            traffic_data = await api.get_client_traffic(email)

        return {
            "protocol": active_profile.protocol_name,
            **traffic_data,
        }

    async def get_active_vpn_link(self, user: User) -> str | None:
        """Get the connection link for the user's active VPN profile."""
        active_profile = user.active_profile
        if not active_profile:
            return None

        # The profile_data in DB already contains all necessary info; merge with settings
        return generate_vpn_link(
            active_profile.protocol_name,
            active_profile.profile_data,
            active_profile.settings,
        )

    async def get_pending_requests(self) -> list[VPNRequest]:
        """Get all pending VPN requests."""
        return await self.request_repo.get_all_pending()

    async def get_all_users_with_vpn(self) -> list[User]:
        """Get all users with an active VPN profile."""
        return await self.user_repo.get_all_with_vpn()

    async def switch_protocol(self, user: User, protocol_name: str) -> tuple[bool, str]:
        """Switch the user's active VPN to a new protocol."""
        protocol = settings.get_protocol(protocol_name)
        if not protocol:
            return False, f"Протокол '{protocol_name}' не настроен."

        # Revoke current active profile before creating a new one
        if user.active_profile:
            await self.revoke_vpn(user)

        # This flow is very similar to approving a request, but without a request object
        async with XUIApi() as api:
            client_name = generate_client_name(user.username, user.telegram_id)
            client_data = await api.create_client(
                inbound_id=protocol.inbound_id, email=client_name, protocol=protocol.name
            )
            if not client_data:
                return False, "Ошибка создания профиля в 3X-UI"

            protocol_settings = await api.get_protocol_settings(protocol.inbound_id)

        full_profile_data = {**client_data, **protocol_settings}

        profile = await self.user_repo.create_vpn_profile(
            user=user, protocol_name=protocol.name, profile_data=full_profile_data
        )

        vpn_link = generate_vpn_link(protocol.name, profile.profile_data, profile.settings)
        if not vpn_link:
            return False, "Не удалось сгенерировать ссылку для VPN."

        logger.info(f"Switched protocol to {protocol_name} for user {user.telegram_id}")
        return True, vpn_link

    async def update_profile_settings(self, user: User, sni: str) -> bool:
        """Update user-specific settings for the active profile, e.g., SNI."""
        active_profile = user.active_profile
        if not active_profile:
            return False

        # Validate SNI against allowed list from the panel
        async with XUIApi() as api:
            protocol_settings = await api.get_protocol_settings(
                active_profile.profile_data.get("inbound_id")
            )
            allowed_snis = protocol_settings.get("reality", {}).get("sni_options", [])

        if sni not in allowed_snis:
            logger.warning(f"User {user.telegram_id} tried to set an invalid SNI: {sni}")
            return False

        # Store the selected SNI in the profile's settings
        if not active_profile.settings:
            active_profile.settings = {}
        active_profile.settings["sni"] = sni

        await self.user_repo.update_vpn_profile(active_profile)
        logger.info(f"Updated SNI to {sni} for user {user.telegram_id}")
        return True
