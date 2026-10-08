"""High-performance ban enforcement middleware with in-memory caching."""

import time
from typing import Any, Awaitable, Callable, Dict, Set
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, User as TgUser

from database.database import get_session
from database.repositories import UserRepository


class BanMiddleware(BaseMiddleware):
    # In-memory cache of banned IDs to eliminate remote database roundtrip lag (0ms overhead)
    banned_cache: Set[int] = set()
    last_refresh: float = 0.0

    @classmethod
    async def refresh_cache_if_needed(cls, force: bool = False) -> None:
        now = time.time()
        # Refresh cache at most once every 60 seconds
        if force or (now - cls.last_refresh > 60.0):
            try:
                async with get_session() as session:
                    repo = UserRepository(session)
                    banned_users = await repo.get_banned_users(limit=1000)
                    cls.banned_cache = {u.id for u in banned_users}
                    cls.last_refresh = now
            except Exception:
                pass

    @classmethod
    def mark_banned(cls, user_id: int) -> None:
        cls.banned_cache.add(user_id)

    @classmethod
    def mark_unbanned(cls, user_id: int) -> None:
        cls.banned_cache.discard(user_id)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if not tg_user:
            return await handler(event, data)

        # Check in-memory cache first (0ms)
        if tg_user.id in self.banned_cache:
            if isinstance(event, Update) and event.callback_query:
                await event.callback_query.answer("⛔ Your account has been suspended.", show_alert=True)
            elif isinstance(event, Update) and event.message:
                await event.message.reply("⛔ <b>Account Suspended</b>\nContact support if you believe this is an error.", parse_mode="HTML")
            return

        return await handler(event, data)
