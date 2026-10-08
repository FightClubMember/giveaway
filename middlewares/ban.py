"""Middleware to enforce user ban status."""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, User as TgUser

from database.database import get_session
from database.repositories import UserRepository


class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if not tg_user:
            return await handler(event, data)

        async with get_session() as session:
            repo = UserRepository(session)
            user = await repo.get_by_id(tg_user.id)
            if user and user.is_banned:
                # If callback query, answer callback with notice
                if isinstance(event, Update) and event.callback_query:
                    await event.callback_query.answer(
                        "⛔ Your account has been suspended from this bot.",
                        show_alert=True,
                    )
                elif isinstance(event, Update) and event.message:
                    await event.message.reply(
                        "⛔ <b>Account Suspended</b>\n\n"
                        f"Reason: {user.ban_reason or 'Violation of community giveaway guidelines'}.\n"
                        "Contact support if you believe this is an error.",
                        parse_mode="HTML",
                    )
                return  # Drop processing

        return await handler(event, data)
