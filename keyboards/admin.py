"""Inline keyboards for the Administrator Dashboard and Control Panel."""

from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import GiveawayRequirement, GiveawayStatus


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Master administration panel keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎁 Create Giveaway", callback_data="adm_create_gw"),
                InlineKeyboardButton(text="📋 Manage Giveaways", callback_data="adm_list_gw_1"),
            ],
            [
                InlineKeyboardButton(text="🎨 Poster Studio", callback_data="adm_poster_menu"),
                InlineKeyboardButton(text="✨ AI Copywriter", callback_data="adm_ai_copy"),
            ],
            [
                InlineKeyboardButton(text="🎟 Create Promo Code", callback_data="adm_create_promo"),
                InlineKeyboardButton(text="📊 Platform Stats", callback_data="adm_stats"),
            ],
            [
                InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast"),
                InlineKeyboardButton(text="🏆 Review Claims", callback_data="adm_claims"),
            ],
            [
                InlineKeyboardButton(text="📣 Required Channels", callback_data="adm_channels"),
                InlineKeyboardButton(text="🚫 Ban / Unban User", callback_data="adm_ban_manager"),
            ],
            [
                InlineKeyboardButton(text="📝 Activity Logs", callback_data="adm_logs"),
                InlineKeyboardButton(text="🔙 Return to User Bot", callback_data="back_to_main"),
            ],
        ]
    )


def admin_giveaway_manage_keyboard(giveaway_id: int, status: str) -> InlineKeyboardMarkup:
    """Actions on an individual giveaway inside admin panel."""
    pause_text = "▶️ Resume" if status == GiveawayStatus.PAUSED.value else "⏸ Pause"
    pause_callback = f"adm_resume_{giveaway_id}" if status == GiveawayStatus.PAUSED.value else f"adm_pause_{giveaway_id}"

    buttons = [
        [
            InlineKeyboardButton(text=pause_text, callback_data=pause_callback),
            InlineKeyboardButton(text="🎰 Draw Winners Now (Live)", callback_data=f"adm_draw_{giveaway_id}"),
        ],
        [
            InlineKeyboardButton(text="🎨 Generate Poster", callback_data=f"adm_poster_{giveaway_id}"),
            InlineKeyboardButton(text="✨ AI Promotional Copy", callback_data=f"adm_aicopy_{giveaway_id}"),
        ],
        [
            InlineKeyboardButton(text="📢 Announce to Users", callback_data=f"adm_announce_{giveaway_id}"),
            InlineKeyboardButton(text="📊 Stats & Participants", callback_data=f"adm_gw_stats_{giveaway_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑 Delete Giveaway", callback_data=f"adm_delete_{giveaway_id}"),
            InlineKeyboardButton(text="🔙 Back to List", callback_data="adm_list_gw_1"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_claim_action_keyboard(claim_id: int) -> InlineKeyboardMarkup:
    """Actions to review, approve, or reject a winner claim."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve Claim", callback_data=f"adm_claim_app_{claim_id}"),
                InlineKeyboardButton(text="❌ Reject Claim", callback_data=f"adm_claim_rej_{claim_id}"),
            ],
            [
                InlineKeyboardButton(text="🔄 Request Details", callback_data=f"adm_claim_req_{claim_id}"),
                InlineKeyboardButton(text="🔙 All Claims", callback_data="adm_claims"),
            ],
        ]
    )


def admin_channels_keyboard(channels: List[GiveawayRequirement]) -> InlineKeyboardMarkup:
    """List of configured mandatory channels with remove buttons."""
    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 Remove: {ch.title} ({ch.chat_id})",
                callback_data=f"adm_rm_channel_{ch.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="➕ Add New Channel", callback_data="adm_add_channel")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Admin Hub", callback_data="admin_hub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button during admin form wizards."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel Operation", callback_data="adm_cancel_fsm")]
        ]
    )
