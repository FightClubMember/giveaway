"""User profile and entry management handlers."""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database.database import get_session
from database.repositories import EntryRepository, GiveawayRepository
from services.giveaway_service import GiveawayService
from keyboards.user import back_to_menu_keyboard
from utils.formatting import format_profile_card

logger = logging.getLogger(__name__)
router = Router(name="profile")


@router.message(Command("profile"))
@router.callback_query(F.data == "menu_profile")
async def handle_profile(event: Message | CallbackQuery) -> None:
    """Display comprehensive user profile and lifetime stats."""
    user = event.from_user
    if not user:
        return

    async with get_session() as session:
        stats = await GiveawayService.get_user_profile(session, user.id)

    text = format_profile_card(stats)
    keyboard = back_to_menu_keyboard()

    if isinstance(event, CallbackQuery):
        if event.message:
            try:
                await event.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                await event.message.answer(text=text, parse_mode="HTML", reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text=text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "menu_entries")
async def handle_my_entries(callback: CallbackQuery) -> None:
    """Show detailed list of active giveaways user has entered."""
    user_id = callback.from_user.id

    async with get_session() as session:
        giveaway_repo = GiveawayRepository(session)
        entry_repo = EntryRepository(session)

        active_giveaways = await giveaway_repo.get_active_giveaways(limit=50)
        lines = [
            "🎟 <b>MY CURRENT GIVEAWAY ENTRIES</b>\n",
            "Here is the breakdown of your tickets in active giveaways:\n",
        ]

        found_any = False
        for gw in active_giveaways:
            user_entries = await entry_repo.get_user_entries_for_giveaway(gw.id, user_id)
            if user_entries > 0:
                found_any = True
                lines.append(f"• <b>{gw.title}</b> ({gw.prize})")
                lines.append(f"  └ Tickets: <b>{user_entries} Entries</b>")
                lines.append("")

        if not found_any:
            lines.append("<i>You haven't joined any active giveaways yet!</i>")
            lines.append("Tap <b>🎁 Active Giveaways</b> in the main hub to enter.")

    keyboard = back_to_menu_keyboard()
    if callback.message:
        await callback.message.edit_text(text="\n".join(lines), parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
