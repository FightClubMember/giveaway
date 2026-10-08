"""Tests for winner prize claiming and administrator review workflow."""

import pytest
from datetime import timedelta
from database.models import ClaimStatus, utcnow
from database.repositories import WinnerRepository, WinnerClaimRepository


@pytest.mark.asyncio
async def test_winner_claim_creation_and_approval(test_session, sample_giveaway):
    winner_repo = WinnerRepository(test_session)
    claim_repo = WinnerClaimRepository(test_session)

    # Register a winner
    winner = await winner_repo.add(
        giveaway_id=sample_giveaway.id,
        user_id=8001,
        rank=1,
        entries_count=5,
        selection_hash="testhash123",
    )

    # Winner submits claim
    expires_at = utcnow() + timedelta(hours=24)
    claim = await claim_repo.create(
        winner_id=winner.id,
        giveaway_id=sample_giveaway.id,
        user_id=8001,
        claim_data="UPI: winner@okhdfcbank",
        expires_at=expires_at,
    )

    assert claim.id is not None
    assert claim.status == ClaimStatus.PENDING.value
    assert claim.claim_data == "UPI: winner@okhdfcbank"

    # Admin reviews and approves
    approved = await claim_repo.update_status(
        claim_id=claim.id,
        status=ClaimStatus.APPROVED,
        notes="Transferred via UPI Ref #987654",
        reviewed_by=999999,
    )
    assert approved is True

    # Verify claim state
    updated_claim = await claim_repo.get_by_id(claim.id)
    assert updated_claim.status == ClaimStatus.APPROVED.value
    assert updated_claim.reviewed_by == 999999
    assert "987654" in updated_claim.admin_notes


@pytest.mark.asyncio
async def test_instant_reward_and_custom_prompt_settings(test_session, sample_giveaway):
    from database.repositories import GiveawayRepository
    gw_repo = GiveawayRepository(test_session)

    # Configure instant redeem reward
    success = await gw_repo.update_reward_settings(
        giveaway_id=sample_giveaway.id,
        claim_type="instant",
        secret_reward="STEAM-KEY-XYZ-999",
        custom_claim_prompt="Enjoy your Steam key directly!",
    )
    assert success is True

    # Verify retrieval
    gw = await gw_repo.get_by_id(sample_giveaway.id)
    assert gw.claim_type == "instant"
    assert gw.secret_reward == "STEAM-KEY-XYZ-999"
    assert gw.custom_claim_prompt == "Enjoy your Steam key directly!"
