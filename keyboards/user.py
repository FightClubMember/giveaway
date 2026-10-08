"""Inline and Reply keyboards for user flows with hardcore friendly Hinglish and Telegram Bot API 9.4 styling."""

from typing import List
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from keyboards.styled_buttons import InlineKeyboardButton, KeyboardButton
from database.models import Giveaway, GiveawayRequirement
from config import settings


def main_reply_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Persistent native bottom Reply Keyboard in friendly Hinglish with API 9.4 styling."""
    rows = [
        [
            KeyboardButton(text="🎁 Live Giveaways", style="success"),
            KeyboardButton(text="🎟 Meri Tickets", style="primary"),
        ],
        [
            KeyboardButton(text="👥 Dost Bulao (Refer)", style="primary"),
            KeyboardButton(text="🏆 Topper List", style="primary"),
        ],
        [
            KeyboardButton(text="🔥 Daily Free Ticket", style="success"),
            KeyboardButton(text="🤖 John Bhai Ka AI", style="primary"),
        ],
        [
            KeyboardButton(text="👤 Meri Profile", style="primary"),
            KeyboardButton(text="ℹ️ Kaise Kaam Karta Hai?", style="primary"),
        ],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="⚙️ Admin Adda (Boss)", style="danger")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="🎁 Neeche option tap karo ya John Bhai se poocho...",
    )


def quick_actions_inline_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Streamlined quick-action inline buttons in friendly Hinglish."""
    buttons = [
        [
            InlineKeyboardButton(text="🎁 Live Giveaways Dekho 🟢", callback_data="menu_active", style="success"),
            InlineKeyboardButton(text="👥 Dost Bulao Aur Jeeto 🚀", callback_data="menu_referral", style="primary"),
        ],
        [
            InlineKeyboardButton(text="🤖 John Bhai Ke AI Se Poocho ⚡", callback_data="menu_ai_ask", style="primary"),
            InlineKeyboardButton(text="🎟 Secret Code Redeem Karo 🔮", callback_data="user_redeem_code", style="primary"),
        ],
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="⚙️ Admin Control Panel 👑", callback_data="admin_hub", style="danger")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Alias for quick_actions_inline_keyboard."""
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
        nav_row.append(InlineKeyboardButton(text="◀️ Peeche", callback_data=f"{prefix}_page_{page - 1}", style="primary"))
    nav_row.append(InlineKeyboardButton(text=f"📄 Page {page}/{max(1, total_pages)}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Aage ▶️", callback_data=f"{prefix}_page_{page + 1}", style="primary"))

    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="🔙 Main Menu Pe Wapas", callback_data="back_to_main", style="primary")])
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
            InlineKeyboardButton(text="🎟️ GIVEAWAY ME ENTER KARO 🚀", callback_data=f"gw_join_{giveaway_id}", style="success")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="👥 Dost Bulao (+Extra Ticket)", callback_data="menu_referral", style="primary"),
            InlineKeyboardButton(text="📊 Meri Tickets Dekho", callback_data=f"gw_stats_{giveaway_id}", style="primary"),
        ])

    buttons.append([
        InlineKeyboardButton(text="📜 Niyam & Rules", callback_data=f"gw_rules_{giveaway_id}", style="primary"),
        InlineKeyboardButton(text="🔙 Saare Giveaways", callback_data="menu_active", style="primary"),
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
        text = f"👉 Join Karo: {req.title} 📢"
        if link:
            buttons.append([InlineKeyboardButton(text=text, url=link, style="primary")])

    buttons.append([
        InlineKeyboardButton(text="🔄 Join Kar Liya, Check Karo! ⚡", callback_data=f"gw_join_{giveaway_id}", style="success"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Wapas", callback_data=f"gw_view_{giveaway_id}", style="danger"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def referral_share_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """Vibrant social share keyboard."""
    share_url = f"https://t.me/share/url?url={referral_link}&text=Bhai%20John's%20Giveaway%20Bot%20join%20karo%20aur%20free%20prizes%20jeeto!"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📤 Dosto Ko Link Bhejo 🚀", url=share_url, style="success"),
            ],
            [
                InlineKeyboardButton(text="🔙 Main Menu Pe Wapas", callback_data="back_to_main", style="primary"),
            ],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Standard back button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Main Menu Pe Wapas", callback_data="back_to_main", style="primary")]
        ]
    )
