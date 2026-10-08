"""Giveaway winners display and historical audit handlers."""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.database import get_session
from database.repositories import GiveawayRepository, WinnerRepository
from keyboards.user import back_to_menu_keyboard
from utils.formatting import format_winners_card

logger = logging.getLogger(__name__)
router = Router(name="winners")


@router.message(Command("winners"))
@router.callback_query(F.data.in_(["menu_winners", "menu_history"]))
async def handle_winners_list(event: Message | CallbackQuery) -> None:
    """Display recently ended giveaways and their official winners."""
    async with get_session() as session:
        giveaway_repo = GiveawayRepository(session)
        ended_giveaways = await giveaway_repo.get_ended_giveaways(limit=10)

    if not ended_giveaways:
        text = (
            "🏆 <b>GIVEAWAY WINNERS & ARCHIVE</b>\n\n"
            "<i>No giveaways have concluded yet! Check back once our active giveaways finish.</i>"
        )
        keyboard = back_to_menu_keyboard()
    else:
        text = (
            "🏆 <b>RECENT CONCLUDED GIVEAWAYS</b>\n\n"
            "Select a giveaway below to view the official drawn winners and cryptographic audit hashes:"
        )
        buttons = []
        for gw in ended_giveaways:
            buttons.append([
                InlineKeyboardButton(
                    text=f"🏁 {gw.title} ({gw.prize})",
                    callback_data=f"winners_view_{gw.id}",
                )
            ])
        buttons.append([InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(event, CallbackQuery):
        if event.message:
            try:
                await event.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                await event.message.answer(text=text, parse_mode="HTML", reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text=text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("winners_view_"))
async def handle_winners_detail(callback: CallbackQuery) -> None:
    """View official winners list for a specific ended giveaway."""
    giveaway_id = int(callback.data.split("_")[2])

    async with get_session() as session:
        giveaway_repo = GiveawayRepository(session)
        winner_repo = WinnerRepository(session)

        giveaway = await giveaway_repo.get_by_id(giveaway_id)
        if not giveaway:
            await callback.answer("Giveaway not found.", show_alert=True)
            return

        winners = await winner_repo.get_for_giveaway(giveaway_id)

    text = format_winners_card(giveaway, winners)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 All Concluded Giveaways", callback_data="menu_winners")],
            [InlineKeyboardButton(text="🔙 Main Hub", callback_data="back_to_main")],
        ]
    )

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
