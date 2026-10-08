"""Inline keyboards for the Administrator Dashboard and Control Panel with API 9.4 styling."""

from typing import List
from aiogram.types import InlineKeyboardMarkup
from keyboards.styled_buttons import InlineKeyboardButton
from database.models import GiveawayRequirement, GiveawayStatus


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Master administration panel keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎁 Create Giveaway", callback_data="adm_create_gw", style="success"),
                InlineKeyboardButton(text="📋 Manage Giveaways", callback_data="adm_list_gw_1", style="primary"),
            ],
            [
                InlineKeyboardButton(text="🎨 Poster Studio", callback_data="adm_poster_menu", style="primary"),
                InlineKeyboardButton(text="✨ AI Copywriter", callback_data="adm_ai_copy", style="primary"),
            ],
            [
                InlineKeyboardButton(text="🎟 Create Promo Code", callback_data="adm_create_promo", style="primary"),
                InlineKeyboardButton(text="📊 Platform Stats", callback_data="adm_stats", style="primary"),
            ],
            [
                InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast", style="primary"),
                InlineKeyboardButton(text="🏆 Review Claims", callback_data="adm_claims", style="success"),
            ],
            [
                InlineKeyboardButton(text="📣 Required Channels", callback_data="adm_channels", style="primary"),
                InlineKeyboardButton(text="🚫 Ban / Unban User", callback_data="adm_ban_manager", style="danger"),
            ],
            [
                InlineKeyboardButton(text="📝 Activity Logs", callback_data="adm_logs", style="primary"),
                InlineKeyboardButton(text="🔙 Return to User Bot", callback_data="back_to_main", style="primary"),
            ],
        ]
    )


def admin_giveaway_manage_keyboard(giveaway_id: int, status: str) -> InlineKeyboardMarkup:
    """Actions on an individual giveaway inside admin panel."""
    pause_text = "▶️ Resume" if status == GiveawayStatus.PAUSED.value else "⏸ Pause"
    pause_callback = f"adm_resume_{giveaway_id}" if status == GiveawayStatus.PAUSED.value else f"adm_pause_{giveaway_id}"

    buttons = [
        [
            InlineKeyboardButton(text=pause_text, callback_data=pause_callback, style="primary"),
            InlineKeyboardButton(text="🎰 Draw Winners Now (Live)", callback_data=f"adm_draw_{giveaway_id}", style="success"),
        ],
        [
            InlineKeyboardButton(text="🎨 Generate Poster", callback_data=f"adm_poster_{giveaway_id}", style="primary"),
            InlineKeyboardButton(text="✨ AI Promotional Copy", callback_data=f"adm_aicopy_{giveaway_id}", style="primary"),
        ],
        [
            InlineKeyboardButton(text="🎁 Set Secret Reward / Claim Type", callback_data=f"adm_reward_{giveaway_id}", style="success"),
            InlineKeyboardButton(text="📊 Stats & Participants", callback_data=f"adm_gw_stats_{giveaway_id}", style="primary"),
        ],
        [
            InlineKeyboardButton(text="📢 Announce to Users", callback_data=f"adm_announce_{giveaway_id}", style="primary"),
            InlineKeyboardButton(text="🗑 Delete Giveaway", callback_data=f"adm_delete_{giveaway_id}", style="danger"),
        ],
        [
            InlineKeyboardButton(text="🔙 Back to List", callback_data="adm_list_gw_1", style="primary"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_claim_action_keyboard(claim_id: int) -> InlineKeyboardMarkup:
    """Actions to review, approve, or reject a winner claim."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve Claim", callback_data=f"adm_claim_app_{claim_id}", style="success"),
                InlineKeyboardButton(text="❌ Reject Claim", callback_data=f"adm_claim_rej_{claim_id}", style="danger"),
            ],
            [
                InlineKeyboardButton(text="🔄 Request Details", callback_data=f"adm_claim_req_{claim_id}", style="primary"),
                InlineKeyboardButton(text="🔙 All Claims", callback_data="adm_claims", style="primary"),
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
                style="danger",
            )
        ])
    buttons.append([InlineKeyboardButton(text="➕ Add New Channel", callback_data="adm_add_channel", style="success")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Admin Hub", callback_data="admin_hub", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_reward_options_keyboard(giveaway_id: int) -> InlineKeyboardMarkup:
    """Options for setting secret reward or custom claim instructions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔑 Set Instant Redeem Code / Link", callback_data=f"adm_setcode_{giveaway_id}", style="success"),
            ],
            [
                InlineKeyboardButton(text="✍️ Set Custom Claim Question/Prompt", callback_data=f"adm_setprompt_{giveaway_id}", style="primary"),
            ],
            [
                InlineKeyboardButton(text="🔄 Switch to Manual Approval", callback_data=f"adm_setmanual_{giveaway_id}", style="primary"),
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Giveaway Control", callback_data=f"adm_manage_{giveaway_id}", style="primary"),
            ],
        ]
    )


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button during admin form wizards."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel Operation", callback_data="admin_cancel", style="danger")]
        ]
    )
