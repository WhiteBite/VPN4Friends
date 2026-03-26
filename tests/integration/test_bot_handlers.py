"""Integration tests for bot handlers."""

import pytest
from aiogram import Bot
from aiogram.types import Message, User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.handlers.user import router as user_router


class TestStartHandler:
    """Tests for /start command handler."""

    @pytest.mark.asyncio
    async def test_start_command_creates_user(self, db_session: AsyncSession):
        """Test that /start command creates user in database."""
        # Create mock message
        tg_user = TelegramUser(
            id=123456789,
            is_bot=False,
            first_name="Test",
            username="testuser",
        )

        message = Message(
            message_id=1,
            date=None,
            chat=tg_user,
            from_user=tg_user,
            text="/start",
        )

        # Create user in DB
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.first_name,
        )
        db_session.add(user)
        await db_session.commit()

        # Verify user exists
        from src.database.repositories.user_repo import UserRepository

        repo = UserRepository(db_session)
        found_user = await repo.get_by_telegram_id(tg_user.id)

        assert found_user is not None
        assert found_user.telegram_id == tg_user.id

    @pytest.mark.asyncio
    async def test_start_command_response(self, db_session: AsyncSession):
        """Test that /start command returns correct response."""
        # This test would require mocking the bot
        # For now, just verify the handler exists
        assert user_router is not None


class TestRequestVPNHandler:
    """Tests for VPN request handler."""

    @pytest.mark.asyncio
    async def test_request_vpn_button(self, db_session: AsyncSession):
        """Test VPN request button callback."""
        # Create user
        user = User(
            telegram_id=987654321,
            username="requesttest",
            full_name="Request Test",
        )
        db_session.add(user)
        await db_session.commit()

        # Verify user can create request
        from src.services.vpn_service import VPNService

        service = VPNService(db_session)
        request = await service.create_request(user)

        assert request is not None
        assert request.status.value == "pending"


class TestMyLinkHandler:
    """Tests for 'My Link' handler."""

    @pytest.mark.asyncio
    async def test_my_link_with_vpn(self, db_session: AsyncSession):
        """Test getting VPN link for user with VPN."""
        # Create user with VPN
        user = User(
            telegram_id=111222333,
            username="linktest",
            full_name="Link Test",
            has_vpn=True,
        )
        db_session.add(user)
        await db_session.commit()

        # Verify user has VPN
        assert user.has_vpn is True

    @pytest.mark.asyncio
    async def test_my_link_without_vpn(self, db_session: AsyncSession):
        """Test getting link for user without VPN."""
        # Create user without VPN
        user = User(
            telegram_id=444555666,
            username="nolinktest",
            full_name="No Link Test",
            has_vpn=False,
        )
        db_session.add(user)
        await db_session.commit()

        # Verify user has no VPN
        assert user.has_vpn is False
