"""Middleware to handle user UI mode preferences."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import UIMode
from src.database.repositories.user_repo import UserRepository


class UIModeMiddleware(BaseMiddleware):
    """Middleware that injects ui_mode into handler data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Skip if no user in event (e.g. some system events)
        user: TgUser | None = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        session: AsyncSession = data.get("session")
        if not session:
            # If session middleware hasn't run yet, we can't do much
            # But usually DatabaseMiddleware runs first.
            return await handler(event, data)

        repo = UserRepository(session)
        db_user = await repo.get_by_telegram_id(user.id)

        if db_user:
            data["ui_mode"] = db_user.ui_mode
            data["db_user"] = db_user
        else:
            data["ui_mode"] = UIMode.NONE
            data["db_user"] = None

        return await handler(event, data)
