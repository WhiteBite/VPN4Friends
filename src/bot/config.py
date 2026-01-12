"""Application configuration using pydantic-settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings


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
    inbound_id: int

    # Database (absolute path for Docker)
    database_url: str = "sqlite+aiosqlite:////app/data/vpn_bot.db"

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
