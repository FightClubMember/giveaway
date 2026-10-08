"""Automated background scheduler for expiring giveaways and winner draws."""

import asyncio
import logging
from aiogram import Bot

from config import settings
from database.database import get_session
from database.repositories import GiveawayRepository
from services.winner_service import WinnerService
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


async def run_giveaway_scheduler(bot: Bot, interval_seconds: int = 30) -> None:
    """Continuously check for giveaways that reached their end_time and auto-draw winners."""
    logger.info("Giveaway automated scheduler started (Interval: %ds)", interval_seconds)
    while True:
        try:
            async with get_session() as session:
                giveaway_repo = GiveawayRepository(session)
                due_giveaways = await giveaway_repo.get_due_active_giveaways()

                for gw in due_giveaways:
                    logger.info("Giveaway #%d '%s' has expired! Selecting winners...", gw.id, gw.title)
                    result = await WinnerService.select_winners(session, gw.id)

                    logger.info("Successfully drawn %d winners for giveaway #%d", len(result.winners), gw.id)

                    # Notify winners
                    for winner in result.winners:
                        await NotificationService.notify_winner(
                            bot=bot,
                            user_id=winner.user_id,
                            giveaway_id=gw.id,
                            giveaway_title=gw.title,
                            prize=gw.prize,
                            claim_hours=settings.CLAIM_WINDOW_HOURS,
                        )

        except asyncio.CancelledError:
            logger.info("Giveaway scheduler task cancelled.")
            break
        except Exception as e:
            logger.exception("Error in giveaway scheduler loop: %s", e)

        await asyncio.sleep(interval_seconds)
