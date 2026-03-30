import hmac
import json
import time
from hashlib import sha256
from typing import Annotated
from urllib.parse import parse_qsl

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.database.models import User
from src.database.repositories import UserRepository
from src.database.session import get_session

JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7


def create_access_token(telegram_id: int) -> str:
    """Create a long-lived JWT token for the user."""
    expire = time.time() + (TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    to_encode = {
        "sub": str(telegram_id),
        "exp": int(expire),
        "iat": int(time.time()),
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def _validate_telegram_data(init_data: str) -> dict:
    """Validate initData from Telegram Mini App."""
    try:
        parsed_data = dict(parse_qsl(init_data))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid initData format",
        ) from e

    if "hash" not in parsed_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'hash' not found in initData",
        )

    hash_str = parsed_data.pop("hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))

    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), sha256)

    if h.hexdigest() != hash_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid hash",
        )

    return parsed_data


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    x_telegram_init_data: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """
    Get current user from either Telegram initData or JWT Bearer token.
    Allows authentication from both Telegram Mini App and external browsers.
    """
    telegram_id: int | None = None
    user_data_from_tg: dict | None = None

    # 1. Try JWT Bearer Token (prioritize for external browsers)
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ")[1]
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
            telegram_id = int(payload.get("sub"))
        except (jwt.PyJWTError, ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token",
            ) from e

    # 2. Try Telegram Init Data (for Mini App)
    if not telegram_id and x_telegram_init_data:
        validated_data = _validate_telegram_data(x_telegram_init_data)
        user_data_from_tg = json.loads(validated_data.get("user", "{}"))
        telegram_id = user_data_from_tg.get("id") if user_data_from_tg else None

    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)

    if not user:
        if not user_data_from_tg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Auto-create user from Telegram data if they don't exist yet
        first_name = user_data_from_tg.get("first_name", "")
        last_name = user_data_from_tg.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip() or "Unknown"

        user, _ = await user_repo.get_or_create(
            telegram_id=telegram_id,
            full_name=full_name,
            username=user_data_from_tg.get("username"),
            is_admin=telegram_id in settings.admin_ids,
        )

    return user
