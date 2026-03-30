"""3X-UI API client for VPN profile management."""

import json
import logging
import uuid
from typing import Any

import aiohttp

from src.bot.config import settings
from src.services.panel_api import PanelAPI

logger = logging.getLogger(__name__)


class XUIApiError(Exception):
    """Exception raised for 3X-UI API errors."""

    pass


class XUIApi(PanelAPI):
    """Async client for 3X-UI panel API."""

    def __init__(self, server_config: dict | None = None) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._cookie_jar = aiohttp.CookieJar(unsafe=True)
        # Allow per-server config override
        self._cfg = server_config or {
            "api_url": settings.xui_api_url,
            "base_path": settings.xui_base_path,
            "username": settings.xui_username,
            "password": settings.xui_password,
            "host": settings.xui_host,
        }

        # Safely default base_path to "panel" for 3X-UI if missing in server_config
        if "base_path" not in self._cfg:
            self._cfg["base_path"] = "panel"

    async def __aenter__(self) -> "XUIApi":
        # Add a total timeout of 10 seconds to all requests to avoid hanging on unreachable nodes
        timeout = aiohttp.ClientTimeout(total=10)
        self._session = aiohttp.ClientSession(cookie_jar=self._cookie_jar, timeout=timeout)
        await self._login()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._session:
            await self._session.close()

    def _build_url(self, path: str) -> str:
        """Build full URL for API endpoint."""
        base = self._cfg["api_url"].rstrip("/")
        base_path = self._cfg.get("base_path", "").strip("/")
        if base_path:
            return f"{base}/{base_path}{path}"
        return f"{base}{path}"

    async def _login(self) -> None:
        """Authenticate with 3X-UI panel."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._cfg["api_url"].rstrip("/") + "/login"
        data = {
            "username": self._cfg["username"],
            "password": self._cfg["password"],
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
                body = await resp.text()
                logger.error(
                    f"update_inbound({inbound_id}) failed: HTTP {resp.status}, body={body}"
                )
                return False

            result = await resp.json()
            success = result.get("success", False)
            if not success:
                logger.error(f"update_inbound({inbound_id}) API error: {result.get('msg')}")
            return success

    async def list_inbounds(self) -> list[dict[str, Any]]:
        """List all inbounds."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url("/api/inbounds/list")
        async with self._session.get(url) as resp:
            if resp.status != 200:
                raise XUIApiError(f"List inbounds failed with HTTP {resp.status}")

            result = await resp.json()
            if not result.get("success"):
                raise XUIApiError(f"List inbounds API error: {result.get('msg')}")
            return result.get("obj", [])

    async def add_inbound(self, data: dict[str, Any]) -> bool:
        """Add a new inbound."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url("/api/inbounds/add")
        async with self._session.post(url, json=data) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.error(f"add_inbound failed: HTTP {resp.status}, body={body}")
                return False

            result = await resp.json()
            success = result.get("success", False)
            if not success:
                logger.error(f"add_inbound API error: {result.get('msg')}")
            return success

    def _get_client_template(
        self, protocol: str, client_id: str, email: str, transport: str = "tcp"
    ) -> dict[str, Any]:
        """Get a new client template based on the protocol.

        IMPORTANT: flow=xtls-rprx-vision is ONLY compatible with TCP transport.
        For gRPC, xHTTP, WS — flow MUST be empty or the connection will fail silently.
        """
        base_template = {
            "id": client_id,
            "email": email,
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": 0,
            "enable": True,
            "tgId": "",
            "subId": "",
            "reset": 0,
        }
        if protocol == "vless":
            # flow is ONLY for TCP+REALITY. gRPC/xHTTP/WS must have empty flow!
            if transport == "tcp":
                base_template["flow"] = "xtls-rprx-vision"
            else:
                base_template["flow"] = ""

        return base_template

    async def create_client(
        self, inbound_id: int, email: str, protocol: str, client_id: str | None = None
    ) -> dict[str, Any] | None:
        """Create a new client in the specified inbound.

        If a client with the same email already exists, returns its data
        instead of creating a duplicate (prevents Xray crash).
        """
        inbound = await self.get_inbound(inbound_id)

        settings_data = json.loads(inbound["settings"])
        clients = settings_data.get("clients", [])

        # BUG-1 FIX: Check for existing client with same email
        for existing in clients:
            if existing.get("email") == email:
                logger.warning(
                    f"Client '{email}' already exists in inbound {inbound_id}, returning existing"
                )
                return {
                    "client_id": existing["id"],
                    "email": email,
                    "protocol": protocol,
                    "inbound_id": inbound_id,
                }

        client_id = client_id or str(uuid.uuid4())

        # Detect transport from the inbound's streamSettings for correct flow
        try:
            ss = json.loads(inbound.get("streamSettings", "{}"))
        except (json.JSONDecodeError, TypeError):
            ss = {}
        transport = ss.get("network", "tcp")

        new_client = self._get_client_template(protocol, client_id, email, transport)

        clients.append(new_client)
        settings_data["clients"] = clients

        inbound["settings"] = json.dumps(settings_data)

        if await self.update_inbound(inbound_id, inbound):
            return {
                "client_id": client_id,
                "email": email,
                "protocol": protocol,
                "inbound_id": inbound_id,
            }
        return None

    async def batch_add_clients(
        self,
        inbound_id: int,
        clients_info: list[tuple[str, str]],
        protocol: str = "vless",
        transport: str = "tcp",
    ) -> bool:
        """Efficiently add/sync multiple clients (email, client_id) to an inbound.

        Matches clients by UUID (id) instead of email to handle suffixed emails.
        For non-primary inbounds, email is suffixed with -<port> to avoid
        UNIQUE constraint on client_traffics.email in 3x-ui.

        Args:
            inbound_id: Target inbound ID
            clients_info: List of (email, client_id) tuples
            protocol: Protocol (vless, etc.)
            transport: Transport type (tcp, grpc, xhttp, ws) — affects flow setting
        """
        if not clients_info:
            return True

        inbound = await self.get_inbound(inbound_id)
        inbound_port = inbound.get("port", 0)
        settings_data = json.loads(inbound["settings"])
        clients = settings_data.get("clients", [])
        existing_uuids = {c.get("id") for c in clients}

        changed = False
        for email, client_id in clients_info:
            if client_id in existing_uuids:
                # Client already exists (matched by UUID) — fix flow if wrong
                for c in clients:
                    if c.get("id") == client_id:
                        correct_flow = "xtls-rprx-vision" if transport == "tcp" else ""
                        if c.get("flow", "") != correct_flow:
                            c["flow"] = correct_flow
                            changed = True
                            logger.info(
                                f"Fixed flow for {email} on port {inbound_port}: "
                                f"'{c.get('flow', '')}' -> '{correct_flow}'"
                            )
                continue

            # Client not on this inbound — add with suffixed email
            suffixed_email = f"{email}-{inbound_port}" if inbound_port else email
            new_client = self._get_client_template(protocol, client_id, suffixed_email, transport)
            clients.append(new_client)
            changed = True
            logger.debug(f"Adding client {email} ({client_id[:8]}...) to port {inbound_port}")

        if not changed:
            return True

        settings_data["clients"] = clients
        inbound["settings"] = json.dumps(settings_data)
        return await self.update_inbound(inbound_id, inbound)

    async def add_client_to_all_inbounds(
        self, email: str, client_id: str, protocol: str | list[str] = "vless"
    ) -> int:
        """Add a client to all enabled inbounds matching the protocol(s).

        If protocol is "all", adds to all supported VPN protocols (vless, trojan, shadowsocks).
        Returns the number of inbounds successfully updated.
        """
        if not self._session:
            raise XUIApiError("Session not initialized")

        protocols = [protocol] if isinstance(protocol, str) else protocol
        if protocol == "all":
            protocols = ["vless", "trojan", "shadowsocks", "tuic", "juicity"]

        url = self._build_url("/api/inbounds/list")
        async with self._session.get(url) as resp:
            if resp.status != 200:
                return 0
            result = await resp.json()
            if not result.get("success"):
                return 0
            inbounds = result.get("obj", [])

        success_count = 0
        for inbound in inbounds:
            if not inbound.get("enable"):
                continue

            inbound_proto = inbound.get("protocol")
            if protocols != "all" and inbound_proto not in protocols:
                continue

            # Safety: never add UUID-based clients to password-based protocols
            # Shadowsocks requires 'password' field; adding UUID-only clients crashes Xray
            if inbound_proto in ("shadowsocks", "shadowsocks_2022"):
                continue

            # Detect transport from streamSettings for correct flow
            port = inbound.get("port", 0)
            try:
                ss = json.loads(inbound.get("streamSettings", "{}"))
            except (json.JSONDecodeError, TypeError):
                ss = {}
            transport = ss.get("network", "tcp")

            # Suffix email with port to avoid UNIQUE constraint on client_traffics
            suffixed_email = f"{email}-{port}" if port else email

            # Check if client UUID already exists on this inbound
            try:
                settings_data = json.loads(inbound.get("settings", "{}"))
            except (json.JSONDecodeError, TypeError):
                settings_data = {}
            existing_uuids = {c.get("id") for c in settings_data.get("clients", [])}

            if client_id in existing_uuids:
                # Already exists, fix flow if needed
                clients = settings_data.get("clients", [])
                for c in clients:
                    if c.get("id") == client_id:
                        correct_flow = (
                            "xtls-rprx-vision"
                            if (transport == "tcp" and inbound_proto == "vless")
                            else ""
                        )
                        if c.get("flow", "") != correct_flow:
                            c["flow"] = correct_flow
                            settings_data["clients"] = clients
                            inbound["settings"] = json.dumps(settings_data)
                            await self.update_inbound(inbound["id"], inbound)
                            logger.info(f"Fixed flow for {email} on port {port}")
                success_count += 1
                continue

            res = await self.create_client(inbound["id"], suffixed_email, inbound_proto, client_id)
            if res:
                success_count += 1

        return success_count

    async def delete_client(self, inbound_id: int, email: str) -> bool:
        """Delete a client from the specified inbound by email."""
        inbound = await self.get_inbound(inbound_id)

        settings_data = json.loads(inbound["settings"])
        clients = settings_data.get("clients", [])

        new_clients = [c for c in clients if c["email"] != email]
        if len(new_clients) == len(clients):
            return False  # Client not found

        settings_data["clients"] = new_clients
        inbound["settings"] = json.dumps(settings_data)

        return await self.update_inbound(inbound_id, inbound)

    async def remove_client_from_all_inbounds(self, email: str) -> int:
        """Remove a client by email from all enabled inbounds.

        Returns the number of inbounds successfully updated.
        """
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url("/api/inbounds/list")
        async with self._session.get(url) as resp:
            if resp.status != 200:
                return 0
            result = await resp.json()
            if not result.get("success"):
                return 0
            inbounds = result.get("obj", [])

        success_count = 0
        for inbound in inbounds:
            if not inbound.get("enable"):
                continue

            # Check if client exists before calling delete
            settings_str = inbound.get("settings", "{}")
            if email not in settings_str:
                continue

            # Could fail if client isn't really there, but delete_client handles it gracefully
            if await self.delete_client(inbound["id"], email):
                success_count += 1

        return success_count

    async def get_client_traffic(self, email: str) -> dict[str, int]:
        """Get client traffic statistics for a specific email."""
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

    async def get_all_client_traffics(self) -> list[dict]:
        """Get traffic statistics for ALL clients on this panel."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        # 3X-UI internal endpoint for all traffic stats
        url = self._build_url("/api/inbounds/getClientTraffics/all")

        async with self._session.get(url) as resp:
            if resp.status != 200:
                return []

            result = await resp.json()
            if result.get("success") and isinstance(result.get("obj"), list):
                return result["obj"]
            return []

    async def health_check(self) -> bool:
        """Check if 3X-UI panel is accessible by listing inbounds."""
        if not self._session:
            return False
        try:
            url = self._build_url("/api/inbounds/list")
            async with self._session.get(url, timeout=5) as resp:
                return resp.status == 200
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

    async def get_protocol_settings(self, inbound_id: int) -> dict[str, Any]:
        """Get protocol-specific settings from an inbound configuration."""
        inbound = await self.get_inbound(inbound_id)
        protocol = inbound.get("protocol")

        settings_data = {"port": inbound["port"], "remark": inbound["remark"]}

        if protocol == "vless":
            stream_settings = json.loads(inbound["streamSettings"])
            reality_settings = stream_settings.get("realitySettings", {})
            reality_inner = reality_settings.get("settings", {})
            server_names = reality_settings.get("serverNames", [])
            short_ids = reality_settings.get("shortIds", [])

            settings_data["reality"] = {
                "public_key": reality_inner.get("publicKey", ""),
                "fingerprint": reality_inner.get(
                    "fingerprint", stream_settings.get("fingerprint", "chrome")
                ),
                "sni_options": server_names,
                "default_sni": server_names[0] if server_names else "",
                "short_id_options": short_ids,
                "default_short_id": short_ids[0] if short_ids else "",
                "spider_x": reality_inner.get("spiderX", "/"),
            }
        elif protocol == "shadowsocks":
            ss_settings = json.loads(inbound["settings"])
            settings_data["shadowsocks"] = {
                "method": ss_settings.get("method", ""),
                "password": ss_settings.get("password", ""),
            }

        return settings_data

    async def get_xray_template_config(self) -> dict[str, Any]:
        """Get the Xray template config (outbounds + routing) from 3x-ui settings.

        The template config is stored in the panel's database and contains
        the outbounds, routing rules, and other Xray-level settings that are
        merged with inbounds managed via the inbound API.
        """
        settings = await self.get_all_settings()
        template_str = settings.get("xrayTemplateConfig", "{}")
        return json.loads(template_str), settings

    async def get_all_settings(self) -> dict[str, Any]:
        """Get ALL panel settings (needed to update any single field)."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url("/setting/all")
        async with self._session.post(url) as resp:
            if resp.status != 200:
                raise XUIApiError(f"Get settings failed with HTTP {resp.status}")

            result = await resp.json()
            if not result.get("success"):
                raise XUIApiError(f"Get settings failed: {result.get('msg')}")

            return result.get("obj", {})

    async def update_xray_template_config(
        self,
        template: dict[str, Any],
        full_settings: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> bool:
        """Update the Xray template config via the /xray/update endpoint.

        IMPORTANT: Uses /api/xray/update (not /setting/update) because the
        settings endpoint strips wireguard outbounds during save. The xray
        endpoint uses SaveXraySetting() which preserves all outbounds.

        After updating, explicitly restarts Xray to apply the new config.
        The full_settings parameter is kept for backward compatibility but ignored.
        """
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url("/xray/update")
        template_json = json.dumps(template)

        # /xray/update accepts form-encoded data with xraySetting field
        async with self._session.post(url, data={"xraySetting": template_json}) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.error(f"update_xray_template failed: HTTP {resp.status}, body={body}")
                return False

            result = await resp.json()
            success = result.get("success", False)
            if not success:
                logger.error(f"update_xray_template API error: {result.get('msg')}")
                return False

        # 3x-ui does NOT auto-restart Xray on template update — must call explicitly
        return await self.restart_xray()

    async def restart_xray(self) -> bool:
        """Restart the Xray service via 3x-ui API."""
        if not self._session:
            raise XUIApiError("Session not initialized")

        url = self._build_url("/api/server/restartXrayService")
        async with self._session.post(url) as resp:
            if resp.status != 200:
                logger.error(f"restart_xray failed: HTTP {resp.status}")
                return False
            result = await resp.json()
            success = result.get("success", False)
            if not success:
                logger.error(f"restart_xray API error: {result.get('msg')}")
            else:
                logger.info("Xray service restarted successfully")
            return success


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
