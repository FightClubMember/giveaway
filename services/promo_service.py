"""Secret Promo / Voucher Code management and redemption service."""

import logging
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import EntryType
from database.repositories import (
    PromoRepository,
    EntryRepository,
    GiveawayRepository,
    UserRepository,
    ParticipantRepository,
)

logger = logging.getLogger(__name__)


class PromoService:
    @classmethod
    async def create_code(
        cls,
        session: AsyncSession,
        code: str,
        entries_amount: int = 5,
        max_uses: int = 100,
        giveaway_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> Tuple[bool, str]:
        promo_repo = PromoRepository(session)
        existing = await promo_repo.get_by_code(code)
        if existing:
            return False, f"Code '{code.upper()}' already exists."

        await promo_repo.create(
            code=code,
            entries_amount=entries_amount,
            max_uses=max_uses,
            giveaway_id=giveaway_id,
            created_by=created_by,
        )
        return True, f"Promo code '{code.upper()}' created successfully (+{entries_amount} entries, {max_uses} uses)."

    @classmethod
    async def redeem_code(
        cls,
        session: AsyncSession,
        code: str,
        user_id: int,
    ) -> Tuple[bool, str, int]:
        """Redeem a promo code for bonus giveaway entries."""
        promo_repo = PromoRepository(session)
        entry_repo = EntryRepository(session)
        gw_repo = GiveawayRepository(session)
        part_repo = ParticipantRepository(session)

        promo = await promo_repo.get_by_code(code)
        if not promo:
            return False, "❌ Invalid promo code. Please double-check the spelling.", 0

        if promo.uses_count >= promo.max_uses:
            return False, "⚠️ This promo code has reached its maximum redemption limit.", 0

        if await promo_repo.is_redeemed_by_user(promo.id, user_id):
            return False, "⚠️ You have already redeemed this promo code!", 0

        # Find target giveaway: either the one bound to promo, or the user's active giveaway
        target_gw_id = promo.giveaway_id
        if not target_gw_id:
            active_list = await gw_repo.get_active_giveaways(limit=5)
            if not active_list:
                return False, "No active giveaways available to apply bonus entries to right now.", 0
            # Target the first active giveaway
            target_gw_id = active_list[0].id

        # Make sure user is joined or join them
        if not await part_repo.is_participant(target_gw_id, user_id):
            await part_repo.add(giveaway_id=target_gw_id, user_id=user_id)

        # Allocate entries
        await entry_repo.add(
            giveaway_id=target_gw_id,
            user_id=user_id,
            entry_type=EntryType.CUSTOM,
            amount=promo.entries_amount,
            reference_id=f"promo_{promo.code}",
        )

        # Mark redeemed
        await promo_repo.redeem(promo.id, user_id)

        return True, f"🎉 Promo code redeemed! You received <b>+{promo.entries_amount} extra entries</b>!", promo.entries_amount
