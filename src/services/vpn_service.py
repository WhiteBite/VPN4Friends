"""VPN service for business logic."""

import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.database.models import User, VPNRequest
from src.database.repositories import RequestRepository, UserRepository
from src.services.panel_api import PanelAPI
from src.services.url_generator import generate_vpn_link
from src.services.xui_api import XUIApi, generate_client_name

logger = logging.getLogger(__name__)


def get_panel_for_server(server_id: str | None = None) -> PanelAPI:
    """Factory: return the correct PanelAPI for a server endpoint.

    If the endpoint is a relay with a ``target``, follows the chain
    to the actual server with the panel. Falls back to default XUIApi.
    """
    if server_id:
        endpoint = settings.get_endpoint(server_id)

        # Resolve relay → target (relay shares the target's panel)
        if endpoint and endpoint.is_relay and endpoint.target:
            endpoint = settings.get_endpoint(endpoint.target)

        if endpoint and endpoint.panel_type == "hiddify":
            from src.services.hiddify_api import HiddifyApi

            return HiddifyApi(endpoint.panel_config)
        elif endpoint and endpoint.panel_config:
            return XUIApi(endpoint.panel_config)

    # Default: global 3X-UI settings
    return XUIApi()


class VPNService:
    """Service for VPN-related business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.request_repo = RequestRepository(session)

    def _get_active_panels(self) -> list[PanelAPI]:
        """Return a list of unique active PanelAPI instances."""
        from src.services.hiddify_api import HiddifyApi

        panels: list[PanelAPI] = [XUIApi()]
        seen_urls = {settings.xui_api_url}

        for ep in settings.endpoints:
            api_url = ep.panel_config.get("api_url") if ep.panel_config else None
            if not api_url or api_url in seen_urls:
                continue

            if ep.panel_type == "3xui":
                panels.append(XUIApi(ep.panel_config))
                seen_urls.add(api_url)
            elif ep.panel_type == "hiddify":
                panels.append(HiddifyApi(ep.panel_config))
                seen_urls.add(api_url)

        return panels

    def _find_best_endpoint(self, protocol_hint: str | None, location_hint: str | None) -> str:
        """Find the most suitable endpoint based on user request hints.

        Logic:
        1. Exact match for location (country) AND protocol.
        2. Match for location only.
        3. Match for protocol only.
        4. Fallback to first available endpoint.
        """
        if not settings.endpoints:
            return "vless"  # Fallback

        candidates = settings.endpoints

        # 1. Exact match: Location + Protocol
        if location_hint and protocol_hint:
            for ep in candidates:
                if (
                    ep.country.lower() == location_hint.lower()
                    and ep.name.lower() == protocol_hint.lower()
                ):
                    return ep.name
            # Fuzzy match location + protocol
            for ep in candidates:
                if (
                    ep.country.lower() == location_hint.lower()
                    and ep.protocol.lower() == protocol_hint.lower()
                ):
                    return ep.name

        # 2. Match Location
        if location_hint:
            for ep in candidates:
                if ep.country.lower() == location_hint.lower():
                    return ep.name

        # 3. Match Protocol
        if protocol_hint:
            for ep in candidates:
                if ep.protocol.lower() == protocol_hint.lower():
                    return ep.name

        # 4. Fallback
        return candidates[0].name

    async def create_request(
        self,
        user: User,
        user_comment: str | None = None,
        protocol: str | None = None,
        location: str | None = None,
    ) -> VPNRequest | None:
        """Create VPN access request if user doesn't have one pending."""
        if user.has_vpn:
            logger.info(f"User {user.telegram_id} already has VPN")
            return None

        if await self.request_repo.has_pending(user):
            logger.info(f"User {user.telegram_id} already has pending request")
            return None

        request = await self.request_repo.create(
            user,
            user_comment=user_comment,
            protocol=protocol,
            location=location,
        )
        logger.info(f"Created VPN request {request.id} for user {user.telegram_id}")
        return request

    async def approve_request(
        self, request_id: int, protocol_name: str | None = None
    ) -> tuple[bool, str]:
        """
        Approve VPN request and create a global profile.

        The user is synced to all available panels and protocols.
        The `protocol_name` is now optional and acts as a hint for the default endpoint.
        """
        request = await self.request_repo.get_by_id(request_id)
        if not request:
            return False, "Заявка не найдена"

        if request.status.value != "pending":
            return False, "Заявка уже обработана"

        user = request.user

        # Prevent duplicate VPN: if user already has an active profile, skip
        if user.has_vpn:
            await self.request_repo.approve(request)
            return False, "У пользователя уже есть активный VPN."

        # BUG-2 FIX: Immediately mark as approved to prevent race condition
        # (double-click on "Approve" button)
        await self.request_repo.approve(request)

        client_name = generate_client_name(user.username, user.telegram_id)
        client_id = str(uuid.uuid4())

        # Minimal profile_data: only UUID and email.
        # Connection specifics (host, port, etc.) are resolved dynamically in API.
        full_profile_data = {
            "client_id": client_id,
            "email": client_name,
            "remark": f"VPN4Friends ({user.telegram_id})",
        }

        try:
            # Sync to ALL supported protocols on ALL panels to enable truly Universal Access
            synced_any = await self.sync_client_to_all_panels(client_name, client_id, "all")
            if not synced_any:
                await self.request_repo.revert_to_pending(request)
                return False, "Ошибка создания профиля: ни одна панель не доступна"
        except Exception as e:
            logger.error(f"Failed to sync client for request {request_id}: {e}")
            await self.request_repo.revert_to_pending(request)
            return False, "Ошибка синхронизации с серверами"

        # Determine best starting endpoint honoring user request preferences
        default_endpoint = protocol_name or self._find_best_endpoint(
            request.protocol, request.location
        )
        profile = await self.user_repo.create_vpn_profile(
            user=user,
            protocol_name="vless",  # Display protocol
            profile_data=full_profile_data,
        )

        # Set default endpoint settings
        profile.settings = {"endpoint": default_endpoint}
        await self.user_repo.update_vpn_profile(profile)

        # Return the link for the default endpoint
        vpn_link = await self.get_active_vpn_link(user)
        if not vpn_link:
            return False, "Доступ одобрен, но ссылка будет доступна через минуту в Кабинете."

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

        if email:
            logger.info(f"Revoking VPN for user {user.telegram_id} across all panels...")
            await self.remove_client_from_all_panels(email)

        await self.user_repo.delete_active_profile(user)
        logger.info(f"Revoked VPN for user {user.telegram_id}")
        return True

    async def remove_client_from_all_panels(self, email: str) -> bool:
        """Broadcast user deletion to all configured VPN panels."""
        panels_to_sync = self._get_active_panels()

        deleted = False
        for panel in panels_to_sync:
            try:
                async with panel:
                    res = await panel.remove_client_from_all_inbounds(email)
                    if res > 0:
                        deleted = True
            except Exception as e:
                logger.error(f"Error removing {email} from panel: {e}")

        return deleted

    async def sync_client_to_all_panels(
        self, email: str, client_id: str, protocol: str = "vless"
    ) -> bool:
        """Propagate a client to all active VPN panels defined in settings.

        This is the core 'self-healing' engine that ensures a user exists
        on all servers in the cluster using their unique client_id.
        """
        success = False
        panels_to_sync = self._get_active_panels()

        # 2. Add client to all panels
        for panel in panels_to_sync:
            try:
                async with panel:
                    # Panel-agnostic "ensure client exists" call
                    res = await panel.add_client_to_all_inbounds(
                        email=email, client_id=client_id, protocol=protocol
                    )
                    if res:
                        success = True
                    logger.info(
                        f"Sync complete for {email} on {panel.api_url if hasattr(panel, 'api_url') else 'panel'}"
                    )
            except Exception as e:
                logger.error(f"Failed to sync {email} to panel: {e}")

        return success

    async def get_user_stats(self, user: User) -> dict[str, Any] | None:
        """Get traffic statistics for the user's active profile."""
        active_profile = user.active_profile
        if not active_profile:
            return None

        email = active_profile.profile_data.get("email")
        if not email:
            return None

        total_up = 0
        total_down = 0

        panels_to_check = self._get_active_panels()

        for panel in panels_to_check:
            try:
                async with panel:
                    traffic = await panel.get_client_traffic(email)
                    if traffic:
                        total_up += traffic.get("upload", 0)
                        total_down += traffic.get("download", 0)
            except Exception as e:
                logger.error(f"Error getting stats for {email} from panel: {e}")

        return {
            "protocol": active_profile.protocol_name,
            "upload": total_up,
            "download": total_down,
        }

    async def get_active_vpn_link(self, user: User) -> str | None:
        """Get the connection link for the user's active VPN profile (default endpoint)."""
        active_profile = user.active_profile
        if not active_profile:
            return None

        endpoint_name = (active_profile.settings or {}).get("endpoint")
        endpoint = settings.get_endpoint(endpoint_name) if endpoint_name else None

        return generate_vpn_link(
            active_profile.protocol_name,
            active_profile.profile_data,
            active_profile.settings,
            endpoint=endpoint,
        )

    async def get_all_active_vpn_links(self, user: User) -> list[tuple[str, str]]:
        """Get all connection links across visible endpoints for the user's active VPN profile."""
        active_profile = user.active_profile
        if not active_profile:
            return []

        GROUP_EXPLANATIONS = {
            "fast": "Прямое подключение, мин. пинг",
            "moscow": "Обход блокировок (если не заходит)",
            "warp": "Для Netflix, ChatGPT и др.",
            "stealth": "Скрытый протокол для сложных сетей",
            "stealth_warp": "Скрытый вход + разблокировка",
        }

        links = []
        for endpoint in settings.endpoints:
            user_proto = (active_profile.protocol_name or "").lower()
            if "reality" in user_proto or "finland_xhttp" in user_proto:
                user_proto = "vless"
            ep_proto = (endpoint.protocol or "").lower()
            if "reality" in ep_proto or "finland_xhttp" in ep_proto:
                ep_proto = "vless"

            # We only generate links for endpoints that match the user's current protocol
            if endpoint.visible_in_sub and ep_proto == user_proto:
                try:
                    link = generate_vpn_link(
                        active_profile.protocol_name or "vless",
                        active_profile.profile_data or {},
                        active_profile.settings or {},
                        endpoint=endpoint,
                    )
                    if link:
                        label = endpoint.sub_label or f"{endpoint.country} ({endpoint.label})"
                        explanation = GROUP_EXPLANATIONS.get(endpoint.group)
                        if explanation:
                            label = f"{label} ({explanation})"
                        links.append((label, link))
                except Exception as e:
                    logger.error(f"Error generating link for {endpoint.name}: {e}")

        # Also always include MTProto/SOCKS proxies for Telegram if they exist
        for endpoint in settings.endpoints:
            if endpoint.category == "telegram" and endpoint.protocol in ("mtproto", "socks"):
                link = generate_vpn_link(
                    endpoint.protocol,
                    {},
                    None,
                    endpoint=endpoint,
                )
                if link:
                    label = endpoint.sub_label or f"Telegram Proxy ({endpoint.country})"
                    if "socks" in endpoint.protocol:
                        label = f"🔓 {label} (Только для Telegram — SOCKS5)"
                    else:
                        label = f"💬 {label} (Только для Telegram — MTProto)"
                    links.append((label, link))

        # Fallback if no specific endpoints matched
        if not links:
            base_link = await self.get_active_vpn_link(user)
            if base_link:
                links.append(("Основное подключение", base_link))

        return links

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

        # BUG-3 FIX: Don't switch to the same protocol
        if user.active_profile and user.active_profile.protocol_name == protocol_name:
            return False, "Этот протокол уже активен."

        # Revoke current active profile before creating a new one
        if user.active_profile:
            await self.revoke_vpn(user)

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

    async def get_all_users_stats(self) -> dict[str, dict[str, int]]:
        """Fetch traffic stats for ALL users from all panels in bulk.

        Returns a mapping of {email: {"upload": N, "download": M}}.
        """
        aggregated_stats = {}
        panels = self._get_active_panels()

        # 2. Fetch stats in parallel from all panels
        results = await asyncio.gather(
            *[self._fetch_panel_stats(p) for p in panels], return_exceptions=True
        )

        for res in results:
            if isinstance(res, list):
                for stat in res:
                    email = stat.get("email")
                    if not email:
                        continue

                    # Strip port suffix if present (e.g. "user@domain.com-443")
                    base_email = email.split("-")[0] if "-" in email else email

                    if base_email not in aggregated_stats:
                        aggregated_stats[base_email] = {"upload": 0, "download": 0}

                    aggregated_stats[base_email]["upload"] += stat.get("up", 0)
                    aggregated_stats[base_email]["download"] += stat.get("down", 0)

        return aggregated_stats

    async def _fetch_panel_stats(self, panel) -> list[dict]:
        try:
            async with panel:
                return await panel.get_all_client_traffics()
        except Exception as e:
            logger.error(f"Failed to fetch stats from {panel.api_url}: {e}")
            return []
