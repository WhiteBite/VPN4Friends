"""Dependencies for the FastAPI application."""

import hmac
import json
from hashlib import sha256
from typing import Annotated
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.database.models import User
from src.database.repositories import UserRepository
from src.database.session import get_session


def _validate_telegram_data(init_data: str) -> dict:
    """Validate initData from Telegram Mini App."""
    try:
        parsed_data = dict(parse_qsl(init_data))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid initData format",
        )

    if "hash" not in parsed_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'hash' not found in initData",
        )

    hash_str = parsed_data.pop("hash")
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed_data.items())
    )

    secret_key = hmac.new(
        "WebAppData".encode(), settings.bot_token.encode(), sha256
    ).digest()
    h = hmac.new(secret_key, data_check_string.encode(), sha256)

    if h.hexdigest() != hash_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid hash",
        )

    return parsed_data


async def get_current_user(
    x_telegram_init_data: Annotated[str, Header()],
    session: AsyncSession = Depends(get_session),
) -> User:
    """Get current user from Telegram initData."""
    validated_data = _validate_telegram_data(x_telegram_init_data)
    user_data = json.loads(validated_data.get("user", "{}"))

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User data not found in initData",
        )

    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in initData",
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)

    if not user:
        # In a real scenario, we might create the user here
        # For now, we assume the user must have interacted with the bot first
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please start the bot first.",
        )

    return user
