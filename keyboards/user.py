"""Inline keyboards for user flows and giveaway interactions."""

from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import Giveaway, GiveawayRequirement
from config import settings


def main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Build the premium main menu hub keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="🎁 Active Giveaways", callback_data="menu_active"),
            InlineKeyboardButton(text="🏆 Winners", callback_data="menu_winners"),
        ],
        [
            InlineKeyboardButton(text="🎟 My Entries", callback_data="menu_entries"),
            InlineKeyboardButton(text="👥 Refer & Earn", callback_data="menu_referral"),
        ],
        [
            InlineKeyboardButton(text="🔥 Daily Bonus (+1)", callback_data="user_daily_bonus"),
            InlineKeyboardButton(text="🏆 Leaderboard", callback_data="menu_leaderboard"),
        ],
        [
            InlineKeyboardButton(text="🎟 Redeem Promo Code", callback_data="user_redeem_code"),
            InlineKeyboardButton(text="🤖 Ask John's AI", callback_data="menu_ai_ask"),
        ],
        [
            InlineKeyboardButton(text="👤 My Profile", callback_data="menu_profile"),
            InlineKeyboardButton(text="ℹ️ How It Works", callback_data="menu_guide"),
        ],
        [
            InlineKeyboardButton(text="📞 Support", url=settings.SUPPORT_URL),
        ],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Admin Dashboard", callback_data="admin_hub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def giveaways_pagination_keyboard(
    giveaways: List[Giveaway],
    page: int,
    total_pages: int,
    prefix: str = "gw",
) -> InlineKeyboardMarkup:
    """Paginated list of giveaways."""
    buttons = []
    for gw in giveaways:
        buttons.append([
            InlineKeyboardButton(
                text=f"🎁 {gw.title} ({gw.prize})",
                callback_data=f"{prefix}_view_{gw.id}",
            )
        ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"{prefix}_page_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{max(1, total_pages)}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"{prefix}_page_{page + 1}"))

    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def giveaway_detail_keyboard(
    giveaway_id: int,
    is_joined: bool,
    user_entries: int = 0,
) -> InlineKeyboardMarkup:
    """Action buttons for a single giveaway card."""
    buttons = []
    if not is_joined:
        buttons.append([
            InlineKeyboardButton(text="🎟 JOIN GIVEAWAY NOW", callback_data=f"gw_join_{giveaway_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="👥 Get More Entries (+Refer)", callback_data="menu_referral"),
            InlineKeyboardButton(text="🎟 My Stats", callback_data=f"gw_stats_{giveaway_id}"),
        ])

    buttons.append([
        InlineKeyboardButton(text="📜 Rules & Details", callback_data=f"gw_rules_{giveaway_id}"),
        InlineKeyboardButton(text="🔙 All Giveaways", callback_data="menu_active"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_verification_keyboard(
    giveaway_id: int,
    missing_requirements: List[GiveawayRequirement],
) -> InlineKeyboardMarkup:
    """Buttons to visit required channels/groups and verify again."""
    buttons = []
    for req in missing_requirements:
        link = req.invite_link or (f"https://t.me/{req.chat_id.replace('@', '')}" if req.chat_id.startswith('@') else None)
        text = f"👉 Join {req.title}"
        if link:
            buttons.append([InlineKeyboardButton(text=text, url=link)])

    buttons.append([
        InlineKeyboardButton(text="🔄 Verify Again", callback_data=f"gw_join_{giveaway_id}"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Back", callback_data=f"gw_view_{giveaway_id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def referral_share_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """Social share keyboard for referral link."""
    share_url = f"https://t.me/share/url?url={referral_link}&text=Join%20this%20exclusive%20giveaway%20hub%20now!"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📤 Share Link With Friends", url=share_url),
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main"),
            ],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Simple back button to return to main menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main")]
        ]
    )
