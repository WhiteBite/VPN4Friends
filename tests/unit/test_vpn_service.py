"""Unit tests for VPNService."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import RequestStatus, User, VPNRequest
from src.services.vpn_service import VPNService


@pytest.fixture
def mock_xui_api():
    """Mock XUI API."""
    with patch("src.services.vpn_service.XUIApi") as mock:
        instance = mock.return_value
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)

        # Default mock responses
        instance.add_client_to_all_inbounds = AsyncMock(return_value=2)
        instance.remove_client_from_all_inbounds = AsyncMock(return_value=1)

        # Reality fallback data (normally fetched from panel if inbound_id is None)
        instance.get_inbound_by_id = AsyncMock(
            return_value={
                "streamSettings": '{"security": "reality", "realitySettings": {"serverNames": ["max.ru", "vk.com"]}}',
                "protocol": "vless",
            }
        )

        yield instance


@pytest.fixture
def mock_hiddify_api():
    """Mock Hiddify API."""
    with patch("src.services.hiddify_api.HiddifyApi") as mock:
        instance = mock.return_value
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)

        # Default mock responses
        instance.add_client_to_all_inbounds = AsyncMock(return_value=1)
        instance.remove_client_from_all_inbounds = AsyncMock(return_value=1)

        yield instance


@pytest.mark.asyncio
async def test_approve_request_success(db_session: AsyncSession, mock_xui_api, mock_hiddify_api):
    """Test successful request approval flow."""
    # Create user and pending request
    user = User(telegram_id=123, username="test", full_name="Test")
    db_session.add(user)
    await db_session.commit()

    vpn_request = VPNRequest(user_id=user.id, status=RequestStatus.PENDING)
    db_session.add(vpn_request)
    await db_session.commit()
    # Add mock endpoint to settings to bypass env parsing issues
    from src.bot.config import ServerEndpoint, settings

    mock_endpoint = ServerEndpoint(
        name="finland_xhttp",
        label="Test",
        host="test.local",
        port=443,
        protocol="vless",
        security="reality",
    )
    settings.endpoints = [mock_endpoint]

    service = VPNService(db_session)

    # Approve request targeting the "finland_xhttp" mock endpoint
    success, msg = await service.approve_request(
        request_id=vpn_request.id, protocol_name="finland_xhttp"
    )

    # Assertions
    assert success is True, f"Approval failed: {msg}"
    assert msg.startswith("vless://")

    # Wait for background task or flush
    await db_session.refresh(vpn_request)
    assert vpn_request.status == RequestStatus.APPROVED

    # Check that panel API was called
    mock_xui_api.add_client_to_all_inbounds.assert_called_once()
    _, kwargs = mock_xui_api.add_client_to_all_inbounds.call_args
    assert kwargs.get("email") or _[0] if _ else kwargs["email"]  # Email was passed
    assert kwargs.get("protocol", _[2] if len(_) > 2 else None) in ("vless", "all")


@pytest.mark.asyncio
async def test_reject_request_success(db_session: AsyncSession):
    """Test successful request rejection flow."""
    user = User(telegram_id=124, username="test_reject", full_name="Test Reject")
    db_session.add(user)
    await db_session.commit()

    vpn_request = VPNRequest(user_id=user.id, status=RequestStatus.PENDING)
    db_session.add(vpn_request)
    await db_session.commit()

    service = VPNService(db_session)

    # Reject request
    success = await service.reject_request(request_id=vpn_request.id, comment="Spam account")

    assert success is True
    await db_session.refresh(vpn_request)
    assert vpn_request.status == RequestStatus.REJECTED
