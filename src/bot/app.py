"""Main application entry point."""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    MenuButtonWebApp,
    WebAppInfo,
)

from src.bot.config import settings
from src.bot.error_handler import router as error_router
from src.bot.middlewares import DatabaseMiddleware
from src.database import init_db
from src.handlers import (
    admin_messaging_router,
    admin_router,
    user_messaging_router,
    user_router,
    web_access_router,
)
from src.handlers.server_selection import router as server_selection_router
from src.services.xui_api import check_xui_connection


def setup_logging() -> None:
    """Configure logging to console and file."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_dir / "bot.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


setup_logging()
logger = logging.getLogger(__name__)


async def setup_bot_commands(bot: Bot) -> None:
    """Register bot commands in Telegram menu."""
    # Commands for all users
    user_commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="menu", description="📋 Главное меню"),
        BotCommand(command="link", description="🔗 Получить ссылку VPN"),
        BotCommand(command="stats", description="📊 Моя статистика"),
        BotCommand(command="support", description="✉️ Написать админу"),
        BotCommand(command="help", description="❓ Справка"),
    ]

    # Additional commands for admins
    admin_commands = user_commands + [
        BotCommand(command="admin", description="⚙️ Админ-панель"),
        BotCommand(command="users", description="👥 Пользователи с VPN"),
        BotCommand(command="broadcast", description="📢 Рассылка"),
        BotCommand(command="notify_update", description="🔔 Уведомить о смене конфига"),
    ]

    # Set commands for all private chats
    await bot.set_my_commands(user_commands, scope=BotCommandScopeAllPrivateChats())

    # Set extended commands for admins
    for admin_id in settings.admin_ids:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.warning(f"Failed to set admin commands for {admin_id}: {e}")


async def notify_admins_startup(bot: Bot) -> None:
    """Notify admins that bot has started."""
    start_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"🟢 Бот запущен!\n\n🕐 Время: {start_time}",
            )
            logger.info(f"Startup notification sent to admin {admin_id}")
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id} about startup: {e}")


async def notify_admins_shutdown(bot: Bot) -> None:
    """Notify admins that bot is shutting down."""
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, "🔴 Бот остановлен.")
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id} about shutdown: {e}")


async def main() -> None:
    """Initialize and start the bot."""
    logger.info("Starting VPN bot...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    from src.database import session_factory

    # Check 3X-UI connection
    logger.info("Checking 3X-UI panel connection...")
    xui_ok, xui_message = await check_xui_connection()
    if xui_ok:
        logger.info(f"✅ {xui_message}")

        # --- Provision nodes in background ---
        async def run_provisioning():
            try:
                from src.database.repositories import UserRepository
                from src.services.xui_provisioner import (
                    sync_node_clients,
                    sync_node_inbounds,
                    sync_node_routing,
                )

                logger.info("Starting auto-provisioning for 3X-UI nodes in background...")

                # Phase 1: Sync outbounds and routing rules per node
                nodes_config = settings.nodes_config
                for node_name, node_cfg in nodes_config.items():
                    try:
                        await sync_node_routing(node_name, node_cfg)
                    except Exception as e:
                        logger.error(f"Failed to sync routing for node {node_name}: {e}")

                # Phase 2: Sync inbounds and clients per endpoint
                async with session_factory() as session:
                    user_repo = UserRepository(session)
                    users_with_vpn = await user_repo.get_all_with_vpn()

                    for endpoint in settings.endpoints:
                        # Skip endpoints without a proper panel API
                        if endpoint.panel_type != "3xui":
                            continue
                        if not endpoint.panel_config or "api_url" not in endpoint.panel_config:
                            continue

                        try:
                            success = await sync_node_inbounds(endpoint)
                            if success:
                                await sync_node_clients(endpoint, users_with_vpn)
                        except Exception as e:
                            logger.error(f"Failed to sync node {endpoint.name}: {e}")

                logger.info("Auto-provisioning complete")
            except Exception as pe:
                logger.error(f"Failed during auto-provisioning: {pe}")

        asyncio.create_task(run_provisioning())

    else:
        logger.warning(f"⚠️ {xui_message}")
        logger.warning("Bot will start, but VPN operations may fail!")

    # Create bot and dispatcher
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    # Register middleware
    dp.update.middleware(DatabaseMiddleware(session_factory))

    # Register error handler first
    dp.include_router(error_router)

    # Register routers
    dp.include_router(user_router)
    dp.include_router(user_messaging_router)
    dp.include_router(server_selection_router)  # Server selection router
    dp.include_router(admin_router)
    dp.include_router(admin_messaging_router)
    dp.include_router(web_access_router)
    logger.info("Handlers registered")

    # Set bot commands
    await setup_bot_commands(bot)
    logger.info("Bot commands registered")

    # Set Mini App menu button
    if settings.miniapp_url:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🚀 VPN Кабинет", web_app=WebAppInfo(url=settings.miniapp_url)
            )
        )
        logger.info(f"Mini App menu button set to: {settings.miniapp_url}")
    else:
        # Set default menu button if no miniapp
        await bot.set_chat_menu_button()
        logger.info("Menu button reset to default")

    # Notify admins about startup
    await notify_admins_startup(bot)

    # Setup graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        shutdown_event.set()

    # Register signal handlers (Unix-style, works on Windows too)
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
    except NotImplementedError:
        # Windows doesn't support add_signal_handler
        pass

    # Start polling
    logger.info("Bot is running...")
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down...")
        await notify_admins_shutdown(bot)
        await bot.session.close()
        logger.info("Bot stopped gracefully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
