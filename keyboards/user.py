"""Inline and Reply keyboards for user flows with modern, colorful Telegram Bot API 9.4 styling."""

from typing import List
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from keyboards.styled_buttons import InlineKeyboardButton, KeyboardButton
from database.models import Giveaway, GiveawayRequirement
from config import settings


def main_reply_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Persistent native bottom Reply Keyboard for 1-tap navigation with API 9.4 styling."""
    rows = [
        [
            KeyboardButton(text="🎁 Active Giveaways", style="success"),
            KeyboardButton(text="🎟 My Entries", style="primary"),
        ],
        [
            KeyboardButton(text="👥 Refer & Earn", style="primary"),
            KeyboardButton(text="🏆 Leaderboard", style="primary"),
        ],
        [
            KeyboardButton(text="🔥 Daily Bonus", style="success"),
            KeyboardButton(text="🤖 Ask John's AI", style="primary"),
        ],
        [
            KeyboardButton(text="👤 My Profile", style="primary"),
            KeyboardButton(text="ℹ️ How It Works", style="primary"),
        ],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="⚙️ Admin Dashboard", style="danger")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="🎁 Tap an option below or type a message...",
    )


def quick_actions_inline_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Streamlined quick-action inline buttons (no duplicates with bottom keyboard)."""
    buttons = [
        [
            InlineKeyboardButton(text="🎁 Browse Active Giveaways 🟢", callback_data="menu_active", style="success"),
            InlineKeyboardButton(text="👥 Invite Friends & Earn 🚀", callback_data="menu_referral", style="primary"),
        ],
        [
            InlineKeyboardButton(text="🤖 Ask John's AI Concierge ⚡", callback_data="menu_ai_ask", style="primary"),
            InlineKeyboardButton(text="🎟 Redeem Voucher 🔮", callback_data="user_redeem_code", style="primary"),
        ],
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="⚙️ Open Admin Control Center 👑", callback_data="admin_hub", style="danger")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Alias for quick_actions_inline_keyboard to eliminate duplicate button clutter."""
    return quick_actions_inline_keyboard(is_admin=is_admin)


def giveaways_pagination_keyboard(
    giveaways: List[Giveaway],
    page: int,
    total_pages: int,
    prefix: str = "gw",
) -> InlineKeyboardMarkup:
    """Paginated list of giveaways with status badges."""
    buttons = []
    for gw in giveaways:
        buttons.append([
            InlineKeyboardButton(
                text=f"🎁 {gw.title} • [{gw.prize}]",
                callback_data=f"{prefix}_view_{gw.id}",
                style="success",
            )
        ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"{prefix}_page_{page - 1}", style="primary"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{max(1, total_pages)}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"{prefix}_page_{page + 1}", style="primary"))

    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def giveaway_detail_keyboard(
    giveaway_id: int,
    is_joined: bool,
    user_entries: int = 0,
) -> InlineKeyboardMarkup:
    """High-conversion action buttons for a single giveaway card."""
    buttons = []
    if not is_joined:
        buttons.append([
            InlineKeyboardButton(text="🎟️ ENTER GIVEAWAY NOW 🚀", callback_data=f"gw_join_{giveaway_id}", style="success")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="👥 Extra Entries (+Refer)", callback_data="menu_referral", style="primary"),
            InlineKeyboardButton(text="📊 My Entry Breakdown", callback_data=f"gw_stats_{giveaway_id}", style="primary"),
        ])

    buttons.append([
        InlineKeyboardButton(text="📜 Official Rules", callback_data=f"gw_rules_{giveaway_id}", style="primary"),
        InlineKeyboardButton(text="🔙 Back to Giveaways", callback_data="menu_active", style="primary"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_verification_keyboard(
    giveaway_id: int,
    missing_requirements: List[GiveawayRequirement],
) -> InlineKeyboardMarkup:
    """Bright action buttons to join missing channels and verify."""
    buttons = []
    for req in missing_requirements:
        link = req.invite_link or (f"https://t.me/{req.chat_id.replace('@', '')}" if req.chat_id.startswith('@') else None)
        text = f"👉 Join {req.title} 📢"
        if link:
            buttons.append([InlineKeyboardButton(text=text, url=link, style="primary")])

    buttons.append([
        InlineKeyboardButton(text="🔄 Verify Membership Now ⚡", callback_data=f"gw_join_{giveaway_id}", style="success"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Back", callback_data=f"gw_view_{giveaway_id}", style="danger"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def referral_share_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """Vibrant social share keyboard."""
    share_url = f"https://t.me/share/url?url={referral_link}&text=Join%20John's%20Giveaway%20Bot%20to%20win%20prizes!"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📤 Share Link with Friends 🚀", url=share_url, style="success"),
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main", style="primary"),
            ],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Standard back button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main", style="primary")]
        ]
    )
