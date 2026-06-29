"""Application configuration using pydantic-settings."""

import json
from typing import Any

from pydantic import BaseModel, field_validator, model_validator
from pydantic_settings import BaseSettings


class Protocol(BaseModel):
    """Represents a single VPN protocol configuration."""

    name: str
    inbound_id: int
    label: str
    description: str
    recommended: bool = False
    icon: str | None = None


class ServerEndpoint(BaseModel):
    """Represents a VPN entry point (relay or direct server).

    Each endpoint knows its panel type and auth credentials.
    """

    name: str
    label: str
    host: str
    port: int = 443
    is_relay: bool = False
    target: str | None = None  # For relays: name of the actual server endpoint
    description: str = ""
    panel_type: str = "3xui"  # "3xui" or "hiddify"
    panel_config: dict = {}  # Panel-specific credentials
    protocol: str = "vless"  # Protocol type: "vless", "mtproto", etc.

    # Categorization fields for the UI
    category: str = "vpn"  # "vpn", "telegram"
    country: str = "Финляндия"  # "Финляндия", "Германия", "Нидерланды"

    # Extra parameters for relays or advanced endpoints
    transport: str | None = None
    security: str | None = None
    sni: str | None = None
    flow: str | None = None
    serviceName: str | None = None
    path: str | None = None
    host_override: str | None = None  # Using host_override to avoid collision with base host
    secret: str | None = None  # MTProto secret

    # Reality-specific overrides
    pbk: str | None = None
    pk: str | None = None
    sid: str | None = None
    fp: str | None = None
    spx: str | None = None

    # SSH configuration for automated setup and self-healing (optional)
    ssh_host: str | None = None
    ssh_user: str | None = None
    ssh_key: str | None = None
    ssh_port: int = 22

    # Subscription grouping & display
    group: str = "fast"  # "fast", "warp", "stealth", "stealth_warp", "moscow", "cdn"
    sub_label: str = ""  # Label in subscription: "⚡ 🇫🇮 Финляндия"
    sort_order: int = 100  # Sorting within subscription (lower = higher)
    visible_in_sub: bool = True  # Include in subscription output
    routing_tag: str = "direct"  # Outbound tag for provisioner routing: "direct" or "warp"


class GroupConfig(BaseModel):
    """Metadata for grouping endpoints in subscriptions and UI."""

    name: str  # e.g., "fast"
    order: int  # Sorting order
    label: str  # Display label with emoji
    explanation: str | None = None  # Brief tooltip text


class Settings(BaseSettings):
    """Bot configuration loaded from environment variables."""

    # Telegram
    bot_token: str
    admin_ids: list[int] = []
    miniapp_url: str = ""
    jwt_secret: str = "change-me-in-production-please"  # Default for dev
    # 3X-UI Panel
    xui_api_url: str
    xui_base_path: str = "/panel"
    xui_username: str
    xui_password: str
    xui_host: str

    # Global Reality Keys
    reality_private_key: str = ""
    reality_public_key: str = ""
    reality_short_id: str = ""

    # Protocols configuration (JSON string from .env)
    protocols_config: str = "[]"
    protocols: list[Protocol] = []

    # Server groups metadata (JSON string from .env)
    groups_config_raw: str = ""
    groups_config: dict[str, GroupConfig] = {}

    # Server endpoints (JSON string from .env)
    endpoints_config: str = "[]"
    endpoints: list[ServerEndpoint] = []

    # Node topology: outbounds + routing (JSON string from .env)
    nodes_config_raw: str = "{}"
    nodes_config: dict = {}

    # Database - use env var if set (e.g. in Docker), else fallback to local file
    database_url: str = "sqlite+aiosqlite:///vpn_bot.db"

    # MTProto Proxy for Telegram
    mtproto_proxy_host: str = ""
    mtproto_proxy_port: int = 0
    mtproto_proxy_secret: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "env_prefix": "",
    }

    @model_validator(mode="after")
    def parse_protocols_config(self) -> "Settings":
        """Parse PROTOCOLS_CONFIG JSON string into a list of Protocol objects."""
        try:
            protocols_data = json.loads(self.protocols_config)
            if not isinstance(protocols_data, list):
                raise ValueError("PROTOCOLS_CONFIG must be a JSON array")
            self.protocols = [Protocol(**p) for p in protocols_data]
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid PROTOCOLS_CONFIG: {e}") from e
        return self

    @model_validator(mode="after")
    def parse_endpoints_config(self) -> "Settings":
        """Parse ENDPOINTS_CONFIG JSON string into a list of ServerEndpoint objects.

        Optionally merges additional endpoints from a JSON file pointed to by
        ENDPOINTS_CONFIG_EXT_FILE env var. This lets large endpoint lists (e.g.
        many VPNUS locations) live outside the env_file, which has a line-length
        limit that causes silent truncation for long values.
        """
        import os

        try:
            endpoints_data = json.loads(self.endpoints_config)
            if not isinstance(endpoints_data, list):
                raise ValueError("ENDPOINTS_CONFIG must be a JSON array")
        except (json.JSONDecodeError, ValueError):
            endpoints_data = []

        # Merge optional extension file (e.g. /opt/vpn4friends-endpoints-vpnus.json)
        ext_file = os.environ.get("ENDPOINTS_CONFIG_EXT_FILE", "")
        if ext_file:
            try:
                with open(ext_file, encoding="utf-8") as fh:
                    ext_data = json.load(fh)
                if isinstance(ext_data, list):
                    existing_names = {e.get("name") for e in endpoints_data if isinstance(e, dict)}
                    for entry in ext_data:
                        if isinstance(entry, dict) and entry.get("name") not in existing_names:
                            endpoints_data.append(entry)
            except (OSError, json.JSONDecodeError):
                pass  # file missing or malformed — silently ignore

        self.endpoints = [ServerEndpoint(**e) for e in endpoints_data]
        return self

    @model_validator(mode="after")
    def parse_groups_config(self) -> "Settings":
        """Parse GROUPS_CONFIG_RAW JSON string into a dict of GroupConfig objects."""
        default_groups = {
            "fast": {
                "name": "fast",
                "order": 1,
                "label": "⚡ Быстрый",
                "explanation": "Прямое подключение, мин. пинг",
            },
            "warp": {
                "name": "warp",
                "order": 2,
                "label": "🎬 Разблокировка",
                "explanation": "Для Netflix, ChatGPT и др.",
            },
            "stealth": {
                "name": "stealth",
                "order": 3,
                "label": "🛡 Стойкий",
                "explanation": "Скрытый протокол для сложных сетей",
            },
            "stealth_warp": {
                "name": "stealth_warp",
                "order": 4,
                "label": "🛡🎬 Стойкий + Разблокировка",
                "explanation": "Скрытый вход + разблокировка",
            },
            "moscow": {
                "name": "moscow",
                "order": 5,
                "label": "📱 Через Москву",
                "explanation": "Обход блокировок (если не заходит)",
            },
            "cdn": {
                "name": "cdn",
                "order": 6,
                "label": "☁️ CDN Fallback",
                "explanation": "Медленный, через Cloudflare",
            },
        }

        try:
            if not self.groups_config_raw:
                # Use defaults if not provided in env
                self.groups_config = {k: GroupConfig(**v) for k, v in default_groups.items()}
                return self

            groups_data = json.loads(self.groups_config_raw)
            if not isinstance(groups_data, dict):
                raise ValueError("GROUPS_CONFIG_RAW must be a JSON object")
            self.groups_config = {k: GroupConfig(**v) for k, v in groups_data.items()}
        except (json.JSONDecodeError, ValueError):
            # Fallback to default on error
            self.groups_config = {k: GroupConfig(**v) for k, v in default_groups.items()}
        return self

    @model_validator(mode="after")
    def parse_nodes_config(self) -> "Settings":
        """Parse NODES_CONFIG_RAW JSON string into a dict of node configs."""
        try:
            nodes_data = json.loads(self.nodes_config_raw)
            if isinstance(nodes_data, dict):
                self.nodes_config = nodes_data
        except (json.JSONDecodeError, ValueError):
            self.nodes_config = {}
        return self

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: Any) -> list[int]:
        if not value:
            return []

        if isinstance(value, int):
            return [value]

        # If it's already a list, clean up each string element before int conversion
        if isinstance(value, list):
            import re

            cleaned_ints = []
            for item in value:
                # Extract numbers from string representation like '[1234]'
                nums = re.findall(r"\d+", str(item))
                cleaned_ints.extend([int(n) for n in nums])
            return cleaned_ints

        if isinstance(value, str):
            import re

            # Extract all numbers using regex, this handles "123, 456", "[123, 456]" and '"[123]"'
            numbers = re.findall(r"\d+", str(value))
            return [int(n) for n in numbers]

        try:
            return [int(value)]
        except (ValueError, TypeError):
            return []

    def get_protocol(self, protocol_name: str) -> Protocol | None:
        """Get protocol object by name."""
        for proto in self.protocols:
            if proto.name == protocol_name:
                return proto
        return None

    def get_endpoint(self, endpoint_name: str) -> ServerEndpoint | None:
        """Get server endpoint by name."""
        for ep in self.endpoints:
            if ep.name == endpoint_name:
                return ep
        return None


settings = Settings()
