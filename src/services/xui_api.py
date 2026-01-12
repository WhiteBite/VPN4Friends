"""3X-UI API client for VPN profile management."""

import json
import logging
import uuid
from typing import Any
from urllib.parse import quote

import aiohttp

from src.bot.config import settings

logger = logging.getLogger(__name__)


class XUIApiError(Exception):
    """Exception raised for 3X-UI API errors."""

    pass


class XUIApi:
    """Async client for 3X-UI panel API."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._cookie_jar = aiohttp.CookieJar(unsafe=True)

    async def __aenter__(self) -> "XUIApi":
        self._session = aiohttp.ClientSession(cookie_jar=self._cookie_jar)
        await self._login()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._session:
            await self._session.close()

    def _build_url(self, path: str) -> str:
        """Build full URL for API endpoint."""
        base = settings.xui_api_url.rstrip("/")
        base_path = settings.xui_base_path.strip("/")
        if base_path:
            return f"{base}/{base_path}{path}"
        return f"{base}{path}"

    async def _login(self) -> None:
        """Authenticate with 3X-UI panel."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = settings.xui_api_url.rstrip("/") + "/login"
        data = {
            "username": settings.xui_username,
            "password": settings.xui_password,
        }

        async with self._session.post(url, data=data) as resp:
            if resp.status != 200:
                raise XUIApiError(f"Login failed with status {resp.status}")

            result = await resp.json()
            if not result.get("success"):
                raise XUIApiError(f"Login failed: {result.get('msg')}")

            logger.info("Successfully logged in to 3X-UI panel")

    async def get_inbound(self, inbound_id: int) -> dict[str, Any]:
        """Get inbound configuration."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url(f"/api/inbounds/get/{inbound_id}")

        async with self._session.get(url) as resp:
            if resp.status != 200:
                raise XUIApiError(f"Get inbound failed with status {resp.status}")

            result = await resp.json()
            if not result.get("success"):
                raise XUIApiError(f"Get inbound failed: {result.get('msg')}")

            return result["obj"]

    async def update_inbound(self, inbound_id: int, data: dict[str, Any]) -> bool:
        """Update inbound configuration."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url(f"/api/inbounds/update/{inbound_id}")

        async with self._session.post(url, json=data) as resp:
            if resp.status != 200:
                return False

            result = await resp.json()
            return result.get("success", False)

    async def create_client(self, email: str) -> dict[str, Any] | None:
        """Create new VLESS client in inbound."""
        inbound = await self.get_inbound(settings.inbound_id)

        settings_data = json.loads(inbound["settings"])
        stream_settings = json.loads(inbound["streamSettings"])
        reality_settings = stream_settings.get("realitySettings", {})

        clients = settings_data.get("clients", [])

        client_id = str(uuid.uuid4())
        new_client = {
            "id": client_id,
            "flow": "xtls-rprx-vision",
            "email": email,
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": 0,
            "enable": True,
            "tgId": "",
            "subId": "",
            "reset": 0,
        }

        clients.append(new_client)
        settings_data["clients"] = clients

        update_data = {
            "up": inbound["up"],
            "down": inbound["down"],
            "total": inbound["total"],
            "remark": inbound["remark"],
            "enable": inbound["enable"],
            "expiryTime": inbound["expiryTime"],
            "listen": inbound["listen"],
            "port": inbound["port"],
            "protocol": inbound["protocol"],
            "settings": json.dumps(settings_data),
            "streamSettings": inbound["streamSettings"],
            "sniffing": inbound["sniffing"],
        }

        if await self.update_inbound(settings.inbound_id, update_data):
            # Extract Reality settings from inbound for URL generation
            # In 3X-UI, publicKey and fingerprint are nested in settings
            reality_inner = reality_settings.get("settings", {})
            server_names = reality_settings.get("serverNames", [])
            short_ids = reality_settings.get("shortIds", [])

            return {
                "client_id": client_id,
                "email": email,
                "port": inbound["port"],
                "remark": inbound["remark"],
                "reality": {
                    "public_key": reality_inner.get("publicKey", ""),
                    "fingerprint": reality_inner.get(
                        "fingerprint", stream_settings.get("fingerprint", "chrome")
                    ),
                    "sni": server_names[0] if server_names else "",
                    "short_id": short_ids[0] if short_ids else "",
                    "spider_x": reality_inner.get("spiderX", "/"),
                },
            }
        return None

    async def delete_client(self, email: str) -> bool:
        """Delete client from inbound by email."""
        inbound = await self.get_inbound(settings.inbound_id)

        settings_data = json.loads(inbound["settings"])
        clients = settings_data.get("clients", [])

        new_clients = [c for c in clients if c["email"] != email]
        if len(new_clients) == len(clients):
            return False  # Client not found

        settings_data["clients"] = new_clients

        update_data = {
            "up": inbound["up"],
            "down": inbound["down"],
            "total": inbound["total"],
            "remark": inbound["remark"],
            "enable": inbound["enable"],
            "expiryTime": inbound["expiryTime"],
            "listen": inbound["listen"],
            "port": inbound["port"],
            "protocol": inbound["protocol"],
            "settings": json.dumps(settings_data),
            "streamSettings": inbound["streamSettings"],
            "sniffing": inbound["sniffing"],
        }

        return await self.update_inbound(settings.inbound_id, update_data)

    async def get_client_traffic(self, email: str) -> dict[str, int]:
        """Get client traffic statistics."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url(f"/api/inbounds/getClientTraffics/{email}")

        async with self._session.get(url) as resp:
            if resp.status != 200:
                return {"upload": 0, "download": 0}

            result = await resp.json()
            if result.get("success") and isinstance(result.get("obj"), dict):
                return {
                    "upload": result["obj"].get("up", 0),
                    "download": result["obj"].get("down", 0),
                }
            return {"upload": 0, "download": 0}

    async def health_check(self) -> bool:
        """Check if 3X-UI panel is accessible."""
        try:
            await self.get_inbound(settings.inbound_id)
            return True
        except Exception:
            return False

    async def get_server_status(self) -> dict[str, Any]:
        """Get server status including clients count and traffic."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url("/api/inbounds/list")

        async with self._session.get(url) as resp:
            if resp.status != 200:
                raise XUIApiError(f"Get inbounds failed with status {resp.status}")

            result = await resp.json()
            if not result.get("success"):
                raise XUIApiError(f"Get inbounds failed: {result.get('msg')}")

            inbounds = result.get("obj", [])
            total_clients = 0
            total_up = 0
            total_down = 0

            for inbound in inbounds:
                if not inbound.get("enable"):
                    continue
                settings_data = json.loads(inbound.get("settings", "{}"))
                clients = settings_data.get("clients", [])
                total_clients += len([c for c in clients if c.get("enable", True)])
                total_up += inbound.get("up", 0)
                total_down += inbound.get("down", 0)

            return {
                "online": True,
                "clients": total_clients,
                "upload": total_up,
                "download": total_down,
                "inbounds": len([i for i in inbounds if i.get("enable")]),
            }

    async def get_online_clients(self) -> list[dict[str, Any]]:
        """Get list of currently online clients."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url("/api/inbounds/onlines")

        try:
            async with self._session.post(url) as resp:
                if resp.status != 200:
                    return []

                result = await resp.json()
                if result.get("success"):
                    return result.get("obj", []) or []
                return []
        except Exception:
            return []

    async def get_reality_settings(self) -> dict[str, Any]:
        """Get Reality settings from inbound configuration."""
        inbound = await self.get_inbound(settings.inbound_id)
        stream_settings = json.loads(inbound["streamSettings"])
        reality_settings = stream_settings.get("realitySettings", {})
        # In 3X-UI, publicKey and fingerprint are nested in settings
        reality_inner = reality_settings.get("settings", {})

        server_names = reality_settings.get("serverNames", [])
        short_ids = reality_settings.get("shortIds", [])

        return {
            "public_key": reality_inner.get("publicKey", ""),
            "fingerprint": reality_inner.get(
                "fingerprint", stream_settings.get("fingerprint", "chrome")
            ),
            "sni": server_names[0] if server_names else "",
            "short_id": short_ids[0] if short_ids else "",
            "spider_x": reality_inner.get("spiderX", "/"),
            "port": inbound["port"],
            "remark": inbound["remark"],
        }


async def check_xui_connection() -> tuple[bool, str]:
    """Check connection to 3X-UI panel. Returns (success, message)."""
    try:
        async with XUIApi() as api:
            if await api.health_check():
                return True, "3X-UI panel is accessible"
            return False, "3X-UI panel returned error"
    except XUIApiError as e:
        return False, f"3X-UI API error: {e}"
    except Exception as e:
        return False, f"Connection error: {e}"


def generate_client_name(username: str | None, telegram_id: int) -> str:
    """Generate client name for VPN profile using Telegram username."""
    if username:
        # Убираем недопустимые символы, оставляем только буквы, цифры, _, -
        clean_name = "".join(c for c in username if c.isalnum() or c in "_-")
        if clean_name:
            return clean_name
    # Fallback на telegram_id если username нет
    return f"user_{telegram_id}"


def generate_vless_url(profile_data: dict[str, Any]) -> str:
    """Generate VLESS connection URL from profile data with Reality settings."""
    remark = profile_data.get("remark", "")
    email = profile_data["email"]
    fragment = f"{remark}-{email}" if remark else email

    # Get Reality settings from profile (fetched from panel)
    reality = profile_data.get("reality", {})
    public_key = reality.get("public_key", "")
    fingerprint = reality.get("fingerprint", "chrome")
    sni = reality.get("sni", "")
    short_id = reality.get("short_id", "")
    spider_x = reality.get("spider_x", "/")

    # URL-encode spider_x (e.g., "/" -> "%2F")
    spider_x_encoded = quote(spider_x, safe="")

    return (
        f"vless://{profile_data['client_id']}@{settings.xui_host}:{profile_data['port']}"
        f"?type=tcp&security=reality"
        f"&pbk={public_key}"
        f"&fp={fingerprint}"
        f"&sni={sni}"
        f"&sid={short_id}"
        f"&spx={spider_x_encoded}"
        f"&flow=xtls-rprx-vision"
        f"#{fragment}"
    )
