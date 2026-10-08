"""Tests for user registration, referral binding, and anti-abuse mechanisms."""

import pytest
from database.repositories import UserRepository, ReferralRepository, EntryRepository
from services.referral_service import ReferralService
from services.giveaway_service import GiveawayService
from database.models import EntryType


@pytest.mark.asyncio
async def test_user_registration(test_session):
    user_repo = UserRepository(test_session)
    user, is_new = await user_repo.get_or_create(
        user_id=1001,
        username="alice",
        first_name="Alice",
    )
    assert is_new is True
    assert user.id == 1001
    assert user.username == "alice"

    # Second call should not recreate
    user_again, is_new_again = await user_repo.get_or_create(user_id=1001)
    assert is_new_again is False
    assert user_again.id == 1001


@pytest.mark.asyncio
async def test_self_referral_prevention(test_session):
    """Ensure user cannot refer themselves."""
    is_new, referrer_id = await ReferralService.process_referral_start(
        session=test_session,
        user_id=2001,
        raw_start_param="ref_2001",  # Self-referral attempt
        username="charlie",
    )
    assert is_new is True
    assert referrer_id is None

    user_repo = UserRepository(test_session)
    user = await user_repo.get_by_id(2001)
    assert user.referrer_id is None


@pytest.mark.asyncio
async def test_duplicate_referral_prevention(test_session):
    """Ensure an existing user cannot change their referrer later."""
    user_repo = UserRepository(test_session)
    # Register referrer
    await user_repo.get_or_create(user_id=3001, username="inviter1")
    await user_repo.get_or_create(user_id=3002, username="inviter2")

    # User joins with first referrer
    is_new, ref1 = await ReferralService.process_referral_start(
        session=test_session,
        user_id=3003,
        raw_start_param="ref_3001",
    )
    assert is_new is True
    assert ref1 == 3001

    # User starts bot again with different referral parameter
    is_new2, ref2 = await ReferralService.process_referral_start(
        session=test_session,
        user_id=3003,
        raw_start_param="ref_3002",
    )
    assert is_new2 is False
    assert ref2 == 3001  # Referrer remains the original inviter!


@pytest.mark.asyncio
async def test_referral_reward_on_giveaway_qualification(test_session, sample_giveaway):
    """Ensure referrer is only rewarded when referred user joins an active giveaway."""
    user_repo = UserRepository(test_session)
    ref_repo = ReferralRepository(test_session)
    entry_repo = EntryRepository(test_session)

    # 1. Register referrer
    await user_repo.get_or_create(user_id=4001, username="bob")

    # 2. Register referee with referral param
    await ReferralService.process_referral_start(
        session=test_session,
        user_id=4002,
        raw_start_param="ref_4001",
    )

    # Referral is initially not valid
    ref_record = await ref_repo.get_by_referred_id(4002)
    assert ref_record is not None
    assert ref_record.is_valid is False

    # 3. Reward qualification
    rewarded_referrer_id = await ReferralService.reward_referrer_on_qualification(
        session=test_session,
        referred_user_id=4002,
        giveaway_id=sample_giveaway.id,
    )
    assert rewarded_referrer_id == 4001

    # Referral is now valid
    ref_record_after = await ref_repo.get_by_referred_id(4002)
    assert ref_record_after.is_valid is True

    # Check referrer was credited with referral bonus
    referrer_entries = await entry_repo.get_user_entries_for_giveaway(sample_giveaway.id, 4001)
    assert referrer_entries == sample_giveaway.referral_bonus

    # Second qualification attempt on the same referred user should not double-reward
    reward_again = await ReferralService.reward_referrer_on_qualification(
        session=test_session,
        referred_user_id=4002,
        giveaway_id=sample_giveaway.id,
    )
    assert reward_again is None
