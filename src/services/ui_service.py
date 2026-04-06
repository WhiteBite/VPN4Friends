"""Service for managing user UI preferences and Telegram native interface."""

import logging

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    MenuButtonDefault,
    MenuButtonWebApp,
    WebAppInfo,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import settings
from src.database.models import UIMode, User
from src.database.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class UIService:
    """Service to handle UI mode switching and native Telegram integration."""

    def __init__(self, session: AsyncSession, bot: Bot) -> None:
        self.session = session
        self.bot = bot
        self.user_repo = UserRepository(session)

    async def set_user_ui_mode(self, user: User, mode: UIMode) -> None:
        """Update user UI mode and refresh Telegram native interface."""
        user.ui_mode = mode
        await self.user_repo.update(user)

        if mode == UIMode.MINIAPP:
            await self._activate_miniapp_ui(user)
        elif mode == UIMode.BOT:
            await self._activate_bot_ui(user)

    async def _activate_miniapp_ui(self, user: User) -> None:
        """Set native Web App button and clear native commands."""
        try:
            # 1. Set Menu Button to WebApp
            if settings.miniapp_url:
                await self.bot.set_chat_menu_button(
                    chat_id=user.telegram_id,
                    menu_button=MenuButtonWebApp(
                        text="🚀 Открыть",
                        web_app=WebAppInfo(url=settings.miniapp_url),
                    ),
                )

            # 2. Clear personal commands (so they don't pop up in App mode)
            await self.bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=user.telegram_id))

        except Exception as e:
            logger.error(f"Failed to activate Mini App UI for {user.telegram_id}: {e}")

    async def _activate_bot_ui(self, user: User) -> None:
        """Restore default menu button and set native command suggestions."""
        try:
            # 1. Restore Default Menu Button
            await self.bot.set_chat_menu_button(
                chat_id=user.telegram_id,
                menu_button=MenuButtonDefault(),
            )

            # 2. Set personal commands for Bot mode
            user_commands = [
                BotCommand(command="start", description="📋 Главное меню / Смена режима"),
                BotCommand(command="menu", description="📱 Кабинет (Чат-бот)"),
                BotCommand(command="profile", description="👤 Профиль и подписка"),
                BotCommand(command="support", description="✉️ Поддержка"),
                BotCommand(command="app", description="🚀 Перейти в Mini App"),
            ]

            if user.telegram_id in settings.admin_ids:
                commands = user_commands + [
                    BotCommand(command="admin", description="⚙️ Админ-панель"),
                    BotCommand(command="users", description="👥 Пользователи с VPN"),
                    BotCommand(command="broadcast", description="📢 Рассылка"),
                ]
            else:
                commands = user_commands

            await self.bot.set_my_commands(
                commands=commands,
                scope=BotCommandScopeChat(chat_id=user.telegram_id),
            )

        except Exception as e:
            logger.error(f"Failed to activate Bot UI for {user.telegram_id}: {e}")
