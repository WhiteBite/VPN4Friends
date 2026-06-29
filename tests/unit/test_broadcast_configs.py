"""Unit tests for broadcast config handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Message, User

from src.database.models import User as DBUser
from src.database.models import VpnProfile
from src.handlers.messaging import broadcast_user_configs


@pytest.mark.asyncio
async def test_broadcast_user_configs_success(db_session, test_settings):
    """Test broadcast sends personalized configs to VPN users."""
    # Arrange: create a user with active VPN profile
    user = DBUser(
        telegram_id=7777,
        full_name="Test User",
        username="tester",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = VpnProfile(
        user_id=user.id,
        protocol_name="vless",
        profile_data={"client_id": "test-uuid"},
        is_active=True,
    )
    db_session.add(profile)
    await db_session.commit()

    # Mock callback
    tg_user = User(id=123456789, is_bot=False, first_name="Admin")
    callback = AsyncMock(spec=CallbackQuery)
    callback.from_user = tg_user
    callback.data = "broadcast_configs"
    callback.answer = AsyncMock()
    callback.message = AsyncMock(spec=Message)
    callback.message.edit_text = AsyncMock()

    # Mock bot
    bot = AsyncMock()
    bot.send_message = AsyncMock()

    # Mock VPNService to return test links
    mock_links = [
        ("Germany TCP", "vless://test-uuid@ger1.whitebite.ru:8443?type=tcp"),
    ]

    with patch("src.services.vpn_service.VPNService") as MockVPNService:
        mock_service = MagicMock()
        mock_service.get_all_active_vpn_links = AsyncMock(return_value=mock_links)
        MockVPNService.return_value = mock_service

        # Act
        await broadcast_user_configs(callback, db_session, bot)

    # Assert
    callback.answer.assert_awaited_once()
    callback.message.edit_text.assert_awaited()
    # Should show progress then success
    calls = callback.message.edit_text.await_args_list
    assert any("Отправляю конфиги" in str(call) for call in calls)
    assert any("Рассылка конфигов завершена" in str(call) for call in calls)

    # Bot should send two messages: VLESS configs + native MTProto proxy card
    assert bot.send_message.await_count == 2
    first_call, second_call = bot.send_message.await_args_list

    # First message: VLESS configs (HTML)
    assert first_call.kwargs["parse_mode"] == "HTML"
    assert first_call.args[0] == 7777  # telegram_id
    sent_text = first_call.args[1]  # text is positional arg
    assert "Test, твои подключения" in sent_text
    assert "vless://test-uuid" in sent_text

    # Second message: native MTProto proxy card (no parse_mode so Telegram renders it)
    assert second_call.args[0] == 7777
    mtproto_text = second_call.args[1]
    assert "t.me/proxy" in mtproto_text
    assert second_call.kwargs.get("parse_mode") is None


@pytest.mark.asyncio
async def test_broadcast_user_configs_no_users(db_session, test_settings):
    """Test broadcast shows error when no VPN users exist."""
    callback = AsyncMock(spec=CallbackQuery)
    callback.answer = AsyncMock()
    callback.message = AsyncMock(spec=Message)
    callback.message.edit_text = AsyncMock()

    bot = AsyncMock()

    # Act: no users in DB
    await broadcast_user_configs(callback, db_session, bot)

    # Assert
    callback.message.edit_text.assert_awaited_once()
    call_args = callback.message.edit_text.await_args
    assert "Нет пользователей с VPN" in call_args.args[0]
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_broadcast_user_configs_failed_send(db_session, test_settings):
    """Test broadcast handles failed sends gracefully."""
    user = DBUser(
        telegram_id=8888,
        full_name="Fail User",
        username="failer",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = VpnProfile(
        user_id=user.id,
        protocol_name="vless",
        profile_data={},
        is_active=True,
    )
    db_session.add(profile)
    await db_session.commit()

    callback = AsyncMock(spec=CallbackQuery)
    callback.answer = AsyncMock()
    callback.message = AsyncMock(spec=Message)
    callback.message.edit_text = AsyncMock()

    bot = AsyncMock()
    bot.send_message = AsyncMock(side_effect=Exception("User blocked bot"))

    with patch("src.services.vpn_service.VPNService") as MockVPNService:
        mock_service = MagicMock()
        mock_service.get_all_active_vpn_links = AsyncMock(return_value=[])
        MockVPNService.return_value = mock_service

        await broadcast_user_configs(callback, db_session, bot)

    # Should show 0 sent, 1 failed
    calls = callback.message.edit_text.await_args_list
    final_call = calls[-1]
    assert "Отправлено: 0" in final_call.args[0]
    assert "Не доставлено: 1" in final_call.args[0]
