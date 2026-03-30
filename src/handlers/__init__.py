from src.handlers.admin import router as admin_router
from src.handlers.messaging import (
    admin_router as admin_messaging_router,
)
from src.handlers.messaging import (
    user_router as user_messaging_router,
)
from src.handlers.user import router as user_router
from src.handlers.web_access import router as web_access_router

__all__ = [
    "user_router",
    "admin_router",
    "user_messaging_router",
    "admin_messaging_router",
    "web_access_router",
]
