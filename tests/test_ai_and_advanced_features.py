"""Tests for Groq AI assistant, HD Poster generation, Promo codes, and Leaderboards."""

import pytest
from PIL import Image

from services.ai_service import GroqAIService
from services.poster_service import PosterService
from services.promo_service import PromoService
from database.repositories import UserRepository, ReferralRepository, LeaderboardRepository


@pytest.mark.asyncio
async def test_groq_ai_user_query_fallback():
    """Ensure AI assistant generates intelligent guidance even if API key is not supplied."""
    ans_ref = await GroqAIService.answer_user_query("Dave", "How do referrals work?")
    assert "referral" in ans_ref.lower() or "invite" in ans_ref.lower()

    ans_win = await GroqAIService.answer_user_query("Dave", "How are winners picked fairly?")
    assert "fair" in ans_win.lower() or "winner" in ans_win.lower()

    ans_claim = await GroqAIService.answer_user_query("Dave", "How do I claim my prize?")
    assert "claim" in ans_claim.lower() or "prize" in ans_claim.lower()


def test_poster_service_image_generation():
    """Test HD poster generation produces a valid non-empty PNG image."""
    buffer = PosterService.generate_giveaway_poster(
        title="PS5 Pro Mega Giveaway",
        prize="Sony PlayStation 5 Pro 2TB",
        winners_count=3,
        time_left="2d 5h",
    )
    assert buffer is not None
    data = buffer.getvalue()
    assert len(data) > 5000  # Valid PNG has substantial size

    # Verify PIL can open it
    buffer.seek(0)
    img = Image.open(buffer)
    assert img.size in [(1200, 675), (1000, 560)]
    assert img.format == "PNG"

    # Verify welcome poster generation
    w_buf = PosterService.generate_welcome_poster(user_name="Himanshu")
    assert w_buf is not None
    w_data = w_buf.getvalue()
    assert len(w_data) > 5000
    w_buf.seek(0)
    w_img = Image.open(w_buf)
    assert w_img.size == (1200, 675)
    assert w_img.format == "PNG"


@pytest.mark.asyncio
async def test_promo_code_lifecycle(test_session, sample_giveaway):
    """Test promo code creation, redemption, and duplicate prevention."""
    # 1. Create code
    created, msg = await PromoService.create_code(
        session=test_session,
        code="JOHNSPECIAL",
        entries_amount=5,
        max_uses=2,
        giveaway_id=sample_giveaway.id,
    )
    assert created is True

    # 2. Redeem by User 1
    success, reply, amount = await PromoService.redeem_code(test_session, "JOHNSPECIAL", user_id=9991)
    assert success is True
    assert amount == 5
    assert "+5" in reply

    # 3. Duplicate redemption attempt by User 1
    dup_success, dup_reply, _ = await PromoService.redeem_code(test_session, "JOHNSPECIAL", user_id=9991)
    assert dup_success is False
    assert "already redeemed" in dup_reply.lower()

    # 4. Redeem by User 2 (reaches max limit of 2)
    u2_success, _, _ = await PromoService.redeem_code(test_session, "JOHNSPECIAL", user_id=9992)
    assert u2_success is True

    # 5. User 3 attempts to redeem capped code
    u3_success, u3_reply, _ = await PromoService.redeem_code(test_session, "JOHNSPECIAL", user_id=9993)
    assert u3_success is False
    assert "maximum redemption limit" in u3_reply.lower()


@pytest.mark.asyncio
async def test_leaderboard_queries(test_session):
    """Test leaderboard returns ranked users."""
    user_repo = UserRepository(test_session)
    ref_repo = ReferralRepository(test_session)
    lb_repo = LeaderboardRepository(test_session)

    # Setup users
    await user_repo.get_or_create(user_id=8881, username="top_inviter")
    await user_repo.get_or_create(user_id=8882, username="friend1", referrer_id=8881)
    await ref_repo.mark_valid(8882)

    top_refs = await lb_repo.get_top_referrers(limit=5)
    assert len(top_refs) >= 1
    assert top_refs[0][0].id == 8881
    assert top_refs[0][1] == 1
