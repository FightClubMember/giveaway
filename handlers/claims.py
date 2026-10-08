"""Winner prize claiming and redemption FSM flow."""

import logging
from datetime import timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import settings
from database.database import get_session
from database.models import ClaimStatus, utcnow
from database.repositories import (
    WinnerRepository,
    WinnerClaimRepository,
    GiveawayRepository,
    UserRepository,
)
from keyboards.admin import admin_claim_action_keyboard
from keyboards.user import back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="claims")


class ClaimStates(StatesGroup):
    waiting_for_details = State()


@router.callback_query(F.data.startswith("claim_"))
async def handle_start_claim(callback: CallbackQuery, state: FSMContext) -> None:
    """Initiate secure prize claim flow for a verified winner."""
    giveaway_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    async with get_session() as session:
        winner_repo = WinnerRepository(session)
        claim_repo = WinnerClaimRepository(session)
        giveaway_repo = GiveawayRepository(session)

        winner = await winner_repo.get_by_giveaway_and_user(giveaway_id, user_id)
        if not winner:
            await callback.answer("❌ You are not recorded as a winner for this giveaway.", show_alert=True)
            return

        existing_claim = await claim_repo.get_by_winner_id(winner.id)
        if existing_claim:
            await callback.answer(
                f"Your claim is currently: {existing_claim.status.upper()}.",
                show_alert=True,
            )
            return

        giveaway = await giveaway_repo.get_by_id(giveaway_id)
        if not giveaway:
            await callback.answer("Giveaway record not found.", show_alert=True)
            return

    # Set state and prompt user
    await state.set_state(ClaimStates.waiting_for_details)
    await state.update_data(winner_id=winner.id, giveaway_id=giveaway_id, giveaway_title=giveaway.title)

    text = (
        f"🎁 <b>CLAIM YOUR PRIZE: {giveaway.title}</b>\n\n"
        f"💰 <b>Prize:</b> {giveaway.prize}\n\n"
        "Please send your delivery or payment details in your next message:\n"
        "• <b>UPI ID / PhonePe / GPay</b> (for INR prizes)\n"
        "• <b>Crypto Address & Network</b> (e.g. USDT TRC20 / TON)\n"
        "• <b>Email or Shipping Address</b> (for vouchers or physical gifts)\n\n"
        "🔒 <i>Your submission is encrypted and only visible to authorized administrators.</i>"
    )

    if callback.message:
        await callback.message.answer(text=text, parse_mode="HTML")
    await callback.answer()


@router.message(ClaimStates.waiting_for_details)
async def handle_submit_claim_details(message: Message, state: FSMContext, bot: Bot) -> None:
    """Receive and store private claim details, then alert admins."""
    user = message.from_user
    if not user or not message.text:
        await message.reply("Please provide your claim details as text.")
        return

    data = await state.get_data()
    winner_id = data.get("winner_id")
    giveaway_id = data.get("giveaway_id")
    giveaway_title = data.get("giveaway_title", "Giveaway")

    claim_data = message.text.strip()
    expires_at = utcnow() + timedelta(hours=settings.CLAIM_WINDOW_HOURS)

    async with get_session() as session:
        claim_repo = WinnerClaimRepository(session)
        claim = await claim_repo.create(
            winner_id=winner_id,
            giveaway_id=giveaway_id,
            user_id=user.id,
            claim_data=claim_data,
            expires_at=expires_at,
        )

        claim_id = claim.id

    await state.clear()

    # Confirm to winner
    await message.reply(
        "✅ <b>Claim Submitted Successfully!</b>\n\n"
        f"Giveaway: <b>{giveaway_title}</b>\n"
        f"Claim ID: <code>#{claim_id}</code>\n"
        "Status: <b>PENDING REVIEW</b>\n\n"
        "Our team will verify your details and deliver your prize shortly. "
        "You will receive a notification as soon as it is processed.",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )

    # Dispatch alert to administrators
    admin_alert = (
        "🏆 <b>NEW PRIZE CLAIM RECEIVED!</b>\n\n"
        f"Claim ID: <code>#{claim_id}</code>\n"
        f"Giveaway: <b>{giveaway_title}</b> (ID: {giveaway_id})\n"
        f"Winner: {user.mention} (<code>{user.id}</code>)\n\n"
        f"📝 <b>Claim Data:</b>\n<code>{claim_data}</code>"
    )

    for admin_id in settings.admin_id_list:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_alert,
                parse_mode="HTML",
                reply_markup=admin_claim_action_keyboard(claim_id=claim_id),
            )
        except Exception as e:
            logger.warning("Could not alert admin %d of claim #%d: %s", admin_id, claim_id, e)
