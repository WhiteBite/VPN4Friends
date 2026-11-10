"""Regression tests for the subscription endpoint lookup."""

import base64

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import src.api.routers.subscription as subscription_module
from src.api.main import app
from src.bot.config import ServerEndpoint, settings
from src.database.models import Base, User, VpnProfile


@pytest.mark.asyncio
async def test_subscription_found_by_profile_data_client_id(tmp_path):
    """Subscription resolves profiles whose client_id lives only in profile_data."""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'sub.db'}"
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    token = "cid-in-json-only"
    async with maker() as session:
        user = User(telegram_id=900000001, full_name="Sub Tester")
        session.add(user)
        await session.flush()
        session.add(
            VpnProfile(
                user_id=user.id,
                protocol_name="vless",
                client_id=None,
                profile_data={"client_id": token, "email": "Sub Tester"},
                is_active=True,
            )
        )
        await session.commit()

    original_factory = subscription_module.session_factory
    original_endpoints = settings.endpoints
    subscription_module.session_factory = maker
    settings.endpoints = [
        ServerEndpoint(
            name="tcp",
            label="Direct",
            host="ger1.example",
            port=8443,
            protocol="vless",
            category="vpn",
            transport="tcp",
            security="reality",
            sni="www.microsoft.com",
            flow="xtls-rprx-vision",
            pbk="PUBKEY",
            sid="a1b2c3d4e5f67890",
            visible_in_sub=True,
        )
    ]
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/sub/{token}")
            missing = await client.get("/api/sub/does-not-exist")
    finally:
        subscription_module.session_factory = original_factory
        settings.endpoints = original_endpoints
        await engine.dispose()

    assert response.status_code == 200
    decoded = base64.b64decode(response.text).decode("utf-8")
    assert token in decoded
    assert missing.status_code == 404
