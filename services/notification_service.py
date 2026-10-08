"""User notifications and alert dispatching service."""

import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramAPIError

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    async def notify_winner(
        bot: Bot,
        user_id: int,
        giveaway_id: int,
        giveaway_title: str,
        prize: str,
        claim_hours: int = 24,
    ) -> bool:
        """Send private notification to a giveaway winner."""
        text = (
            "🎉 <b>CONGRATULATIONS! YOU WON!</b> 🎉\n\n"
            f"You have been selected as a winner in:\n"
            f"🎁 <b>{giveaway_title}</b>\n\n"
            f"💰 <b>Prize:</b> {prize}\n\n"
            f"⚠️ <b>Important:</b> You must claim your prize within <b>{claim_hours} hours</b>, "
            f"or the prize may be forfeited or redrawn.\n\n"
            "Click the button below to submit your claim details securely."
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎁 CLAIM PRIZE NOW",
                        callback_data=f"claim_{giveaway_id}",
                    )
                ]
            ]
        )
        try:
            await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML", reply_markup=keyboard)
            return True
        except TelegramForbiddenError:
            logger.warning("Failed to notify winner %d: Bot was blocked by user.", user_id)
            return False
        except TelegramAPIError as e:
            logger.error("Telegram error notifying winner %d: %s", user_id, e)
            return False

    @staticmethod
    async def notify_referrer_reward(
        bot: Bot,
        referrer_id: int,
        giveaway_title: str,
        bonus_entries: int,
    ) -> bool:
        """Send private notification to referrer that a referral was validated."""
        text = (
            "👥 <b>Referral Validated!</b>\n\n"
            "A friend you invited just completed the requirements for:\n"
            f"🎁 <b>{giveaway_title}</b>\n\n"
            f"🎟 <b>Bonus:</b> You earned <b>+{bonus_entries} extra entries!</b>\n"
            "Keep inviting friends to maximize your winning odds!"
        )
        try:
            await bot.send_message(chat_id=referrer_id, text=text, parse_mode="HTML")
            return True
        except Exception:
            return False

    @staticmethod
    async def notify_claim_review(
        bot: Bot,
        user_id: int,
        giveaway_title: str,
        status: str,
        notes: str | None = None,
    ) -> bool:
        """Send notification regarding prize claim status."""
        status_titles = {
            "approved": "✅ <b>PRIZE CLAIM APPROVED!</b>",
            "rejected": "❌ <b>PRIZE CLAIM REJECTED</b>",
            "info_requested": "🔄 <b>ADDITIONAL INFORMATION NEEDED</b>",
        }
        title = status_titles.get(status, "📋 <b>PRIZE CLAIM UPDATE</b>")
        text = (
            f"{title}\n\n"
            f"Giveaway: <b>{giveaway_title}</b>\n"
            f"Status: <b>{status.upper()}</b>\n"
        )
        if notes:
            text += f"\n📝 <b>Note from Admin:</b>\n{notes}\n"

        if status == "approved":
            text += "\nYour prize has been processed. Thank you for participating!"
        elif status == "info_requested":
            text += "\nPlease contact support or reply to provide the requested details."

        try:
            await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
            return True
        except Exception:
            return False
