"""Groq AI interactive assistant handler for John's Giveaway Bot."""

import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.ai_service import GroqAIService
from database.database import get_session
from database.repositories import GiveawayRepository
from keyboards.user import back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="ai_assistant")


class AskAIStates(StatesGroup):
    waiting_for_question = State()


@router.message(Command("ask"))
async def handle_ask_command(message: Message, command: CommandObject) -> None:
    """Direct /ask <question> command powered by Groq AI."""
    user = message.from_user
    if not user:
        return

    query = command.args
    if not query:
        await message.reply(
            "🤖 <b>Ask John's AI:</b>\n\n"
            "Usage: <code>/ask &lt;your question&gt;</code>\n"
            "<i>Example: /ask How do I get more entries in the iPhone giveaway?</i>",
            parse_mode="HTML",
        )
        return

    wait_msg = await message.reply("⚡ <i>John's AI is thinking...</i>", parse_mode="HTML")

    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        active = await gw_repo.get_active_giveaways(limit=3)
        context = ", ".join([f"#{g.id} {g.title} (Prize: {g.prize})" for g in active])

    answer = await GroqAIService.answer_user_query(
        user_name=user.first_name or "Friend",
        query=query,
        context=context,
    )

    await wait_msg.edit_text(answer, parse_mode="HTML", reply_markup=back_to_menu_keyboard())


@router.callback_query(F.data == "menu_ai_ask")
async def start_ask_ai_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to send their question to John's AI."""
    await state.set_state(AskAIStates.waiting_for_question)
    text = (
        "🤖 <b>ASK JOHN'S AI CONCIERGE</b>\n\n"
        "I can help you with anything about <b>John's Giveaway Bot</b>:\n"
        "• How to join and verify channels\n"
        "• How referrals work and maximize winning chances\n"
        "• Prize claiming steps & deadlines\n"
        "• Fairness verification & audit proof\n\n"
        "💬 <i>Please reply with your question below:</i>"
    )
    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.message(AskAIStates.waiting_for_question)
async def process_ai_question(message: Message, state: FSMContext) -> None:
    """Process incoming question using Groq AI."""
    user = message.from_user
    if not user or not message.text:
        return

    await state.clear()
    wait_msg = await message.reply("⚡ <i>John's AI is crafting your answer...</i>", parse_mode="HTML")

    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        active = await gw_repo.get_active_giveaways(limit=3)
        context = ", ".join([f"#{g.id} {g.title} (Prize: {g.prize})" for g in active])

    answer = await GroqAIService.answer_user_query(
        user_name=user.first_name or "Friend",
        query=message.text.strip(),
        context=context,
    )

    await wait_msg.edit_text(answer, parse_mode="HTML", reply_markup=back_to_menu_keyboard())
