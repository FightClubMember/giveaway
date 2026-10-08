"""Rate-limiting / Throttling anti-flood middleware."""

import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, User as TgUser


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        """
        rate_limit: Minimum seconds between consecutive messages/callbacks from a single user.
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
        current_time = time.time()
        last_time = self.user_timestamps.get(user_id, 0.0)

        # Periodic cleanup of old keys if dictionary grows large
        if len(self.user_timestamps) > 10000:
            threshold = current_time - 60
            self.user_timestamps = {u: t for u, t in self.user_timestamps.items() if t > threshold}

        if current_time - last_time < self.rate_limit:
            # User is sending requests too quickly
            if isinstance(event, Update) and event.callback_query:
                await event.callback_query.answer("⚠️ Please wait a moment before tapping again.", show_alert=False)
            return  # Throttle request

        self.user_timestamps[user_id] = current_time
        return await handler(event, data)
