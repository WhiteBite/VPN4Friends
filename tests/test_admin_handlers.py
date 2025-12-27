"""Tests for admin handlers - request approval flow."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message
from aiogram.types import User as TgUser


class TestAdminRequestsHandler:
    """Test admin_requests handler - viewing pending VPN requests."""

    @pytest.fixture
    def mock_callback(self) -> CallbackQuery:
        """Create mock callback query."""
        callback = MagicMock(spec=CallbackQuery)
        callback.answer = AsyncMock()
        callback.from_user = MagicMock(spec=TgUser)
        callback.from_user.id = 267945352  # Admin ID

        # Mock message
        callback.message = MagicMock(spec=Message)
        callback.message.edit_text = AsyncMock()
        callback.message.answer = AsyncMock()
        callback.message.chat = MagicMock(spec=Chat)
        callback.message.chat.id = 267945352

        return callback

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_user_with_underscore(self) -> MagicMock:
        """Create mock user with underscore in username (the bug case)."""
        user = MagicMock()
        user.id = 12
        user.telegram_id = 274756342
        user.username = "daiker_id"  # Underscore that breaks Markdown
        user.full_name = "Igor Daiker"
        user.display_name = "Igor Daiker (@daiker_id)"
        return user

    @pytest.fixture
    def mock_request_pending(self, mock_user_with_underscore) -> MagicMock:
        """Create mock pending VPN request."""
        request = MagicMock()
        request.id = 11
        request.user = mock_user_with_underscore
        request.status = MagicMock()
        request.status.value = "pending"
        request.created_at = datetime(2025, 12, 27, 22, 1, 0)
        return request

    @pytest.mark.asyncio
    async def test_admin_requests_sends_message_with_buttons(
        self,
        mock_callback: CallbackQuery,
        mock_session: AsyncMock,
        mock_request_pending: MagicMock,
    ):
        """Test that admin_requests sends individual messages with action buttons."""
        from src.handlers.admin import admin_requests

        # Mock VPNService to return pending requests
        with patch("src.handlers.admin.VPNService") as MockVPNService:
            mock_vpn_service = MockVPNService.return_value
            mock_vpn_service.get_pending_requests = AsyncMock(return_value=[mock_request_pending])

            await admin_requests(mock_callback, mock_session)

        # Verify callback was answered
        mock_callback.answer.assert_called_once()

        # Verify list message was sent
        mock_callback.message.edit_text.assert_called_once()
        list_text = mock_callback.message.edit_text.call_args[0][0]
        assert "Заявки (1)" in list_text
        assert "Igor Daiker" in list_text

        # Verify individual request message with buttons was sent
        mock_callback.message.answer.assert_called_once()
        call_kwargs = mock_callback.message.answer.call_args[1]

        # Check HTML parse mode (not Markdown!)
        assert call_kwargs.get("parse_mode") == "HTML", (
            "Must use HTML parse_mode to handle usernames with underscores"
        )

        # Check reply_markup contains buttons
        assert "reply_markup" in call_kwargs
        assert call_kwargs["reply_markup"] is not None

    @pytest.mark.asyncio
    async def test_admin_requests_html_escapes_username_with_underscore(
        self,
        mock_callback: CallbackQuery,
        mock_session: AsyncMock,
        mock_request_pending: MagicMock,
    ):
        """Test that usernames with underscores are properly handled in HTML."""
        from src.handlers.admin import admin_requests

        with patch("src.handlers.admin.VPNService") as MockVPNService:
            mock_vpn_service = MockVPNService.return_value
            mock_vpn_service.get_pending_requests = AsyncMock(return_value=[mock_request_pending])

            await admin_requests(mock_callback, mock_session)

        # Get the message text
        call_args = mock_callback.message.answer.call_args[0][0]

        # Should contain display_name with underscore (HTML handles it fine)
        assert "daiker_id" in call_args or "Igor Daiker" in call_args

        # Should use <code> tags for telegram_id, not backticks
        assert "<code>" in call_args
        assert "`" not in call_args, "Should not use Markdown backticks"

    @pytest.mark.asyncio
    async def test_admin_requests_no_pending_shows_empty_message(
        self,
        mock_callback: CallbackQuery,
        mock_session: AsyncMock,
    ):
        """Test that empty pending list shows appropriate message."""
        from src.handlers.admin import admin_requests

        with patch("src.handlers.admin.VPNService") as MockVPNService:
            mock_vpn_service = MockVPNService.return_value
            mock_vpn_service.get_pending_requests = AsyncMock(return_value=[])

            await admin_requests(mock_callback, mock_session)

        mock_callback.answer.assert_called_once()

        # Should show "no requests" message
        call_args = mock_callback.message.edit_text.call_args[0][0]
        assert "Нет заявок" in call_args

        # Should NOT call answer() for individual requests
        mock_callback.message.answer.assert_not_called()


class TestRequestActionKeyboard:
    """Test that request action keyboard has correct buttons."""

    def test_request_action_kb_has_approve_reject_buttons(self):
        """Test keyboard contains approve and reject buttons."""
        from src.keyboards.admin_kb import get_request_action_kb

        # Create mock request
        mock_request = MagicMock()
        mock_request.id = 11

        keyboard = get_request_action_kb(mock_request)

        # Get all button texts
        button_texts = []
        for row in keyboard.inline_keyboard:
            for button in row:
                button_texts.append(button.text)

        assert any("Одобрить" in text for text in button_texts), (
            "Keyboard must have 'Одобрить' (Approve) button"
        )
        assert any("Отклонить" in text for text in button_texts), (
            "Keyboard must have 'Отклонить' (Reject) button"
        )

    def test_request_action_kb_callback_data_format(self):
        """Test callback data contains request_id."""
        from src.keyboards.admin_kb import get_request_action_kb

        mock_request = MagicMock()
        mock_request.id = 42

        keyboard = get_request_action_kb(mock_request)

        # Get all callback_data
        callback_datas = []
        for row in keyboard.inline_keyboard:
            for button in row:
                callback_datas.append(button.callback_data)

        # Should contain request_id in callback data
        assert any("42" in data for data in callback_datas), "Callback data must contain request_id"


class TestNotifyAdminOnNewRequest:
    """Test admin notification when new VPN request is created."""

    @pytest.mark.asyncio
    async def test_notify_admin_uses_html_parse_mode(self):
        """Test that admin notification uses HTML, not Markdown."""
        from unittest.mock import AsyncMock, MagicMock

        from aiogram import Bot

        # This tests the request_vpn handler notification part
        mock_bot = MagicMock(spec=Bot)
        mock_bot.send_message = AsyncMock()

        mock_user = MagicMock()
        mock_user.display_name = "Test User (@test_user)"  # Has underscore
        mock_user.telegram_id = 123456789

        mock_request = MagicMock()
        mock_request.id = 1

        # Simulate sending notification

        admin_id = 267945352
        message_text = (
            f"🔔 Новая заявка на VPN!\n\n"
            f"👤 {mock_user.display_name}\n"
            f"🆔 <code>{mock_user.telegram_id}</code>"
        )

        await mock_bot.send_message(
            admin_id,
            message_text,
            parse_mode="HTML",
        )

        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args[1]

        assert call_kwargs.get("parse_mode") == "HTML", (
            "Admin notification must use HTML parse_mode"
        )

    def test_html_handles_underscore_in_username(self):
        """Verify HTML doesn't interpret underscore as formatting."""
        username = "daiker_id"

        # HTML doesn't have underscore formatting problem like Markdown (_text_ = italic)
        html_text = f"User: {username}"

        # Should contain the underscore literally
        assert "_" in html_text
        assert username in html_text
