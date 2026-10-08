"""Referral and viral growth program handlers."""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database.database import get_session
from services.referral_service import ReferralService
from keyboards.user import referral_share_keyboard

logger = logging.getLogger(__name__)
router = Router(name="referrals")


@router.message(Command("referrals"))
@router.callback_query(F.data == "menu_referral")
async def handle_referrals(event: Message | CallbackQuery) -> None:
    """Display user referral stats and unique invite link."""
    if isinstance(event, CallbackQuery):
        await event.answer()

    user = event.from_user
    if not user:
        return

    async with get_session() as session:
        summary = await ReferralService.get_referral_summary(session, user.id)

    text = (
        "👥 <b>REFER & EARN MORE ENTRIES</b>\n\n"
        "Invite your friends and community members to Giveaway Hub. "
        "For each friend who joins via your link and enters an active giveaway, "
        "you automatically receive bonus entries to boost your odds!\n\n"
        "🔗 <b>Your Unique Referral Link:</b>\n"
        f"<code>{summary['referral_link']}</code>\n\n"
        "📈 <b>Your Referral Performance:</b>\n"
        f"• Total Friends Invited: <b>{summary['total_referrals']}</b>\n"
        f"• Verified & Valid Referrals: <b>{summary['valid_referrals']}</b>\n"
        f"• Bonus Entries Earned: <b>+{summary['bonus_entries']} entries</b>\n\n"
        "<i>Share your link below or copy and paste it into Telegram groups!</i>"
    )

    keyboard = referral_share_keyboard(summary["referral_link"])

    if isinstance(event, CallbackQuery):
        if event.message:
            try:
                await event.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                await event.message.answer(text=text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await event.answer(text=text, parse_mode="HTML", reply_markup=keyboard)
