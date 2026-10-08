"""Telegram Channel and Community membership verification service."""

import logging
from typing import List, Tuple
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

from database.models import GiveawayRequirement

logger = logging.getLogger(__name__)

VALID_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.RESTRICTED,
}


class VerificationService:
    @staticmethod
    async def verify_user_in_channel(bot: Bot, chat_id: str, user_id: int) -> bool:
        """Verify if a user is an active member/admin of the specified channel or group.
        
        Args:
            bot: aiogram Bot instance.
            chat_id: Username (e.g. '@channel') or numeric chat ID (e.g. '-1001234567890').
            user_id: Telegram user ID to verify.
            
        Returns:
            True if user is verified as an active member, False otherwise.
        """
        try:
            # Normalize chat_id if numeric
            target_chat: str | int = chat_id
            if chat_id.startswith("-") and chat_id[1:].isdigit():
                target_chat = int(chat_id)
            elif chat_id.isdigit():
                target_chat = int(chat_id)

            member = await bot.get_chat_member(chat_id=target_chat, user_id=user_id)
            
            if member.status in VALID_STATUSES:
                # If restricted, ensure they haven't been banned from reading
                if member.status == ChatMemberStatus.RESTRICTED:
                    # If is_member is False, they are effectively kicked/restricted out
                    return getattr(member, "is_member", True)
                return True
            return False

        except TelegramBadRequest as e:
            err_msg = str(e).lower()
            if "user not found" in err_msg or "participant_id_invalid" in err_msg:
                return False
            if "chat not found" in err_msg:
                logger.warning("Verification check chat not found: %s", chat_id)
                # If the chat cannot be found by bot, log and don't hard-block users
                return False
            logger.warning("TelegramBadRequest verifying user %d in %s: %s", user_id, chat_id, e)
            return False
        except TelegramForbiddenError:
            logger.error("Bot is not an administrator in channel %s to check membership", chat_id)
            # Cannot verify membership without bot having access
            return False
        except TelegramAPIError as e:
            logger.error("Telegram API error during verification: %s", e)
            return False
        except Exception as e:
            logger.exception("Unexpected error verifying channel membership: %s", e)
            return False

    @classmethod
    async def verify_requirements(
        cls, bot: Bot, user_id: int, requirements: List[GiveawayRequirement]
    ) -> Tuple[bool, List[GiveawayRequirement]]:
        """Verify user membership across all mandatory giveaway requirements.
        
        Returns:
            (all_passed: bool, missing_requirements: list)
        """
        missing = []
        for req in requirements:
            if not req.is_mandatory:
                continue
            is_member = await cls.verify_user_in_channel(bot, req.chat_id, user_id)
            if not is_member:
                missing.append(req)

        return len(missing) == 0, missing
