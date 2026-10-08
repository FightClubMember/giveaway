"""Core giveaway participation, lifecycle, and bonus service."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Giveaway, GiveawayRequirement, GiveawayStatus, EntryType, utcnow
from database.repositories import (
    GiveawayRepository,
    RequirementRepository,
    ParticipantRepository,
    EntryRepository,
    UserRepository,
    WinnerRepository,
)
from services.verification_service import VerificationService
from services.referral_service import ReferralService

logger = logging.getLogger(__name__)


class JoinResult:
    def __init__(
        self,
        success: bool,
        status_code: str,
        message: str,
        missing_requirements: Optional[List[GiveawayRequirement]] = None,
        total_entries: int = 0,
        referrer_rewarded_id: Optional[int] = None,
    ):
        self.success = success
        self.status_code = status_code  # 'SUCCESS', 'ALREADY_JOINED', 'MISSING_REQUIREMENTS', 'INACTIVE', 'BANNED'
        self.message = message
        self.missing_requirements = missing_requirements or []
        self.total_entries = total_entries
        self.referrer_rewarded_id = referrer_rewarded_id


class GiveawayService:
    @classmethod
    async def join_giveaway(
        cls,
        bot: Bot,
        session: AsyncSession,
        giveaway_id: int,
        user_id: int,
    ) -> JoinResult:
        """Process user attempt to join a giveaway.
        
        Verifies all channel requirements, allocates base entries, and awards referral if qualified.
        """
        user_repo = UserRepository(session)
        giveaway_repo = GiveawayRepository(session)
        participant_repo = ParticipantRepository(session)
        req_repo = RequirementRepository(session)
        entry_repo = EntryRepository(session)

        # 1. Check if user is banned
        user = await user_repo.get_by_id(user_id)
        if user and user.is_banned:
            return JoinResult(False, "BANNED", "Your account is suspended from participating in giveaways.")

        # 2. Check giveaway exists and is active
        giveaway = await giveaway_repo.get_by_id(giveaway_id)
        if not giveaway:
            return JoinResult(False, "NOT_FOUND", "Giveaway not found.")
        end_time = giveaway.end_time
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        if giveaway.status != GiveawayStatus.ACTIVE.value or end_time <= utcnow():
            return JoinResult(False, "INACTIVE", "This giveaway is no longer active.")

        # 3. Check if already joined
        if await participant_repo.is_participant(giveaway_id, user_id):
            total_entries = await entry_repo.get_user_entries_for_giveaway(giveaway_id, user_id)
            return JoinResult(
                True,
                "ALREADY_JOINED",
                "You have already entered this giveaway!",
                total_entries=total_entries,
            )

        # 4. Verify channel requirements
        requirements = await req_repo.get_for_giveaway(giveaway_id)
        passed, missing = await VerificationService.verify_requirements(bot, user_id, requirements)
        if not passed:
            return JoinResult(
                False,
                "MISSING_REQUIREMENTS",
                "You must join all required channels/groups to participate.",
                missing_requirements=missing,
            )

        # 5. Add participant
        await participant_repo.add(giveaway_id=giveaway_id, user_id=user_id)

        # 6. Add Base Entry (+1)
        await entry_repo.add(
            giveaway_id=giveaway_id,
            user_id=user_id,
            entry_type=EntryType.BASE,
            amount=1,
            reference_id="initial_join",
        )

        # 7. Check if user qualifies as a referral reward for their inviter
        referrer_id = await ReferralService.reward_referrer_on_qualification(
            session=session,
            referred_user_id=user_id,
            giveaway_id=giveaway_id,
        )

        total_entries = await entry_repo.get_user_entries_for_giveaway(giveaway_id, user_id)

        return JoinResult(
            True,
            "SUCCESS",
            "🎉 You have successfully joined the giveaway!",
            total_entries=total_entries,
            referrer_rewarded_id=referrer_id,
        )

    @classmethod
    async def claim_daily_bonus(
        cls,
        session: AsyncSession,
        user_id: int,
    ) -> Tuple[bool, str, int]:
        """Claim daily activity bonus entries across active giveaways.
        
        Returns:
            (success: bool, message: str, awarded_amount: int)
        """
        user_repo = UserRepository(session)
        giveaway_repo = GiveawayRepository(session)
        entry_repo = EntryRepository(session)

        user = await user_repo.get_by_id(user_id)
        if not user:
            return False, "User not found.", 0

        now = utcnow()
        if user.last_daily_bonus_at:
            last_bonus = user.last_daily_bonus_at
            if last_bonus.tzinfo is None:
                last_bonus = last_bonus.replace(tzinfo=timezone.utc)
            delta = now - last_bonus
            if delta < timedelta(hours=24):
                hours_left = int((timedelta(hours=24) - delta).total_seconds() // 3600)
                minutes_left = int(((timedelta(hours=24) - delta).total_seconds() % 3600) // 60)
                return False, f"⏳ Daily bonus already claimed! Next bonus in {hours_left}h {minutes_left}m.", 0

        active_giveaways = await giveaway_repo.get_active_giveaways(limit=10)
        if not active_giveaways:
            return False, "No active giveaways available right now to apply bonus entries to.", 0

        # Award daily bonus entry to active giveaways user has joined
        participant_repo = ParticipantRepository(session)
        awarded_count = 0
        bonus_val = settings.DAILY_BONUS_ENTRIES

        for gw in active_giveaways:
            if await participant_repo.is_participant(gw.id, user_id):
                current = await entry_repo.get_user_entries_for_giveaway(gw.id, user_id)
                if current < gw.max_entries_per_user:
                    await entry_repo.add(
                        giveaway_id=gw.id,
                        user_id=user_id,
                        entry_type=EntryType.DAILY,
                        amount=bonus_val,
                        reference_id=now.strftime("%Y-%m-%d"),
                    )
                    awarded_count += bonus_val

        await user_repo.update_daily_bonus(user_id)

        if awarded_count > 0:
            return True, f"🔥 Daily Bonus Claimed! Added +{awarded_count} entries to your active giveaways.", awarded_count
        else:
            return True, "🔥 Daily Bonus Recorded! Join an active giveaway to have entries count towards the draw.", 0

    @classmethod
    async def get_user_giveaway_stats(
        cls,
        session: AsyncSession,
        giveaway_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """Fetch granular stats for user in a specific giveaway."""
        entry_repo = EntryRepository(session)
        breakdown = await entry_repo.get_user_entries_breakdown(giveaway_id, user_id)
        total = sum(breakdown.values())
        return {
            "total_entries": total,
            "base_entries": breakdown.get(EntryType.BASE.value, 0),
            "referral_entries": breakdown.get(EntryType.REFERRAL.value, 0),
            "daily_entries": breakdown.get(EntryType.DAILY.value, 0),
            "custom_entries": breakdown.get(EntryType.CUSTOM.value, 0),
        }

    @classmethod
    async def get_user_profile(cls, session: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Fetch overall user profile statistics."""
        user_repo = UserRepository(session)
        participant_repo = ParticipantRepository(session)
        entry_repo = EntryRepository(session)
        winner_repo = WinnerRepository(session)
        referral_summary = await ReferralService.get_referral_summary(session, user_id)

        user = await user_repo.get_by_id(user_id)
        participated_ids = await participant_repo.get_user_participated_giveaway_ids(user_id)
        wins_count = await winner_repo.count_user_wins(user_id)
        all_breakdown = await entry_repo.get_user_all_entries_breakdown(user_id)
        total_entries = sum(all_breakdown.values())

        return {
            "user": user,
            "total_entries": total_entries,
            "total_referrals": referral_summary["total_referrals"],
            "valid_referrals": referral_summary["valid_referrals"],
            "wins_count": wins_count,
            "giveaways_joined": len(participated_ids),
            "referral_link": referral_summary["referral_link"],
        }

    @classmethod
    async def broadcast_giveaway_to_connected_groups(
        cls,
        bot: Bot,
        session: AsyncSession,
        giveaway_id: int,
    ) -> int:
        """Automatically send the HD poster and announcement to all connected Telegram groups/channels."""
        from database.repositories import ConnectedChatRepository
        from services.poster_service import PosterService
        from utils.formatting import format_time_remaining
        from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton

        gw_repo = GiveawayRepository(session)
        chat_repo = ConnectedChatRepository(session)

        gw = await gw_repo.get_by_id(giveaway_id)
        if not gw:
            return 0

        chats = await chat_repo.get_all_active_auto_post()
        if not chats:
            return 0

        bot_info = await bot.get_me()
        bot_username = bot_info.username

        # Generate HD promotional poster
        time_left = format_time_remaining(gw.end_time)
        poster_io = PosterService.generate_giveaway_poster(
            title=gw.title,
            prize=gw.prize,
            winners_count=gw.winners_count,
            time_left=time_left,
        )
        poster_bytes = poster_io.getvalue()

        caption = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 <b>NEW OFFICIAL GIVEAWAY DROP! 🔥</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👑 <b>Title:</b> {gw.title}\n"
            f"💰 <b>Prize:</b> <b>{gw.prize}</b>\n"
            f"🏆 <b>Winners:</b> {gw.winners_count}\n"
            f"⏳ <b>Ends In:</b> {time_left}\n\n"
            "🎟 <b>Kaise Participate Karein?</b>\n"
            "Neeche <b>'🎁 JOIN GIVEAWAY'</b> button dabao aur direct bot me enter karo!\n"
            "Dosto ko refer karke apni jeetne ki chance 10x badhao!\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="🎁 JOIN GIVEAWAY NOW (1-Click)",
                    url=f"https://t.me/{bot_username}?start=gw_{gw.id}",
                    style="success",
                )
            ]]
        )

        sent_count = 0
        for chat in chats:
            try:
                photo_file = BufferedInputFile(poster_bytes, filename=f"giveaway_{gw.id}.png")
                msg = await bot.send_photo(
                    chat_id=chat.chat_id,
                    photo=photo_file,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
                sent_count += 1
                try:
                    await bot.pin_chat_message(chat_id=chat.chat_id, message_id=msg.message_id)
                except Exception:
                    pass
            except Exception as e:
                logger.warning("Failed to auto-post giveaway to group %d (%s): %s", chat.chat_id, chat.title, e)
                if "kicked" in str(e).lower() or "blocked" in str(e).lower() or "chat not found" in str(e).lower():
                    await chat_repo.deactivate(chat.chat_id)

        return sent_count
