"""Application configuration using pydantic-settings."""

import json
import logging
import os

from pydantic import BaseModel, field_validator, model_validator
from pydantic_settings import BaseSettings

# --- Direct Environment Variable Check ---
raw_admin_ids = os.getenv("ADMIN_IDS")
logging.info(f"[DIRECT ENV CHECK] Raw ADMIN_IDS from os.getenv: {raw_admin_ids!r}")
# --- End Check ---

class Protocol(BaseModel):
    """Represents a single VPN protocol configuration."""

    name: str
    inbound_id: int
    label: str
    description: str
    recommended: bool = False


class Settings(BaseSettings):
    """Bot configuration loaded from environment variables."""

    # Telegram
    bot_token: str
    admin_ids: list[int] = []

    # 3X-UI Panel
    xui_api_url: str
    xui_base_path: str = "/panel"
    xui_username: str
    xui_password: str
    xui_host: str

    # Protocols configuration (JSON string from .env)
    protocols_config: str = "[]"
    protocols: list[Protocol] = []

    # Database (absolute path for Docker)
    database_url: str = "sqlite+aiosqlite:////app/data/vpn_bot.db"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
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

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str) -> list[int]:
        # --- Temporary Debugging --- 
        import logging
        logging.info(f"[DEBUG] Raw ADMIN_IDS value from .env: {value!r} (type: {type(value)})")
        # --- End Debugging ---
        if isinstance(value, str):
            return [int(x.strip()) for x in value.split(",") if x.strip()]
        return []

    def get_protocol(self, protocol_name: str) -> Protocol | None:
        """Get protocol object by name."""
        for proto in self.protocols:
            if proto.name == protocol_name:
                return proto
        return None


settings = Settings()
