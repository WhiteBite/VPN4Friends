"""Unit tests for database repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import RequestStatus, User, VPNRequest
from src.database.repositories.request_repo import RequestRepository
from src.database.repositories.user_repo import UserRepository


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a new user."""
        repo = UserRepository(db_session)

        user = await repo.create(
            telegram_id=123456789,
            username="testuser",
            full_name="Test User",
        )

        assert user is not None
        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.is_admin is False

    @pytest.mark.asyncio
    async def test_get_by_telegram_id(self, db_session: AsyncSession):
        """Test getting user by Telegram ID."""
        # Create user
        user = User(
            telegram_id=987654321,
            username="findme",
            full_name="Find Me",
        )
        db_session.add(user)
        await db_session.commit()

        # Get user
        repo = UserRepository(db_session)
        found_user = await repo.get_by_telegram_id(987654321)

        assert found_user is not None
        assert found_user.telegram_id == 987654321
        assert found_user.username == "findme"

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_not_found(self, db_session: AsyncSession):
        """Test getting non-existent user."""
        repo = UserRepository(db_session)
        user = await repo.get_by_telegram_id(999999999)

        assert user is None

    @pytest.mark.asyncio
    async def test_update_user(self, db_session: AsyncSession):
        """Test updating user."""
        # Create user
        user = User(
            telegram_id=111222333,
            username="updateme",
            full_name="Update Me",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Update user
        repo = UserRepository(db_session)
        user.is_admin = True
        updated = await repo.update(user)

        assert updated is not None
        assert updated.is_admin is True

    @pytest.mark.asyncio
    async def test_get_all_users(self, db_session: AsyncSession):
        """Test getting all users."""
        # Create multiple users
        for i in range(5):
            user = User(
                telegram_id=1000 + i,
                username=f"user{i}",
                full_name=f"User {i}",
            )
            db_session.add(user)

        await db_session.commit()

        # Get all users
        repo = UserRepository(db_session)
        users = await repo.get_all()

        assert len(users) >= 5


class TestRequestRepository:
    """Tests for RequestRepository."""

    @pytest.mark.asyncio
    async def test_create_request(self, db_session: AsyncSession):
        """Test creating VPN request."""
        # Create user
        user = User(
            telegram_id=555666777,
            username="requestuser",
            full_name="Request User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create request
        repo = RequestRepository(db_session)
        request = await repo.create(user)

        assert request is not None
        assert request.user_id == user.id
        assert request.status == RequestStatus.PENDING

    @pytest.mark.asyncio
    async def test_has_pending_true(self, db_session: AsyncSession):
        """Test has_pending returns True for pending request."""
        # Create user and request
        user = User(
            telegram_id=888999000,
            username="pendinguser",
            full_name="Pending User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        request = VPNRequest(user_id=user.id, status=RequestStatus.PENDING)
        db_session.add(request)
        await db_session.commit()

        # Check has_pending
        repo = RequestRepository(db_session)
        has_pending = await repo.has_pending(user)

        assert has_pending is True

    @pytest.mark.asyncio
    async def test_has_pending_false(self, db_session: AsyncSession):
        """Test has_pending returns False when no pending request."""
        # Create user without request
        user = User(
            telegram_id=111000999,
            username="nopending",
            full_name="No Pending",
        )
        db_session.add(user)
        await db_session.commit()

        # Check has_pending
        repo = RequestRepository(db_session)
        has_pending = await repo.has_pending(user)

        assert has_pending is False

    @pytest.mark.asyncio
    async def test_approve_request(self, db_session: AsyncSession):
        """Test approving request."""
        # Create user and request
        user = User(
            telegram_id=222333444,
            username="approveuser",
            full_name="Approve User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        request = VPNRequest(user_id=user.id, status=RequestStatus.PENDING)
        db_session.add(request)
        await db_session.commit()

        # Approve request
        repo = RequestRepository(db_session)
        await repo.approve(request)

        # Verify
        await db_session.refresh(request)
        assert request.status == RequestStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reject_request(self, db_session: AsyncSession):
        """Test rejecting request."""
        # Create user and request
        user = User(
            telegram_id=333444555,
            username="rejectuser",
            full_name="Reject User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        request = VPNRequest(user_id=user.id, status=RequestStatus.PENDING)
        db_session.add(request)
        await db_session.commit()

        # Reject request
        repo = RequestRepository(db_session)
        await repo.reject(request)

        # Verify
        await db_session.refresh(request)
        assert request.status == RequestStatus.REJECTED

    @pytest.mark.asyncio
    async def test_get_pending_requests(self, db_session: AsyncSession):
        """Test getting pending requests."""
        # Create users and requests
        for i in range(3):
            user = User(
                telegram_id=6000 + i,
                username=f"pending{i}",
                full_name=f"Pending {i}",
            )
            db_session.add(user)
            await db_session.commit()
            await db_session.refresh(user)

            request = VPNRequest(user_id=user.id, status=RequestStatus.PENDING)
            db_session.add(request)
            await db_session.commit()

        # Get pending requests
        repo = RequestRepository(db_session)
        pending = await repo.get_all_pending()

        assert len(pending) >= 3
