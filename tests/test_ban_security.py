"""Tests for user banning, security enforcement, and admin authentication."""

import pytest
from config import settings
from database.repositories import UserRepository
from services.giveaway_service import GiveawayService


@pytest.mark.asyncio
async def test_user_ban_and_unban(test_session):
    user_repo = UserRepository(test_session)
    user, _ = await user_repo.get_or_create(user_id=9001, username="suspect")
    assert user.is_banned is False

    # Ban
    banned = await user_repo.set_banned(user_id=9001, is_banned=True, reason="Detected bot farm")
    assert banned is True

    user_check = await user_repo.get_by_id(9001)
    assert user_check.is_banned is True
    assert user_check.ban_reason == "Detected bot farm"

    # Unban
    unbanned = await user_repo.set_banned(user_id=9001, is_banned=False)
    assert unbanned is True
    user_check2 = await user_repo.get_by_id(9001)
    assert user_check2.is_banned is False


@pytest.mark.asyncio
async def test_banned_user_cannot_join_giveaway(test_session, sample_giveaway, mock_bot):
    user_repo = UserRepository(test_session)
    await user_repo.get_or_create(user_id=9002, username="spammer")
    await user_repo.set_banned(user_id=9002, is_banned=True, reason="Multi-accounting")

    result = await GiveawayService.join_giveaway(
        bot=mock_bot,
        session=test_session,
        giveaway_id=sample_giveaway.id,
        user_id=9002,
    )
    assert result.success is False
    assert result.status_code == "BANNED"


def test_admin_authorization():
    # Test admin detection
    original_admins = settings.ADMIN_IDS
    try:
        settings.ADMIN_IDS = "111222, 333444, 555666"
        assert settings.is_admin(111222) is True
        assert settings.is_admin(333444) is True
        assert settings.is_admin(999999) is False
    finally:
        settings.ADMIN_IDS = original_admins
