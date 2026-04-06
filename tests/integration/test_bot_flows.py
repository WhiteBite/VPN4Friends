from datetime import datetime

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TGUser
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import RequestStatus, UIMode
from src.database.repositories.request_repo import RequestRepository
from src.database.repositories.user_repo import UserRepository


@pytest.mark.asyncio
async def test_full_new_user_flow(dispatcher: Dispatcher, mock_bot: Bot, db_session: AsyncSession):
    # 1. Simulate /start command
    tg_user = TGUser(id=123, is_bot=False, first_name="Test", username="testuser")
    chat = Chat(id=123, type="private")
    message = Message(
        message_id=1, date=datetime.now(), chat=chat, from_user=tg_user, text="/start", bot=mock_bot
    )

    # Send update to dispatcher
    update = Update(update_id=1, message=message)
    await dispatcher.feed_update(mock_bot, update)

    # Verify:
    # - User created in DB
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_telegram_id(123)
    assert user is not None

    # - UI Selection keyboard sent
    # Capture all possible ways aiogram might call the bot
    all_calls = []
    for call in mock_bot.mock_calls:
        # call is (name, args, kwargs)
        # If it's a direct call, name is ''
        name, args, kwargs = call
        if name == "" or name == "send_message":
            # For direct calls, the first arg is the request object (SendMessage, etc.)
            if name == "" and len(args) > 0:
                req = args[0]
                if hasattr(req, "text"):
                    text = req.text
                else:
                    # Might be a different object
                    continue
            else:
                text = kwargs.get("text", "") or (args[1] if len(args) > 1 else "")

            if "выберите, как вам удобнее" in text.lower():
                all_calls.append(call)

    assert all_calls, f"Expected UI selection message not found. Mock calls: {mock_bot.mock_calls}"


@pytest.mark.asyncio
async def test_ui_mode_selection_bot(
    dispatcher: Dispatcher, mock_bot: Bot, db_session: AsyncSession
):
    # Setup: User already exists
    user_repo = UserRepository(db_session)
    user, _ = await user_repo.get_or_create(123, "testuser", "Test")
    user.ui_mode = UIMode.NONE
    await db_session.commit()
    await db_session.refresh(user)

    # 2. Simulate clicking "Чат-бот" button
    tg_user = TGUser(id=123, is_bot=False, first_name="Test", username="testuser")
    callback = CallbackQuery(
        id="12345",
        from_user=tg_user,
        chat_instance="inst123",
        data="set_ui_mode:bot",
        message=Message(
            message_id=2, date=datetime.now(), chat=Chat(id=123, type="private"), bot=mock_bot
        ),
        bot=mock_bot,
    )

    update = Update(update_id=2, callback_query=callback)
    await dispatcher.feed_update(mock_bot, update)

    # Verify:
    # - UI mode updated in DB
    await db_session.refresh(user)
    assert user.ui_mode == UIMode.BOT

    # Check for confirmation (edit_text) or command set
    method_names = [call[0] for call in mock_bot.mock_calls]
    assert "set_my_commands" in method_names or any(c[0] == "" for c in mock_bot.mock_calls)


@pytest.mark.asyncio
async def test_request_vpn_flow(dispatcher: Dispatcher, mock_bot: Bot, db_session: AsyncSession):
    # Setup: User in BOT mode
    user_repo = UserRepository(db_session)
    user, _ = await user_repo.get_or_create(123, "testuser", "Test")
    user.ui_mode = UIMode.BOT

    # Instead of setting read-only has_vpn, ensure they have no active profiles
    for p in user.profiles:
        p.is_active = False
    await db_session.commit()
    await db_session.refresh(user)
    assert not user.has_vpn

    # 3. Simulate clicking "Попросить VPN"
    tg_user = TGUser(id=123, is_bot=False, first_name="Test", username="testuser")
    callback = CallbackQuery(
        id="12346",
        from_user=tg_user,
        chat_instance="inst124",
        data="request_vpn",
        message=Message(
            message_id=3, date=datetime.now(), chat=Chat(id=123, type="private"), bot=mock_bot
        ),
        bot=mock_bot,
    )

    update = Update(update_id=3, callback_query=callback)
    await dispatcher.feed_update(mock_bot, update)

    # Verify:
    # - Request created
    req_repo = RequestRepository(db_session)
    req = await req_repo.get_pending_for_user(user)

    assert req is not None, "VPN Request was not created in DB"
    assert req.status == RequestStatus.PENDING

    # - Check notification to admin (id 123456789 from test settings)
    admin_notified = False
    for name, args, kwargs in mock_bot.mock_calls:
        chat_id = None
        if name == "send_message":
            chat_id = kwargs.get("chat_id") or (args[0] if args else None)
        elif name == "" and len(args) > 0 and hasattr(args[0], "chat_id"):
            # Direct call with an object like SendMessage
            chat_id = args[0].chat_id

        if str(chat_id) == "123456789" or chat_id == 123456789:
            admin_notified = True
            break

    assert admin_notified, f"Admins (123456789) not notified. Calls: {mock_bot.mock_calls}"
