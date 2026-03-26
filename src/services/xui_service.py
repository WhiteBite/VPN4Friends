"""3X-UI Panel API service."""

import logging
from typing import Any

import httpx

from src.bot.config import Settings

logger = logging.getLogger(__name__)


class XuiService:
    """Service for interacting with 3X-UI panel API.

    This service handles all communication with the 3X-UI panel,
    including authentication, user management, and traffic statistics.
    """

    def __init__(self, settings: Settings):
        """Initialize XuiService.

        Args:
            settings: Bot configuration with panel credentials.
        """
        self.base_url = settings.xui_finland_url.rstrip("/")
        self.login = settings.xui_finland_login
        self.password = settings.xui_finland_password
        self._session: httpx.AsyncClient | None = None
        self._logged_in = False

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session with authentication."""
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=True,
            )

        if not self._logged_in:
            await self._login()

        return self._session

    async def _login(self) -> None:
        """Authenticate with 3X-UI panel."""
        if not self._session:
            self._session = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=True,
            )

        login_url = f"{self.base_url}/login"
        response = await self._session.post(
            login_url,
            data={"username": self.login, "password": self.password},
        )
        response.raise_for_status()

        result = response.json()
        if result.get("success"):
            self._logged_in = True
            logger.info("Successfully logged in to 3X-UI panel")
        else:
            raise RuntimeError(f"3X-UI login failed: {result}")

    async def create_user(
        self,
        email: str,
        uuid: str,
        inbound_id: int,
        traffic_limit: int = 0,
        days_limit: int = 0,
    ) -> dict[str, Any]:
        """Create a new user in 3X-UI panel.

        Args:
            email: User email/identifier.
            uuid: User UUID for VLESS protocol.
            inbound_id: ID of the inbound to add user to.
            traffic_limit: Traffic limit in GB (0 = unlimited).
            days_limit: Days limit (0 = unlimited).

        Returns:
            Created user data.

        Raises:
            RuntimeError: If user creation fails.
        """
        session = await self._get_session()

        payload = {
            "id": inbound_id,
            "settings": {
                "clients": [
                    {
                        "id": uuid,
                        "email": email,
                        "limitIp": 0,
                        "totalGB": traffic_limit * 1073741824,  # GB to bytes
                        "expiryTime": 0 if days_limit == 0 else days_limit * 86400000,
                        "enable": True,
                        "tgId": "",
                        "subId": "",
                    }
                ]
            },
        }

        response = await session.post(
            "/panel/api/inbounds/addClient",
            json=payload,
        )
        response.raise_for_status()

        result = response.json()
        if not result.get("success"):
            raise RuntimeError(f"Failed to create user: {result.get('msg', 'Unknown error')}")

        logger.info(f"Created user {email} in 3X-UI panel")
        return result

    async def delete_user(self, uuid: str, inbound_id: int) -> bool:
        """Delete user from 3X-UI panel.

        Args:
            uuid: User UUID to delete.
            inbound_id: ID of the inbound.

        Returns:
            True if deleted successfully.
        """
        session = await self._get_session()

        # First find the user
        user = await self._find_user(uuid)
        if not user:
            logger.warning(f"User {uuid} not found for deletion")
            return False

        response = await session.delete(
            f"/panel/api/inbounds/{inbound_id}/delClient/{user['id']}",
        )
        response.raise_for_status()

        result = response.json()
        if result.get("success"):
            logger.info(f"Deleted user {uuid} from 3X-UI panel")
            return True

        logger.error(f"Failed to delete user {uuid}: {result.get('msg')}")
        return False

    async def get_user_stats(self, uuid: str) -> dict[str, Any] | None:
        """Get user traffic statistics.

        Args:
            uuid: User UUID.

        Returns:
            User statistics or None if not found.
        """
        user = await self._find_user(uuid)
        if not user:
            return None

        return {
            "upload": user.get("up", 0),
            "download": user.get("down", 0),
            "total": user.get("up", 0) + user.get("down", 0),
            "enable": user.get("enable", False),
            "expiryTime": user.get("expiryTime", 0),
        }

    async def _find_user(self, uuid: str) -> dict[str, Any] | None:
        """Find user by UUID in 3X-UI panel.

        Args:
            uuid: User UUID to find.

        Returns:
            User data or None if not found.
        """
        session = await self._get_session()

        # Get all inbounds
        response = await session.get("/panel/api/inbounds/list")
        response.raise_for_status()

        result = response.json()
        if not result.get("success"):
            return None

        # Search through all inbounds
        for inbound in result.get("obj", []):
            settings = inbound.get("settings", {})
            clients = settings.get("clients", [])

            for client in clients:
                if client.get("id") == uuid:
                    return client

        return None

    async def check_connection(self) -> bool:
        """Check if 3X-UI panel is accessible.

        Returns:
            True if panel is accessible.
        """
        try:
            session = await self._get_session()
            response = await session.get("/panel/api/inbounds/list")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"3X-UI connection check failed: {e}")
            return False

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.is_closed:
            await self._session.aclose()
            logger.info("3X-UI session closed")
