"""Hiddify panel API client for VPN profile management."""

import logging
import uuid
from typing import Any

import aiohttp

from src.services.panel_api import PanelAPI

logger = logging.getLogger(__name__)


class HiddifyApiError(Exception):
    """Exception raised for Hiddify API errors."""

    pass


class HiddifyApi(PanelAPI):
    """Async client for Hiddify panel API (v2).

    Hiddify uses token-based auth via ``Hiddify-API-Key`` header.
    API docs: https://github.com/hiddify/hiddify-manager/wiki/API
    """

    def __init__(self, server_config: dict) -> None:
        """Initialize with server config dict.

        Expected keys:
            api_url: Base URL, e.g. ``https://panel.example.com``
            api_token: Hiddify admin API key
            host: Public host for URL generation
        """
        self._cfg = server_config
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "HiddifyApi":
        self._session = aiohttp.ClientSession(
            headers={
                "Hiddify-API-Key": self._cfg["api_token"],
                "Content-Type": "application/json",
            }
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._session:
            await self._session.close()

    def _url(self, path: str) -> str:
        """Build API URL."""
        base = self._cfg["api_url"].rstrip("/")
        return f"{base}/api/v2{path}"

    async def create_client(
        self, inbound_id: int, email: str, protocol: str
    ) -> dict[str, Any] | None:
        """Create a new user in Hiddify.

        Hiddify doesn't have inbound_id concept for user creation — users
        are created globally and assigned to all inbounds.
        ``inbound_id`` is accepted for interface compat but ignored.
        """
        if not self._session:
            raise HiddifyApiError("Session not initialized")

        client_uuid = str(uuid.uuid4())

        payload = {
            "uuid": client_uuid,
            "name": email,
            "usage_limit_GB": 0,  # unlimited
            "package_days": 0,  # unlimited
            "mode": "no_reset",
            "comment": f"Created by VPN4Friends bot",
        }

        url = self._url("/admin/user/")

        try:
            async with self._session.post(url, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return {
                        "client_id": result.get("uuid", client_uuid),
                        "email": email,
                        "protocol": protocol,
                        "inbound_id": inbound_id,
                    }
                elif resp.status == 409:
                    # User already exists — find and return
                    logger.warning(f"Hiddify user '{email}' already exists")
                    existing = await self._find_user(email)
                    if existing:
                        return {
                            "client_id": existing["uuid"],
                            "email": email,
                            "protocol": protocol,
                            "inbound_id": inbound_id,
                        }
                body = await resp.text()
                logger.error(f"Hiddify create_client failed: {resp.status} {body}")
                return None
        except Exception as e:
            logger.error(f"Hiddify create_client error: {e}")
            return None

    async def _find_user(self, name: str) -> dict | None:
        """Find a user by name."""
        if not self._session:
            return None

        url = self._url("/admin/user/")
        try:
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    return None
                users = await resp.json()
                for user in users:
                    if user.get("name") == name:
                        return user
        except Exception:
            pass
        return None

    async def delete_client(self, inbound_id: int, email: str) -> bool:
        """Delete a Hiddify user by name."""
        if not self._session:
            raise HiddifyApiError("Session not initialized")

        user = await self._find_user(email)
        if not user:
            return False

        url = self._url(f"/admin/user/{user['uuid']}/")
        try:
            async with self._session.delete(url) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Hiddify delete_client error: {e}")
            return False

    async def get_client_traffic(self, email: str) -> dict[str, Any] | None:
        """Get traffic stats for a Hiddify user."""
        if not self._session:
            raise HiddifyApiError("Session not initialized")

        user = await self._find_user(email)
        if not user:
            return None

        return {
            "upload": user.get("current_usage_GB", 0) * 1073741824,  # GB → bytes
            "download": 0,  # Hiddify reports combined traffic
        }

    async def get_protocol_settings(self, inbound_id: int) -> dict[str, Any]:
        """Get protocol settings from Hiddify.

        Hiddify manages Reality/TLS settings automatically.
        We return minimal data needed for link generation.
        """
        if not self._session:
            raise HiddifyApiError("Session not initialized")

        # Hiddify generates subscription links — we extract the config
        # For Reality, the settings come from the panel's global config
        settings_data: dict[str, Any] = {
            "port": 443,
            "remark": "VPN4Friends",
        }

        try:
            url = self._url("/admin/server_status/")
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    status = await resp.json()
                    # Extract whatever we can from server status
                    settings_data["host"] = self._cfg.get("host", "")
        except Exception as e:
            logger.warning(f"Hiddify get_protocol_settings error: {e}")

        return settings_data

    async def get_online_clients(self) -> list[str]:
        """Get list of currently online users."""
        if not self._session:
            return []

        try:
            url = self._url("/admin/user/")
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    return []
                users = await resp.json()
                return [u["name"] for u in users if u.get("is_active")]
        except Exception:
            return []

    async def get_server_status(self) -> dict[str, Any]:
        """Get Hiddify server status."""
        if not self._session:
            raise HiddifyApiError("Session not initialized")

        url = self._url("/admin/server_status/")
        try:
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    raise HiddifyApiError(f"Status check failed: {resp.status}")
                result = await resp.json()
                return {
                    "online": True,
                    "clients": result.get("total_users", 0),
                    "upload": 0,
                    "download": 0,
                    "version": result.get("version", "?"),
                }
        except HiddifyApiError:
            raise
        except Exception as e:
            raise HiddifyApiError(f"Server status failed: {e}") from e

    async def get_user_sub_link(self, email: str) -> str | None:
        """Get the subscription link for a Hiddify user.

        Hiddify generates its own VPN links via subscription URLs.
        This is the preferred way to deliver links for Hiddify users.
        """
        user = await self._find_user(email)
        if not user:
            return None

        base = self._cfg["api_url"].rstrip("/")
        uuid = user.get("uuid", "")
        return f"{base}/{uuid}/all.txt"
