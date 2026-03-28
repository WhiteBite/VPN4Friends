"""Application configuration using pydantic-settings."""

import json

from pydantic import BaseModel, field_validator, model_validator
from pydantic_settings import BaseSettings


class Protocol(BaseModel):
    """Represents a single VPN protocol configuration."""

    name: str
    inbound_id: int
    label: str
    description: str
    recommended: bool = False


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

    # Reality-specific overrides
    pbk: str | None = None
    sid: str | None = None
    fp: str | None = None
    spx: str | None = None


class Settings(BaseSettings):
    """Bot configuration loaded from environment variables."""

    # Telegram
    bot_token: str
    admin_ids: list[int] = []
    miniapp_url: str = ""

    @model_validator(mode="after")
    def get_admin_ids_from_env(self) -> "Settings":
        """Force-load admin_ids from environment variable to bypass parsing issues."""
        import os

        admin_ids_str = os.getenv("ADMIN_IDS")
        if admin_ids_str:
            self.admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
        return self

    # 3X-UI Panel
    xui_api_url: str
    xui_base_path: str = "/panel"
    xui_username: str
    xui_password: str
    xui_host: str

    # Global Reality Keys
    reality_public_key: str = ""
    reality_short_id: str = ""

    # Protocols configuration (JSON string from .env)
    protocols_config: str = "[]"
    protocols: list[Protocol] = []

    # Server endpoints (JSON string from .env)
    endpoints_config: str = "[]"
    endpoints: list[ServerEndpoint] = []

    # Database (absolute path for Docker)
    database_url: str = "sqlite+aiosqlite:////app/data/vpn_bot.db"

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
        """Parse ENDPOINTS_CONFIG JSON string into a list of ServerEndpoint objects."""
        try:
            endpoints_data = json.loads(self.endpoints_config)
            if not isinstance(endpoints_data, list):
                raise ValueError("ENDPOINTS_CONFIG must be a JSON array")
            self.endpoints = [ServerEndpoint(**e) for e in endpoints_data]
        except (json.JSONDecodeError, ValueError):
            # Endpoints are optional — don't crash if not configured
            self.endpoints = []
        return self

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str) -> list[int]:
        if isinstance(value, str):
            return [int(x.strip()) for x in value.split(",") if x.strip()]
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
