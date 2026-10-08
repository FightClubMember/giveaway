"""Inline and Reply keyboards for user flows with modern, colorful Telegram styling."""

from typing import List
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from database.models import Giveaway, GiveawayRequirement
from config import settings


def main_reply_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Persistent native bottom Reply Keyboard for 1-tap navigation."""
    rows = [
        [
            KeyboardButton(text="🎁 Active Giveaways"),
            KeyboardButton(text="🎟 My Entries"),
        ],
        [
            KeyboardButton(text="👥 Refer & Earn"),
            KeyboardButton(text="🏆 Leaderboard"),
        ],
        [
            KeyboardButton(text="🔥 Daily Bonus"),
            KeyboardButton(text="🤖 Ask John's AI"),
        ],
        [
            KeyboardButton(text="👤 My Profile"),
            KeyboardButton(text="ℹ️ How It Works"),
        ],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="⚙️ Admin Dashboard")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="🎁 Tap an option below or type a message...",
    )


def main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Vibrant, colorful inline keyboard with modern emoji hierarchy."""
    buttons = [
        [
            InlineKeyboardButton(text="🎁 Explore Giveaways 🟢", callback_data="menu_active"),
            InlineKeyboardButton(text="🏆 Hall of Winners 👑", callback_data="menu_winners"),
        ],
        [
            InlineKeyboardButton(text="🎟 My Active Entries 💎", callback_data="menu_entries"),
            InlineKeyboardButton(text="👥 Invite & Multiply 🚀", callback_data="menu_referral"),
        ],
        [
            InlineKeyboardButton(text="🔥 Daily Free Ticket ⚡", callback_data="user_daily_bonus"),
            InlineKeyboardButton(text="🏆 Top Leaderboard 🌟", callback_data="menu_leaderboard"),
        ],
        [
            InlineKeyboardButton(text="🎟 Redeem Voucher 🔮", callback_data="user_redeem_code"),
            InlineKeyboardButton(text="🤖 Ask John's AI 🧠", callback_data="menu_ai_ask"),
        ],
        [
            InlineKeyboardButton(text="👤 My Account & Wins 📊", callback_data="menu_profile"),
            InlineKeyboardButton(text="ℹ️ Rules & Guide 📖", callback_data="menu_guide"),
        ],
        [
            InlineKeyboardButton(text="📞 24/7 VIP Support 💬", url=settings.SUPPORT_URL),
        ],
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="⚙️ Admin Control Center 👑", callback_data="admin_hub")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
            )
        ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"{prefix}_page_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{max(1, total_pages)}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"{prefix}_page_{page + 1}"))

    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main")])
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
            InlineKeyboardButton(text="🎟️ ENTER GIVEAWAY NOW 🚀", callback_data=f"gw_join_{giveaway_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="👥 Get Extra Entries (+Refer)", callback_data="menu_referral"),
            InlineKeyboardButton(text="📊 My Entry Breakdown", callback_data=f"gw_stats_{giveaway_id}"),
        ])

    buttons.append([
        InlineKeyboardButton(text="📜 Official Rules", callback_data=f"gw_rules_{giveaway_id}"),
        InlineKeyboardButton(text="🔙 Back to Giveaways", callback_data="menu_active"),
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
            buttons.append([InlineKeyboardButton(text=text, url=link)])

    buttons.append([
        InlineKeyboardButton(text="🔄 Verify Membership Now ⚡", callback_data=f"gw_join_{giveaway_id}"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Back", callback_data=f"gw_view_{giveaway_id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def referral_share_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """Vibrant social share keyboard."""
    share_url = f"https://t.me/share/url?url={referral_link}&text=Join%20John's%20Giveaway%20Bot%20to%20win%20prizes!"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📤 Share Link with Friends 🚀", url=share_url),
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main"),
            ],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Standard back button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main")]
        ]
    )
