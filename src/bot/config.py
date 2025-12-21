"""Application configuration using pydantic-settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Bot configuration loaded from environment variables."""

    # Telegram
    bot_token: str
    admin_ids: list[int] = []

    # 3X-UI Panel
    xui_api_url: str = "http://localhost:54321"
    xui_base_path: str = "/panel"
    xui_username: str = "admin"
    xui_password: str = "admin"
    xui_host: str = "your-server.com"
    inbound_id: int = 1

    # Reality settings
    reality_public_key: str = ""
    reality_fingerprint: str = "chrome"
    reality_sni: str = "example.com"
    reality_short_id: str = ""
    reality_spider_x: str = "/"

    # Database
    database_url: str = "sqlite+aiosqlite:///vpn_bot.db"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str | list[int] | int) -> list[int]:
        if isinstance(value, int):
            return [value]
        if isinstance(value, str):
            return [int(x.strip()) for x in value.split(",") if x.strip()]
        return value


settings = Settings()
