"""Global error handler for the bot."""

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

from src.services.xui_api import XUIApiError

logger = logging.getLogger(__name__)
router = Router(name="errors")


@router.error()
async def global_error_handler(event: ErrorEvent) -> bool:
    """Handle all unhandled exceptions."""
    exception = event.exception
    update = event.update

    # Log the error
    if isinstance(exception, XUIApiError):
        logger.error(f"3X-UI API error: {exception}")
        error_message = "❌ Ошибка подключения к VPN-серверу. Попробуй позже."
    else:
        logger.exception(f"Unhandled exception: {exception}", exc_info=exception)
        error_message = "❌ Произошла ошибка. Попробуй позже."

    # Try to notify user
    try:
        if update.message:
            await update.message.answer(error_message)
        elif update.callback_query:
            await update.callback_query.answer(error_message, show_alert=True)
    except Exception as e:
        logger.warning(f"Failed to send error message to user: {e}")

    return True  # Error handled
