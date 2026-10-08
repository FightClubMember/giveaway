"""Tests for giveaway creation, participation, requirements, and bonus claims."""

import pytest
from datetime import timedelta
from unittest.mock import MagicMock
from aiogram.enums import ChatMemberStatus

from database.models import GiveawayStatus, utcnow
from database.repositories import (
    GiveawayRepository,
    RequirementRepository,
    ParticipantRepository,
    EntryRepository,
    UserRepository,
)
from services.giveaway_service import GiveawayService


@pytest.mark.asyncio
async def test_giveaway_creation(test_session):
    gw_repo = GiveawayRepository(test_session)
    end_time = utcnow() + timedelta(hours=48)
    gw = await gw_repo.create(
        title="Mega PlayStation 5 Giveaway",
        description="Win a PS5 Disc Edition",
        prize="PS5 Console",
        winners_count=3,
        end_time=end_time,
        referral_bonus=3,
        max_entries_per_user=10,
    )
    assert gw.id is not None
    assert gw.status == GiveawayStatus.ACTIVE.value
    assert gw.winners_count == 3
    assert gw.referral_bonus == 3


@pytest.mark.asyncio
async def test_join_giveaway_successful(test_session, sample_giveaway, mock_bot):
    user_repo = UserRepository(test_session)
    await user_repo.get_or_create(user_id=5001, username="gamer")

    # Mock bot get_chat_member to return MEMBER
    member_mock = MagicMock()
    member_mock.status = ChatMemberStatus.MEMBER
    mock_bot.get_chat_member.return_value = member_mock

    # Add a requirement
    req_repo = RequirementRepository(test_session)
    await req_repo.add(chat_id="@testchannel", title="Test Channel", giveaway_id=sample_giveaway.id)

    # Join
    result = await GiveawayService.join_giveaway(
        bot=mock_bot,
        session=test_session,
        giveaway_id=sample_giveaway.id,
        user_id=5001,
    )

    assert result.success is True
    assert result.status_code == "SUCCESS"
    assert result.total_entries == 1

    part_repo = ParticipantRepository(test_session)
    assert await part_repo.is_participant(sample_giveaway.id, 5001) is True


@pytest.mark.asyncio
async def test_join_giveaway_missing_channel_requirements(test_session, sample_giveaway, mock_bot):
    user_repo = UserRepository(test_session)
    await user_repo.get_or_create(user_id=5002, username="guest")

    # Mock bot to simulate user NOT in channel
    member_mock = MagicMock()
    member_mock.status = ChatMemberStatus.LEFT
    mock_bot.get_chat_member.return_value = member_mock

    req_repo = RequirementRepository(test_session)
    await req_repo.add(chat_id="@mandatory_chan", title="Mandatory Channel", giveaway_id=sample_giveaway.id)

    result = await GiveawayService.join_giveaway(
        bot=mock_bot,
        session=test_session,
        giveaway_id=sample_giveaway.id,
        user_id=5002,
    )

    assert result.success is False
    assert result.status_code == "MISSING_REQUIREMENTS"
    assert len(result.missing_requirements) == 1
    assert result.missing_requirements[0].chat_id == "@mandatory_chan"


@pytest.mark.asyncio
async def test_join_already_joined_giveaway(test_session, sample_giveaway, mock_bot):
    user_repo = UserRepository(test_session)
    await user_repo.get_or_create(user_id=5003, username="loyal_user")

    # First join
    res1 = await GiveawayService.join_giveaway(
        bot=mock_bot, session=test_session, giveaway_id=sample_giveaway.id, user_id=5003
    )
    assert res1.success is True

    # Attempt to join again
    res2 = await GiveawayService.join_giveaway(
        bot=mock_bot, session=test_session, giveaway_id=sample_giveaway.id, user_id=5003
    )
    assert res2.status_code == "ALREADY_JOINED"
    assert res2.total_entries == 1


@pytest.mark.asyncio
async def test_join_inactive_giveaway(test_session, sample_giveaway, mock_bot):
    gw_repo = GiveawayRepository(test_session)
    await gw_repo.update_status(sample_giveaway.id, GiveawayStatus.PAUSED)

    user_repo = UserRepository(test_session)
    await user_repo.get_or_create(user_id=5004)

    result = await GiveawayService.join_giveaway(
        bot=mock_bot, session=test_session, giveaway_id=sample_giveaway.id, user_id=5004
    )
    assert result.success is False
    assert result.status_code == "INACTIVE"


@pytest.mark.asyncio
async def test_daily_bonus_claim_and_cooldown(test_session, sample_giveaway, mock_bot):
    user_repo = UserRepository(test_session)
    await user_repo.get_or_create(user_id=5005)

    # Join giveaway first
    await GiveawayService.join_giveaway(
        bot=mock_bot, session=test_session, giveaway_id=sample_giveaway.id, user_id=5005
    )

    # First claim succeeds
    success, msg, count = await GiveawayService.claim_daily_bonus(test_session, user_id=5005)
    assert success is True
    assert count == 1

    # Immediate second claim should be rejected on 24h cooldown
    success2, msg2, count2 = await GiveawayService.claim_daily_bonus(test_session, user_id=5005)
    assert success2 is False
    assert "already claimed" in msg2.lower()
