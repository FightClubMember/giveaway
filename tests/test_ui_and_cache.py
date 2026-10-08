"""Tests for UI Reply Keyboard, Ban in-memory caching, Admin Claim mechanics, and API 9.4 Styled Buttons."""

import pytest
from keyboards.user import main_reply_keyboard, quick_actions_inline_keyboard
from keyboards.styled_buttons import (
    InlineKeyboardButton as StyledInlineButton,
    KeyboardButton as StyledKeyboardButton,
    TelebotInlineKeyboardButton,
    TelebotKeyboardButton,
)
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
    assert "🎁 Live Giveaways" in button_texts
    assert "🎟 Meri Tickets" in button_texts
    assert "👥 Dost Bulao (Refer)" in button_texts
    assert "🏆 Topper List" in button_texts
    assert "🔥 Daily Free Ticket" in button_texts
    assert "🤖 John Bhai Ka AI" in button_texts
    assert "👤 Meri Profile" in button_texts
    assert "ℹ️ Kaise Kaam Karta Hai?" in button_texts
    assert "⚙️ Admin Adda (Boss)" not in button_texts

    admin_kb = main_reply_keyboard(is_admin=True)
    admin_texts = [btn.text for row in admin_kb.keyboard for btn in row]
    assert "⚙️ Admin Adda (Boss)" in admin_texts


def test_quick_actions_inline_keyboard():
    """Verify quick actions keyboard has streamlined non-duplicate buttons."""
    user_kb = quick_actions_inline_keyboard(is_admin=False)
    button_texts = [btn.text for row in user_kb.inline_keyboard for btn in row]
    assert any("Live Giveaways Dekho" in t for t in button_texts)
    assert any("Dost Bulao" in t for t in button_texts)
    assert any("John Bhai" in t for t in button_texts)
    assert not any("Admin" in t for t in button_texts)

    admin_kb = quick_actions_inline_keyboard(is_admin=True)
    admin_texts = [btn.text for row in admin_kb.inline_keyboard for btn in row]
    assert any("Admin Control Panel" in t for t in admin_texts)


def test_telegram_api_9_4_styled_buttons_aiogram():
    """Verify aiogram button subclasses serialize with style='primary', 'success', 'danger'."""
    btn_success = StyledInlineButton(text="Claim", callback_data="claim", style="success")
    btn_primary = StyledInlineButton(text="Menu", callback_data="menu", style="primary")
    btn_danger = StyledInlineButton(text="Delete", callback_data="del", style="danger")

    dump_success = btn_success.model_dump(exclude_none=True)
    dump_primary = btn_primary.model_dump(exclude_none=True)
    dump_danger = btn_danger.model_dump(exclude_none=True)

    assert dump_success.get("style") == "success"
    assert dump_primary.get("style") == "primary"
    assert dump_danger.get("style") == "danger"

    kb_btn = StyledKeyboardButton(text="Start", style="primary")
    kb_dump = kb_btn.model_dump(exclude_none=True)
    assert kb_dump.get("style") == "primary"


def test_telegram_api_9_4_styled_buttons_telebot():
    """Verify telebot button subclasses serialize with style in to_dict()."""
    if TelebotInlineKeyboardButton is not None:
        t_btn = TelebotInlineKeyboardButton(text="Join", callback_data="join", style="success")
        t_dict = t_btn.to_dict()
        assert t_dict.get("style") == "success"
        assert t_dict.get("text") == "Join"

    if TelebotKeyboardButton is not None:
        t_kb = TelebotKeyboardButton(text="Home", style="danger")
        t_kb_dict = t_kb.to_dict()
        assert t_kb_dict.get("style") == "danger"
        assert t_kb_dict.get("text") == "Home"


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
