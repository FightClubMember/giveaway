"""Tests for UI Reply Keyboard, Ban in-memory caching, and Admin Claim mechanics."""

import pytest
from keyboards.user import main_reply_keyboard
from middlewares.ban import BanMiddleware
from handlers.admin import require_admin, RUNTIME_ADMINS
from utils.formatting import make_progress_bar


def test_main_reply_keyboard():
    """Verify reply keyboard structure for regular users and admins."""
    user_kb = main_reply_keyboard(is_admin=False)
    assert user_kb.resize_keyboard is True
    assert user_kb.is_persistent is True
    # Verify key buttons exist
    button_texts = [btn.text for row in user_kb.keyboard for btn in row]
    assert "🎁 Active Giveaways" in button_texts
    assert "🎟 My Entries" in button_texts
    assert "👥 Refer & Earn" in button_texts
    assert "🏆 Leaderboard" in button_texts
    assert "🔥 Daily Bonus" in button_texts
    assert "🤖 Ask John's AI" in button_texts
    assert "👤 My Profile" in button_texts
    assert "ℹ️ How It Works" in button_texts
    assert "⚙️ Admin Dashboard" not in button_texts

    admin_kb = main_reply_keyboard(is_admin=True)
    admin_texts = [btn.text for row in admin_kb.keyboard for btn in row]
    assert "⚙️ Admin Dashboard" in admin_texts


def test_ban_cache_in_memory():
    """Verify in-memory ban cache set operations."""
    test_id = 987654321
    BanMiddleware.mark_unbanned(test_id)
    assert test_id not in BanMiddleware.banned_cache

    BanMiddleware.mark_banned(test_id)
    assert test_id in BanMiddleware.banned_cache
    BanMiddleware.mark_unbanned(test_id)
    assert test_id not in BanMiddleware.banned_cache


def test_runtime_admin_authorization():
    """Verify runtime admin authorization mechanisms."""
    test_admin_id = 1122334455
    RUNTIME_ADMINS.add(test_admin_id)
    assert require_admin(test_admin_id) is True
    RUNTIME_ADMINS.remove(test_admin_id)


def test_formatting_progress_bar():
    """Verify block progress bar calculation."""
    bar_0 = make_progress_bar(0, 10, length=8)
    assert bar_0 == "▱▱▱▱▱▱▱▱"

    bar_half = make_progress_bar(5, 10, length=8)
    assert bar_half == "▰▰▰▰▱▱▱▱"

    bar_full = make_progress_bar(10, 10, length=8)
    assert bar_full == "▰▰▰▰▰▰▰▰"
