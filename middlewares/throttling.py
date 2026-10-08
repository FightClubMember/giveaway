"""High-performance rate-limiting middleware with admin exemption and zero-lag thresholds."""

import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, User as TgUser

from config import settings


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.1):
        """
        rate_limit: Minimum seconds between consecutive taps. Set to ultra-responsive 0.1s.
        """
        super().__init__()
        self.rate_limit = rate_limit
        self.user_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if not tg_user:
            return await handler(event, data)

        user_id = tg_user.id

        # Never throttle administrators
        from handlers.admin import RUNTIME_ADMINS
        if settings.is_admin(user_id) or user_id in RUNTIME_ADMINS:
            return await handler(event, data)

        current_time = time.time()
        last_time = self.user_timestamps.get(user_id, 0.0)

        # Periodic cleanup of old timestamps
        if len(self.user_timestamps) > 10000:
            threshold = current_time - 60
            self.user_timestamps = {u: t for u, t in self.user_timestamps.items() if t > threshold}

        if current_time - last_time < self.rate_limit:
            # User is spamming buttons faster than 100ms
            if isinstance(event, Update) and event.callback_query:
                try:
                    await event.callback_query.answer()
                except Exception:
                    pass
            return

        self.user_timestamps[user_id] = current_time
        return await handler(event, data)
