"""Advanced edge cases and automated scheduler tests."""

import pytest
import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from database.models import GiveawayStatus, EntryType, utcnow
from database.repositories import (
    GiveawayRepository,
    EntryRepository,
    WinnerRepository,
    UserRepository,
    WinnerClaimRepository,
)
from services.winner_service import WinnerService
from services.referral_service import ReferralService
from services.broadcast_service import BroadcastService
from services.giveaway_service import GiveawayService


@pytest.mark.asyncio
async def test_auto_due_giveaways_query_and_draw(test_session, sample_giveaway):
    """Test scheduler query finds giveaways where end_time <= now."""
    gw_repo = GiveawayRepository(test_session)
    entry_repo = EntryRepository(test_session)

    # Set giveaway end_time in the past
    past_time = utcnow() - timedelta(minutes=10)
    sample_giveaway.end_time = past_time
    await test_session.commit()

    due = await gw_repo.get_due_active_giveaways()
    assert len(due) == 1
    assert due[0].id == sample_giveaway.id

    # Add participants
    await entry_repo.add(sample_giveaway.id, 9901, EntryType.BASE, amount=1)
    await entry_repo.add(sample_giveaway.id, 9902, EntryType.BASE, amount=3)

    # Execute draw
    res = await WinnerService.select_winners(test_session, sample_giveaway.id)
    assert len(res.winners) == 2

    # Should no longer be due
    due_after = await gw_repo.get_due_active_giveaways()
    assert len(due_after) == 0


@pytest.mark.asyncio
async def test_referral_cap_enforcement(test_session, sample_giveaway):
    """Test that referral entries do not exceed max_entries_per_user."""
    entry_repo = EntryRepository(test_session)
    user_repo = UserRepository(test_session)

    # Set max entries low
    sample_giveaway.max_entries_per_user = 3
    sample_giveaway.referral_bonus = 2
    await test_session.commit()

    # User already has 2 entries
    await user_repo.get_or_create(user_id=8801, username="capped_user")
    await entry_repo.add(sample_giveaway.id, 8801, EntryType.BASE, amount=2)

    # Referrer invited user 8802
    await user_repo.get_or_create(user_id=8802, referrer_id=8801)
    awarded_id = await ReferralService.reward_referrer_on_qualification(
        session=test_session,
        referred_user_id=8802,
        giveaway_id=sample_giveaway.id,
    )
    assert awarded_id == 8801

    # Should only have been awarded +1 entry to reach the cap of 3
    total = await entry_repo.get_user_entries_for_giveaway(sample_giveaway.id, 8801)
    assert total == 3


@pytest.mark.asyncio
async def test_broadcast_service_execution(test_session, mock_bot):
    """Test broadcast iterates through users and tallies results."""
    from config import settings
    orig_delay = settings.RATE_LIMIT_DELAY
    settings.RATE_LIMIT_DELAY = 0.0

    try:
        user_repo = UserRepository(test_session)
        for i in range(5):
            await user_repo.get_or_create(user_id=7700 + i)

        res = await BroadcastService.send_broadcast(
            bot=mock_bot,
            session=test_session,
            admin_id=123456,
            text="Hello world!",
        )

        assert res.total >= 5
        assert res.sent >= 5
        assert res.failed == 0
    finally:
        settings.RATE_LIMIT_DELAY = orig_delay
