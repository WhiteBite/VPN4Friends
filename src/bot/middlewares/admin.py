"""Admin filter for aiogram."""

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message


class AdminFilter(Filter):
    """Filter that checks if user is admin."""

    def __init__(self, admin_ids: list[int]) -> None:
        self.admin_ids = admin_ids

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id if event.from_user else None
        return user_id in self.admin_ids
