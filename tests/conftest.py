"""Test configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.main import app
from src.bot.config import Settings
from src.database.models import Base
from src.database.session import session_factory


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
