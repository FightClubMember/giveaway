"""Referral management and reward processing service."""

import logging
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import EntryType
from database.repositories import (
    UserRepository,
    ReferralRepository,
    EntryRepository,
    GiveawayRepository,
)

logger = logging.getLogger(__name__)


class ReferralService:
    @staticmethod
    def get_referral_link(user_id: int) -> str:
        """Construct a unique Telegram referral link for the user."""
        return f"https://t.me/{settings.BOT_USERNAME}?start=ref_{user_id}"

    @classmethod
    async def process_referral_start(
        cls,
        session: AsyncSession,
        user_id: int,
        raw_start_param: Optional[str],
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[int]]:
        """Handle /start command with possible referral payload.
        
        Returns:
            (is_new_user: bool, referrer_id: Optional[int])
        """
        referrer_id: Optional[int] = None
        if raw_start_param and raw_start_param.startswith("ref_"):
            potential_id = raw_start_param.replace("ref_", "").strip()
            if potential_id.isdigit():
                ref_id = int(potential_id)
                # Anti-abuse: Prevent self-referral
                if ref_id != user_id:
                    referrer_id = ref_id

        user_repo = UserRepository(session)
        user, is_new = await user_repo.get_or_create(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            referrer_id=referrer_id,
        )

        return is_new, user.referrer_id

    @classmethod
    async def reward_referrer_on_qualification(
        cls,
        session: AsyncSession,
        referred_user_id: int,
        giveaway_id: int,
    ) -> Optional[int]:
        """Reward the referrer once the referred user joins a giveaway and passes verification.
        
        Awards referral bonus entries to the referrer for the active giveaway.
        Returns the referrer's user ID if newly rewarded, or None.
        """
        ref_repo = ReferralRepository(session)
        referral = await ref_repo.mark_valid(referred_user_id)
        if not referral:
            return None

        referrer_id = referral.referrer_id
        giveaway_repo = GiveawayRepository(session)
        entry_repo = EntryRepository(session)

        giveaway = await giveaway_repo.get_by_id(giveaway_id)
        if not giveaway:
            return referrer_id

        # Check maximum entry cap for the referrer
        current_entries = await entry_repo.get_user_entries_for_giveaway(giveaway_id, referrer_id)
        bonus_to_add = min(
            giveaway.referral_bonus,
            max(0, giveaway.max_entries_per_user - current_entries),
        )

        if bonus_to_add > 0:
            await entry_repo.add(
                giveaway_id=giveaway_id,
                user_id=referrer_id,
                entry_type=EntryType.REFERRAL,
                amount=bonus_to_add,
                reference_id=f"ref_{referred_user_id}",
            )
            logger.info(
                "Awarded +%d referral entries to referrer %d for user %d in giveaway #%d",
                bonus_to_add,
                referrer_id,
                referred_user_id,
                giveaway_id,
            )

        return referrer_id

    @classmethod
    async def get_referral_summary(cls, session: AsyncSession, user_id: int) -> dict:
        """Retrieve total, valid referrals and referral entries earned by user."""
        ref_repo = ReferralRepository(session)
        entry_repo = EntryRepository(session)

        total_refs = await ref_repo.count_total_for_user(user_id)
        valid_refs = await ref_repo.count_valid_for_user(user_id)
        breakdown = await entry_repo.get_user_all_entries_breakdown(user_id)
        bonus_entries = breakdown.get(EntryType.REFERRAL.value, 0)

        return {
            "total_referrals": total_refs,
            "valid_referrals": valid_refs,
            "bonus_entries": bonus_entries,
            "referral_link": cls.get_referral_link(user_id),
        }
