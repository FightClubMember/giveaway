"""Promo code and voucher redemption handlers."""

import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.database import get_session
from services.promo_service import PromoService
from keyboards.user import back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="redeem")


class RedeemStates(StatesGroup):
    waiting_for_code = State()


@router.message(Command("redeem"))
async def handle_redeem_command(message: Message, command: CommandObject) -> None:
    """Direct /redeem <code> command."""
    user = message.from_user
    if not user:
        return

    code = command.args
    if not code:
        await message.reply(
            "🎟 <b>REDEEM PROMO CODE:</b>\n\n"
            "Usage: <code>/redeem &lt;code&gt;</code>\n"
            "<i>Example: /redeem JOHNBONUS5</i>\n\n"
            "Watch our official announcements channel to grab limited promo drops!",
            parse_mode="HTML",
        )
        return

    async with get_session() as session:
        success, reply_text, _ = await PromoService.redeem_code(session, code.strip(), user.id)

    await message.reply(reply_text, parse_mode="HTML", reply_markup=back_to_menu_keyboard())


@router.callback_query(F.data == "user_redeem_code")
async def start_redeem_code_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """Interactive button to prompt for secret promo code."""
    await state.set_state(RedeemStates.waiting_for_code)
    text = (
        "🎟 <b>REDEEM PROMO CODE</b>\n\n"
        "Got a secret voucher or community promo code from John's announcements?\n\n"
        "Enter your code in your next message to claim free extra entries!"
    )
    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.message(RedeemStates.waiting_for_code)
async def process_redeem_code(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if not user or not message.text:
        return

    await state.clear()
    code = message.text.strip()

    async with get_session() as session:
        success, reply_text, _ = await PromoService.redeem_code(session, code, user.id)

    await message.reply(reply_text, parse_mode="HTML", reply_markup=back_to_menu_keyboard())
