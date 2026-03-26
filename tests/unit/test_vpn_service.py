"""Unit tests for VPN service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, VPNRequest, RequestStatus
from src.services.vpn_service import VPNService


class TestVPNService:
    """Tests for VPNService."""

    @pytest.mark.asyncio
    async def test_create_request_success(self, db_session: AsyncSession, mock_user_data: dict):
        """Test creating VPN request for user."""
        # Create user
        user = User(
            telegram_id=mock_user_data["telegram_id"],
            username=mock_user_data["username"],
            full_name=mock_user_data["full_name"],
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create service and request
        service = VPNService(db_session)
        request = await service.create_request(user)

        assert request is not None
        assert request.user_id == user.id
        assert request.status == RequestStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_request_duplicate(self, db_session: AsyncSession, mock_user_data: dict):
        """Test that user cannot create duplicate pending request."""
        # Create user
        user = User(
            telegram_id=mock_user_data["telegram_id"],
            username=mock_user_data["username"],
            full_name=mock_user_data["full_name"],
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create first request
        service = VPNService(db_session)
        request1 = await service.create_request(user)
        assert request1 is not None

        # Try to create second request
        request2 = await service.create_request(user)
        assert request2 is None

    @pytest.mark.asyncio
    async def test_create_request_with_active_vpn(
        self, db_session: AsyncSession, mock_user_data: dict
    ):
        """Test that user with active VPN cannot create request."""
        # Create user with VPN
        user = User(
            telegram_id=mock_user_data["telegram_id"],
            username=mock_user_data["username"],
            full_name=mock_user_data["full_name"],
            has_vpn=True,
        )
        db_session.add(user)
        await db_session.commit()

        # Try to create request
        service = VPNService(db_session)
        request = await service.create_request(user)

        assert request is None

    @pytest.mark.asyncio
    async def test_approve_request_not_found(self, db_session: AsyncSession):
        """Test approving non-existent request."""
        service = VPNService(db_session)
        success, message = await service.approve_request(999, "finland_xhttp")

        assert success is False
        assert "не найдена" in message.lower()

    @pytest.mark.asyncio
    async def test_approve_request_already_processed(
        self, db_session: AsyncSession, mock_user_data: dict
    ):
        """Test approving already processed request."""
        # Create user and request
        user = User(
            telegram_id=mock_user_data["telegram_id"],
            username=mock_user_data["username"],
            full_name=mock_user_data["full_name"],
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        request = VPNRequest(user_id=user.id, status=RequestStatus.APPROVED)
        db_session.add(request)
        await db_session.commit()

        # Try to approve
        service = VPNService(db_session)
        success, message = await service.approve_request(request.id, "finland_xhttp")

        assert success is False
        assert "уже обработана" in message.lower()


class TestXuiService:
    """Tests for XuiService."""

    @pytest.mark.asyncio
    async def test_service_initialization(self, test_settings):
        """Test XuiService initialization."""
        from src.services.xui_service import XuiService

        service = XuiService(test_settings)

        assert service.base_url == test_settings.xui_finland_url.rstrip("/")
        assert service.login == test_settings.xui_finland_login
        assert service.password == test_settings.xui_finland_password

    @pytest.mark.asyncio
    async def test_close_session(self, test_settings):
        """Test closing XuiService session."""
        from src.services.xui_service import XuiService

        service = XuiService(test_settings)
        await service.close()

        assert service._session is None or service._session.is_closed
