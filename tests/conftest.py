"""Test configuration and fixtures."""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

# Load test environment variables before importing settings
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

test_env_path = Path(__file__).parent.parent / ".env.test"
load_dotenv(test_env_path, override=True)

from src.api.main import app  # noqa: E402
from src.bot.config import Settings  # noqa: E402
from src.database.models import Base  # noqa: E402

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        admin_ids=[123456789],
        miniapp_url="https://test-app.example.com",
        xui_finland_url="https://test-panel.example.com",
        xui_finland_login="test_login",
        xui_finland_password="test_password",
        reality_uuid="test-uuid",
        reality_private_key="test-private-key",
        reality_public_key="test-public-key",
        reality_short_id="test1234",
        mtproto_proxy_host="test.example.com",
        mtproto_proxy_port=4443,
        mtproto_proxy_secret="test_secret",
        endpoints_config="[]",
    )


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        yield session

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def api_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test API client."""
    # Override dependency to use test database
    app.dependency_overrides = {}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
def mock_user_data() -> dict[str, Any]:
    """Mock user data."""
    return {
        "telegram_id": 123456789,
        "username": "testuser",
        "full_name": "Test User",
        "is_admin": False,
    }


@pytest.fixture
def mock_vpn_request_data() -> dict[str, Any]:
    """Mock VPN request data."""
    return {
        "user_id": 1,
        "status": "pending",
    }


@pytest.fixture
def mock_endpoint_data() -> dict[str, Any]:
    """Mock endpoint data."""
    return {
        "name": "finland_xhttp",
        "label": "🇫🇮 Финляндия (xHTTP)",
        "host": "test.example.com",
        "port": 443,
        "protocol": "vless",
        "security": "reality",
        "sni": "max.ru",
        "flow": "xtls-rprx-vision",
    }


@pytest.fixture
def mock_bot() -> AsyncMock:
    """Create a mock bot instance."""
    bot = AsyncMock()
    bot.id = 123456789
    bot.username = "test_bot"
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    return bot


@pytest_asyncio.fixture
async def dispatcher(db_session: AsyncSession) -> Any:
    """Create a dispatcher with all routers and middlewares."""
    import logging
    import traceback

    from aiogram import Dispatcher

    from src.bot.middlewares import DatabaseMiddleware
    from src.bot.middlewares.ui_mode import UIModeMiddleware

    # Configure logging to see what's happening
    logging.basicConfig(level=logging.DEBUG)

    dp = Dispatcher()

    # AIOGRAM 3 log any errors in tests
    @dp.errors()
    async def error_handler(event: Any, exception: Exception):
        print(f"\n!!! DISPATCHER ERROR: {exception}")
        traceback.print_exc()
        return False

    # Fixed session factory mock: must be a function returning an async context manager
    class SessionContextManager:
        def __init__(self, session):
            self.session = session

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    def session_factory_mock():
        return SessionContextManager(db_session)

    dp.update.middleware(DatabaseMiddleware(session_factory_mock))
    dp.update.middleware(UIModeMiddleware())

    from src.handlers.admin import router as admin_router
    from src.handlers.messaging import admin_router as admin_messaging_router
    from src.handlers.messaging import user_router as user_messaging_router
    from src.handlers.user import router as user_router

    # Reset internal parent_router to allow re-attachment in different tests
    # AIOGRAM 3.x+ doesn't allow None via the public property setter
    for r in [user_router, user_messaging_router, admin_router, admin_messaging_router]:
        if r is not None:
            print(f"DEBUG: Including router {r.name if hasattr(r, 'name') else 'unnamed'}")
            r._parent_router = None
            dp.include_router(r)

    return dp
