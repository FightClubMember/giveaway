"""Winner prize claiming, trust confirmation, and admin approval report flow in friendly Hinglish."""

import logging
from datetime import timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import settings
from database.database import get_session
from database.models import ClaimStatus, utcnow
from database.repositories import (
    WinnerRepository,
    WinnerClaimRepository,
    GiveawayRepository,
)
from keyboards.styled_buttons import InlineKeyboardButton
from keyboards.admin import admin_claim_action_keyboard
from keyboards.user import back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="claims")


class ClaimStates(StatesGroup):
    waiting_for_details = State()


@router.callback_query(F.data.startswith("claim_") & ~F.data.startswith("claim_trust_"))
async def handle_start_claim(callback: CallbackQuery) -> None:
    """Step 1: Winner clicks 'Claim Prize'. Show trust question first."""
    await callback.answer()
    giveaway_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    async with get_session() as session:
        winner_repo = WinnerRepository(session)
        claim_repo = WinnerClaimRepository(session)
        giveaway_repo = GiveawayRepository(session)

        winner = await winner_repo.get_by_giveaway_and_user(giveaway_id, user_id)
        if not winner:
            await callback.answer("❌ Bhai aap is giveaway ke winner record me nahi ho.", show_alert=True)
            return

        existing_claim = await claim_repo.get_by_winner_id(winner.id)
        if existing_claim:
            status_text = "APPROVED ✅" if existing_claim.status == ClaimStatus.APPROVED.value else "PENDING REVIEW ⏳"
            await callback.answer(f"Aapka claim status: {status_text}", show_alert=True)
            return

        giveaway = await giveaway_repo.get_by_id(giveaway_id)
        if not giveaway:
            await callback.answer("Giveaway nahi mila.", show_alert=True)
            return

    # Render Trust & Confirmation card
    text = (
        f"🏆 <b>BADHAI HO BHAI! YOU WON!</b> 🎉\n\n"
        f"🎁 <b>Giveaway:</b> {giveaway.title}\n"
        f"💰 <b>Prize:</b> {giveaway.prize}\n\n"
        "🛡️ <b>Trust & Fairness Verification:</b>\n"
        "Prize claim karne se pehle confirm karein:\n"
        "<b>Kya ye giveaway aapko 100% fair, transparent aur trusted laga?</b>\n\n"
        "Neeche button dabakar apna reward claim karein 👇"
    )

    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Yes, 100% Trusted & Fair! Claim Karo 🚀",
                callback_data=f"claim_trust_yes_{giveaway_id}",
                style="success",
            )
        ],
        [
            InlineKeyboardButton(
                text="ℹ️ Help / Support Chahiye",
                callback_data="menu_guide",
                style="primary",
            )
        ],
    ]

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("claim_trust_yes_"))
async def handle_trust_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2: User confirmed trust. Prompt for payment/shipping details."""
    await callback.answer()
    giveaway_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id

    async with get_session() as session:
        winner_repo = WinnerRepository(session)
        giveaway_repo = GiveawayRepository(session)

        winner = await winner_repo.get_by_giveaway_and_user(giveaway_id, user_id)
        giveaway = await giveaway_repo.get_by_id(giveaway_id)

    if not winner or not giveaway:
        await callback.answer("Record nahi mila.", show_alert=True)
        return

    await state.set_state(ClaimStates.waiting_for_details)
    await state.update_data(
        winner_id=winner.id,
        giveaway_id=giveaway_id,
        giveaway_title=giveaway.title,
        giveaway_prize=giveaway.prize,
    )

    text = (
        f"📝 <b>SUBMIT DETAILS TO RECEIVE PRIZE</b>\n\n"
        f"🎁 Giveaway: <b>{giveaway.title}</b>\n"
        f"💰 Prize: <b>{giveaway.prize}</b>\n\n"
        "Bhai apni delivery ya payment details neeche message me type karke bhejo:\n"
        "• <b>UPI ID / PhonePe / GPay</b> (Cash prize ke liye: jaise <code>9876543210@paytm</code>)\n"
        "• <b>Crypto Wallet Address & Network</b> (USDT TRC20 / TON / BEP20)\n"
        "• <b>Telegram Username ya Email</b> (Premium / Vouchers ke liye)\n"
        "• <b>Delivery Address & Phone</b> (Physical gift ke liye)\n\n"
        "🔒 <i>Details encrypted hain aur direct Admin Boss ke paas approval ke liye jaayengi!</i>"
    )

    if callback.message:
        await callback.message.answer(text=text, parse_mode="HTML")


@router.message(ClaimStates.waiting_for_details)
async def handle_submit_claim_details(message: Message, state: FSMContext, bot: Bot) -> None:
    """Step 3: Save claim and alert all admins with full report notification."""
    user = message.from_user
    if not user or not message.text:
        await message.reply("Bhai kripya apni details text message me type karke bhejein.")
        return

    data = await state.get_data()
    winner_id = data.get("winner_id")
    giveaway_id = data.get("giveaway_id")
    giveaway_title = data.get("giveaway_title", "Giveaway")
    giveaway_prize = data.get("giveaway_prize", "Prize")

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

    # Friendly Hinglish Confirmation to winner
    await message.reply(
        "🎉 <b>CLAIM DETAILS SUBMITTED SUCCESSFULLY!</b>\n\n"
        f"🎁 <b>Giveaway:</b> {giveaway_title}\n"
        f"💰 <b>Prize:</b> {giveaway_prize}\n"
        f"📋 <b>Claim ID:</b> <code>#{claim_id}</code>\n"
        f"⏳ <b>Status:</b> <b>WAITING FOR ADMIN APPROVAL</b>\n\n"
        "Bhai Admin Boss ko full report notification bhej di gayi hai! "
        "Jaise hi Admin aapka prize verify karke dispatch karega, aapko yahan instant notification mil jayega! 🔥",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )

    # Dispatch FULL REPORT NOTIFICATION to all admins
    from handlers.admin import RUNTIME_ADMINS
    all_admins = set(settings.admin_id_list) | RUNTIME_ADMINS

    winner_name = f"@{user.username}" if user.username else (user.full_name or f"User #{user.id}")
    admin_alert = (
        "🚨 <b>FULL PRIZE CLAIM REPORT & NOTIFICATION!</b> 🏆\n\n"
        f"📋 <b>Claim ID:</b> <code>#{claim_id}</code>\n"
        f"🎁 <b>Giveaway:</b> <b>{giveaway_title}</b> (ID: {giveaway_id})\n"
        f"💰 <b>Prize:</b> <b>{giveaway_prize}</b>\n"
        f"👤 <b>Winner:</b> {winner_name} (ID: <code>{user.id}</code>)\n"
        f"⭐ <b>Trust Feedback:</b> 100% Confirmed & Trusted ✅\n"
        f"⏳ <b>Status:</b> PENDING ADMIN APPROVAL\n\n"
        f"📝 <b>Winner's Submitted Details:</b>\n"
        f"<code>{claim_data}</code>\n\n"
        "Neeche buttons se approve ya reject karo:"
    )

    for admin_id in all_admins:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_alert,
                parse_mode="HTML",
                reply_markup=admin_claim_action_keyboard(claim_id=claim_id),
            )
        except Exception as e:
            logger.warning("Could not alert admin %d of claim #%d: %s", admin_id, claim_id, e)
