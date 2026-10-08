"""Tests for auditable cryptographic winner selection."""

import pytest
from database.models import Giveaway, GiveawayStatus, EntryType, utcnow
from database.repositories import EntryRepository, WinnerRepository, GiveawayRepository
from services.winner_service import WinnerService


@pytest.mark.asyncio
async def test_winner_selection_fair_and_unique(test_session, sample_giveaway):
    entry_repo = EntryRepository(test_session)

    # User 1: 1 entry
    await entry_repo.add(sample_giveaway.id, 6001, EntryType.BASE, amount=1)
    # User 2: 10 entries
    await entry_repo.add(sample_giveaway.id, 6002, EntryType.BASE, amount=10)
    # User 3: 5 entries
    await entry_repo.add(sample_giveaway.id, 6003, EntryType.BASE, amount=5)

    # Draw 2 winners
    result = await WinnerService.select_winners(test_session, sample_giveaway.id, force_count=2)

    assert len(result.winners) == 2
    assert result.total_participants == 3
    assert result.total_entries == 16
    assert len(result.selection_hash) == 64  # Valid SHA-256 hex string

    winner_ids = [w.user_id for w in result.winners]
    # Verify no duplicates
    assert len(set(winner_ids)) == 2

    # Verify status changed to ended
    gw_repo = GiveawayRepository(test_session)
    gw = await gw_repo.get_by_id(sample_giveaway.id)
    assert gw.status == GiveawayStatus.ENDED.value


@pytest.mark.asyncio
async def test_winner_selection_empty_pool(test_session, sample_giveaway):
    """When a giveaway has 0 entries, select_winners handles gracefully."""
    result = await WinnerService.select_winners(test_session, sample_giveaway.id)
    assert len(result.winners) == 0
    assert result.total_entries == 0


@pytest.mark.asyncio
async def test_winner_selection_fewer_participants_than_winners(test_session, sample_giveaway):
    """When requested winners count (e.g. 5) is greater than total participants (1)."""
    entry_repo = EntryRepository(test_session)
    await entry_repo.add(sample_giveaway.id, 7001, EntryType.BASE, amount=1)

    result = await WinnerService.select_winners(test_session, sample_giveaway.id, force_count=5)
    assert len(result.winners) == 1
    assert result.winners[0].user_id == 7001
