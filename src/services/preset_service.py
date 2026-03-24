"""Preset service for business logic."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.database.models import ConnectionPreset, User
from src.database.repositories import PresetRepository, UserRepository
from src.services.url_generator import generate_vpn_link, merge_profile_settings

logger = logging.getLogger(__name__)


def _build_clash_vless_yaml(profile_data: dict[str, Any], name: str) -> str:
    """Build a minimal Clash/Hiddify YAML config for a VLESS Reality node."""
    reality = profile_data.get("reality", {}) or {}
    host = profile_data.get("host", settings.xui_host)
    port = profile_data.get("port")
    client_id = profile_data.get("client_id", "")

    sni = reality.get("sni", "")
    public_key = reality.get("public_key", "")
    short_id = reality.get("short_id", "")
    spider_x = reality.get("spider_x", "/")
    fingerprint = reality.get("fingerprint", "chrome")

    # Single-proxy YAML snippet compatible with Clash/Hiddify.
    lines = [
        "proxies:",
        f"  - name: {name}",
        "    type: vless",
        f"    server: {host}",
        f"    port: {port}",
        f"    uuid: {client_id}",
        "    flow: xtls-rprx-vision",
        "    tls: true",
        f"    servername: {sni}",
        "    reality-opts:",
        f"      public-key: {public_key}",
        f"      short-id: {short_id}",
        f"      spider-x: {spider_x}",
        f"    client-fingerprint: {fingerprint}",
        "    network: tcp",
    ]

    return "\n".join(lines)


def _build_clash_shadowsocks_yaml(profile_data: dict[str, Any], name: str) -> str:
    """Build a minimal Clash/Hiddify YAML config for a Shadowsocks node."""
    host = profile_data.get("host", settings.xui_host)
    port = profile_data.get("port")
    shadowsocks = profile_data.get("shadowsocks", {}) or {}
    method = shadowsocks.get("method", "")
    password = shadowsocks.get("password", "")

    lines = [
        "proxies:",
        f"  - name: {name}",
        "    type: ss",
        f"    server: {host}",
        f"    port: {port}",
        f"    cipher: {method}",
        f"    password: {password}",
    ]

    return "\n".join(lines)


class PresetService:
    """Service for preset-related business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.preset_repo = PresetRepository(session)

    async def create_preset(
        self, user: User, name: str, app_type: str, format: str, options: dict | None = None
    ) -> ConnectionPreset | None:
        """Create a new connection preset for the user's active profile."""
        active_profile = user.active_profile
        if not active_profile:
            logger.warning(f"User {user.telegram_id} has no active profile to create a preset for.")
            return None

        preset = await self.preset_repo.create(
            user=user,
            profile=active_profile,
            name=name,
            app_type=app_type,
            format=format,
            options=options,
        )
        logger.info(f"Created preset {preset.id} for user {user.telegram_id}")
        return preset

    async def get_user_presets(self, user: User) -> list[ConnectionPreset]:
        """Get all presets for a user."""
        return await self.preset_repo.get_by_user(user)

    async def delete_preset(self, user: User, preset_id: int) -> bool:
        """Delete a preset if it belongs to the user."""
        preset = await self.preset_repo.get_by_id(preset_id)
        if not preset or preset.user_id != user.id:
            return False

        await self.preset_repo.delete(preset)
        logger.info(f"Deleted preset {preset_id} for user {user.telegram_id}")
        return True

    async def get_preset_for_user(self, user: User, preset_id: int) -> ConnectionPreset | None:
        """Get a preset by ID only if it belongs to the given user."""
        preset = await self.preset_repo.get_by_id(preset_id)
        if not preset or preset.user_id != user.id:
            return None
        return preset

    async def generate_config(self, preset: ConnectionPreset) -> dict[str, str] | None:
        """Generate the final config for a preset."""
        profile = preset.profile
        if not profile:
            # This should ideally not happen if DB constraints are set up
            logger.error(f"Preset {preset.id} has no associated profile.")
            return None

        # Raw profile data from 3X-UI panel
        full_profile_data = profile.profile_data

        # Clash/Hiddify YAML config
        if preset.format == "clash_yaml":
            if profile.protocol_name == "vless":
                prepared = merge_profile_settings(full_profile_data, profile.settings or {})
                yaml_config = _build_clash_vless_yaml(prepared, preset.name)
                return {"type": "yaml", "value": yaml_config}
            if profile.protocol_name == "shadowsocks":
                yaml_config = _build_clash_shadowsocks_yaml(full_profile_data, preset.name)
                return {"type": "yaml", "value": yaml_config}

            logger.warning(
                "Unsupported protocol '%s' for clash_yaml format in preset %s",
                profile.protocol_name,
                preset.id,
            )
            return None

        # Generic URI-based config (VLESS/Shadowsocks, etc.)
        if preset.format.endswith("_uri"):
            link = generate_vpn_link(profile.protocol_name, full_profile_data, profile.settings)
            if link:
                return {"type": "uri", "value": link}

        logger.warning("Unsupported format '%s' for preset %s", preset.format, preset.id)
        return None
