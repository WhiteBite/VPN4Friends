"""Comprehensive tests for VPN service business logic."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import RequestStatus, User, VPNRequest
from src.services.vpn_service import VPNService


class TestVPNServiceCreateRequest:
    """Tests for VPNService.create_request - all scenarios."""

    @pytest.mark.asyncio
    async def test_create_request_success(self, db_session: AsyncSession):
        """Test creating request for eligible user."""
        user = User(
            telegram_id=100001,
            username="newuser",
            full_name="New User",
            has_vpn=False,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        service = VPNService(db_session)
        request = await service.create_request(user)

        assert request is not None
        assert request.status == RequestStatus.PENDING
        assert request.user_id == user.id

    @pytest.mark.asyncio
    async def test_create_request_user_has_vpn(self, db_session: AsyncSession):
        """Test that user with active VPN cannot create request."""
        user = User(
            telegram_id=100002,
            username="hasvpn",
            full_name="Has VPN",
            has_vpn=True,
        )
        db_session.add(user)
        await db_session.commit()

        service = VPNService(db_session)
        request = await service.create_request(user)

        assert request is None

    @pytest.mark.asyncio
    async def test_create_request_pending_exists(self, db_session: AsyncSession):
        """Test that user cannot create duplicate pending request."""
        user = User(
            telegram_id=100003,
            username="pending",
            full_name="Pending User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create first request
        service = VPNService(db_session)
        request1 = await service.create_request(user)
        assert request1 is not None

        # Try to create second
        request2 = await service.create_request(user)
        assert request2 is None

    @pytest.mark.asyncio
    async def test_create_request_approved_exists(self, db_session: AsyncSession):
        """Test that user with approved request cannot create new one."""
        user = User(
            telegram_id=100004,
            username="approved",
            full_name="Approved User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create approved request
        request = VPNRequest(user_id=user.id, status=RequestStatus.APPROVED)
        db_session.add(request)
        await db_session.commit()

        service = VPNService(db_session)
        new_request = await service.create_request(user)

        assert new_request is None


class TestVPNServiceApproveRequest:
    """Tests for VPNService.approve_request - all scenarios."""

    @pytest.mark.asyncio
    async def test_approve_nonexistent_request(self, db_session: AsyncSession):
        """Test approving non-existent request."""
        service = VPNService(db_session)
        success, message = await service.approve_request(99999, "finland_xhttp")

        assert success is False
        assert "не найдена" in message.lower()

    @pytest.mark.asyncio
    async def test_approve_already_approved_request(self, db_session: AsyncSession):
        """Test approving already approved request."""
        user = User(telegram_id=200001, username="test", full_name="Test")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        request = VPNRequest(user_id=user.id, status=RequestStatus.APPROVED)
        db_session.add(request)
        await db_session.commit()

        service = VPNService(db_session)
        success, message = await service.approve_request(request.id, "finland_xhttp")

        assert success is False
        assert "уже обработана" in message.lower()

    @pytest.mark.asyncio
    async def test_approve_already_rejected_request(self, db_session: AsyncSession):
        """Test approving rejected request."""
        user = User(telegram_id=200002, username="test2", full_name="Test2")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        request = VPNRequest(user_id=user.id, status=RequestStatus.REJECTED)
        db_session.add(request)
        await db_session.commit()

        service = VPNService(db_session)
        success, message = await service.approve_request(request.id, "finland_xhttp")

        assert success is False
        assert "уже обработана" in message.lower()

    @pytest.mark.asyncio
    async def test_approve_user_has_vpn(self, db_session: AsyncSession):
        """Test approving request when user already has VPN."""
        user = User(telegram_id=200003, username="hasvpn", full_name="Has VPN", has_vpn=True)
        db_session.add(user)
        await db_session.commit()

        request = VPNRequest(user_id=user.id, status=RequestStatus.PENDING)
        db_session.add(request)
        await db_session.commit()

        service = VPNService(db_session)
        success, message = await service.approve_request(request.id, "finland_xhttp")

        assert success is False
        assert "уже есть активный VPN" in message

    @pytest.mark.asyncio
    async def test_approve_nonexistent_endpoint(self, db_session: AsyncSession):
        """Test approving with non-existent endpoint."""
        user = User(telegram_id=200004, username="test4", full_name="Test4")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        request = VPNRequest(user_id=user.id, status=RequestStatus.PENDING)
        db_session.add(request)
        await db_session.commit()

        service = VPNService(db_session)
        success, message = await service.approve_request(request.id, "nonexistent_endpoint")

        assert success is False
        assert "не настроен" in message.lower()


class TestVPNServiceRejectRequest:
    """Tests for VPNService.reject_request - all scenarios."""

    @pytest.mark.asyncio
    async def test_reject_nonexistent_request(self, db_session: AsyncSession):
        """Test rejecting non-existent request."""
        service = VPNService(db_session)
        result = await service.reject_request(99999, "Test rejection")

        assert result is False

    @pytest.mark.asyncio
    async def test_reject_already_approved_request(self, db_session: AsyncSession):
        """Test rejecting already approved request."""
        user = User(telegram_id=300001, username="test", full_name="Test")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        request = VPNRequest(user_id=user.id, status=RequestStatus.APPROVED)
        db_session.add(request)
        await db_session.commit()

        service = VPNService(db_session)
        result = await service.reject_request(request.id, "Test")

        assert result is False

    @pytest.mark.asyncio
    async def test_reject_success(self, db_session: AsyncSession):
        """Test successful rejection."""
        user = User(telegram_id=300002, username="rejectme", full_name="Reject Me")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        request = VPNRequest(user_id=user.id, status=RequestStatus.PENDING)
        db_session.add(request)
        await db_session.commit()

        service = VPNService(db_session)
        result = await service.reject_request(request.id, "Test rejection reason")

        assert result is True

        # Verify status changed
        await db_session.refresh(request)
        assert request.status == RequestStatus.REJECTED
        assert request.admin_comment == "Test rejection reason"


class TestVPNServiceEdgeCases:
    """Edge case tests for VPNService."""

    @pytest.mark.asyncio
    async def test_multiple_users_concurrent_requests(self, db_session: AsyncSession):
        """Test creating requests for multiple users."""
        users = []
        for i in range(5):
            user = User(
                telegram_id=400000 + i,
                username=f"user{i}",
                full_name=f"User {i}",
            )
            db_session.add(user)
            users.append(user)

        await db_session.commit()

        service = VPNService(db_session)
        requests = []
        for user in users:
            request = await service.create_request(user)
            requests.append(request)

        # All requests should be created
        assert all(r is not None for r in requests)
        assert len(set(r.id for r in requests)) == 5  # All unique

    @pytest.mark.asyncio
    async def test_revert_to_pending_on_error(self, db_session: AsyncSession):
        """Test that request reverts to pending on error."""
        user = User(telegram_id=500001, username="errortest", full_name="Error Test")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        request = VPNRequest(user_id=user.id, status=RequestStatus.PENDING)
        db_session.add(request)
        await db_session.commit()

        service = VPNService(db_session)
        # Try to approve with non-existent endpoint - should fail gracefully
        success, message = await service.approve_request(request.id, "nonexistent")

        assert success is False

        # Request should still be pending (reverted)
        await db_session.refresh(request)
        assert request.status == RequestStatus.PENDING
