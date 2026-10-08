"""High-throughput, rate-limited broadcast engine."""

import asyncio
import logging
from typing import List, Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.repositories import UserRepository, BroadcastRepository

logger = logging.getLogger(__name__)


class BroadcastResult:
    def __init__(self, total: int, sent: int, failed: int, blocked: int):
        self.total = total
        self.sent = sent
        self.failed = failed
        self.blocked = blocked


class BroadcastService:
    @classmethod
    async def send_broadcast(
        cls,
        bot: Bot,
        session: AsyncSession,
        admin_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        photo_id: Optional[str] = None,
    ) -> BroadcastResult:
        """Broadcast message to all active users respecting Telegram rate limits.
        
        Uses adaptive delay to avoid 429 Too Many Requests errors.
        """
        user_repo = UserRepository(session)
        broadcast_repo = BroadcastRepository(session)

        user_ids = await user_repo.get_all_active_user_ids()
        total_targets = len(user_ids)

        broadcast_record = await broadcast_repo.create(
            admin_id=admin_id,
            message_text=text,
            total_targets=total_targets,
        )

        sent = 0
        failed = 0
        blocked = 0

        logger.info("Starting broadcast #%d to %d users", broadcast_record.id, total_targets)

        for uid in user_ids:
            try:
                if photo_id:
                    await bot.send_photo(
                        chat_id=uid,
                        photo=photo_id,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                    )
                else:
                    await bot.send_message(
                        chat_id=uid,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                    )
                sent += 1
            except TelegramRetryAfter as e:
                logger.warning("Flood control hit, waiting %d seconds...", e.retry_after)
                await asyncio.sleep(e.retry_after)
                # Retry once
                try:
                    await bot.send_message(chat_id=uid, text=text, parse_mode="HTML", reply_markup=reply_markup)
                    sent += 1
                except Exception:
                    failed += 1
            except TelegramForbiddenError:
                blocked += 1
                failed += 1
            except TelegramAPIError as e:
                logger.debug("Failed sending broadcast to user %d: %s", uid, e)
                failed += 1
            except Exception as e:
                logger.debug("Unexpected broadcast error for user %d: %s", uid, e)
                failed += 1

            # Sleep between requests to obey ~25 msgs/sec
            await asyncio.sleep(settings.RATE_LIMIT_DELAY)

        await broadcast_repo.finish(broadcast_record.id, sent_count=sent, failed_count=failed)
        logger.info("Completed broadcast #%d: sent=%d, blocked=%d, failed=%d", broadcast_record.id, sent, blocked, failed)

        return BroadcastResult(total=total_targets, sent=sent, failed=failed, blocked=blocked)
