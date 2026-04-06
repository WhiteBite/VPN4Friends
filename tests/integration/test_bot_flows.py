from unittest.mock import AsyncMock, patch

import pytest
from aiogram import Bot
from aiogram.types import CallbackQuery, Chat, Message, User
from sqlalchemy import select

from src.database.models import UIMode, VPNRequest
from src.database.models import User as DBUser
from src.handlers.user import cmd_start, request_vpn, set_ui_mode


@pytest.mark.asyncio
async def test_cmd_start_direct(db_session):
    """Test cmd_start handler directly."""
    tg_user = User(id=9991, is_bot=False, first_name="Direct", last_name="User")
    chat = Chat(id=9991, type="private")
    message = AsyncMock(spec=Message)
    message.from_user = tg_user
    message.chat = chat
    message.answer = AsyncMock()

    bot = AsyncMock(spec=Bot)

    await cmd_start(message, db_session, bot)

    # Verify DB
    stmt = select(DBUser).where(DBUser.telegram_id == 9991)
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None

    # Verify feedback
    message.answer.assert_called()
    assert "Привет" in message.answer.call_args.args[0]


@pytest.mark.asyncio
async def test_set_ui_mode_bot_direct(db_session):
    """Test set_ui_mode callback handler directly for bot mode."""
    user = DBUser(telegram_id=8881, full_name="Switch User", ui_mode=UIMode.NONE)
    db_session.add(user)
    await db_session.commit()

    tg_user = User(id=8881, is_bot=False, first_name="Switch")
    callback_query = AsyncMock(spec=CallbackQuery)
    callback_query.from_user = tg_user
    callback_query.data = "set_ui_mode:bot"
    callback_query.message = AsyncMock(spec=Message)
    callback_query.answer = AsyncMock()
    callback_query.message.answer = AsyncMock()
    callback_query.message.edit_text = AsyncMock()

    bot = AsyncMock(spec=Bot)

    await set_ui_mode(callback_query, db_session, bot)

    # Verify DB
    await db_session.refresh(user)
    assert user.ui_mode == UIMode.BOT

    # Verify feedback
    callback_query.message.edit_text.assert_called()
    assert "Режим чат-бота активирован" in callback_query.message.edit_text.call_args.args[0]
    callback_query.message.answer.assert_called()
    assert "Главное меню" in callback_query.message.answer.call_args.args[0]


@pytest.mark.asyncio
async def test_request_vpn_direct(db_session):
    """Test request_vpn callback handler directly."""
    user = DBUser(telegram_id=7771, full_name="Requester", ui_mode=UIMode.BOT)
    db_session.add(user)
    await db_session.commit()

    tg_user = User(id=7771, is_bot=False, first_name="Requester")
    callback_query = AsyncMock(spec=CallbackQuery)
    callback_query.from_user = tg_user
    callback_query.answer = AsyncMock()
    callback_query.message = AsyncMock(spec=Message)
    callback_query.message.edit_text = AsyncMock()

    bot = AsyncMock(spec=Bot)

    with patch("src.handlers.user.VPNService") as MockVPNService:
        mock_service = MockVPNService.return_value
        mock_service.create_request = AsyncMock(return_value=VPNRequest(id=555))

        await request_vpn(callback_query, db_session, bot)

        mock_service.create_request.assert_called()
        callback_query.message.edit_text.assert_called()
        assert "Заявка отправлена" in callback_query.message.edit_text.call_args.args[0]
