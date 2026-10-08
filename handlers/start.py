"""Start command, onboarding, and general info handlers."""

import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery

from config import settings
from database.database import get_session
from database.repositories import UserRepository
from services.referral_service import ReferralService
from keyboards.user import main_menu_keyboard, back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="start")


WELCOME_TEXT = (
    "🎁 <b>JOHN'S GIVEAWAY BOT</b>\n\n"
    "Welcome to <b>John's Giveaway Bot</b> — the premier AI-powered community giveaway platform!\n"
    "Participate in verified giveaways, complete instant community tasks, "
    "multiply your entries with referrals & promo codes, and win real cash, crypto, and gadget prizes.\n\n"
    "🤖 <i>Need help? Tap <b>Ask John's AI</b> anytime to get instant answers!</i>\n"
    "✨ <i>Select an option below to get started:</i>"
)

HOW_IT_WORKS_TEXT = (
    "ℹ️ <b>HOW JOHN'S GIVEAWAY BOT WORKS</b>\n\n"
    "<b>1. Browse Active Giveaways</b>\n"
    "Explore open giveaways and review the prize, winners count, and rules.\n\n"
    "<b>2. Join & Verify Tasks</b>\n"
    "Tap 'Join Giveaway' and join our partner Telegram channels/groups. "
    "Our system verifies your membership in real-time.\n\n"
    "<b>3. Earn Multiplier Entries</b>\n"
    "• <b>Base Entry:</b> +1 entry upon joining.\n"
    "• <b>Referral Bonus:</b> Invite friends with your unique link for extra tickets!\n"
    "• <b>Daily Bonus:</b> Claim a free daily bonus entry every 24 hours.\n"
    "• <b>Promo Codes:</b> Redeem secret codes from our community channels for bonus tickets!\n\n"
    "<b>4. Fair Cryptographic Draw</b>\n"
    "When a giveaway ends, our automated cryptographic algorithm fairly selects "
    "winners proportional to tickets held. Winners receive a private alert to claim their prize.\n\n"
    "Good luck!"
)


@router.message(CommandStart())
async def handle_start(message: Message, command: CommandObject) -> None:
    """Handle /start and /start ref_<id> referral link arrivals."""
    user = message.from_user
    if not user:
        return

    async with get_session() as session:
        is_new, referrer_id = await ReferralService.process_referral_start(
            session=session,
            user_id=user.id,
            raw_start_param=command.args,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        if is_new and referrer_id:
            logger.info("New user %d registered via referral from %d", user.id, referrer_id)

    is_admin = settings.is_admin(user.id)
    await message.answer(
        text=WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(is_admin=is_admin),
    )


@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery) -> None:
    """Return user back to the primary hub menu."""
    user = callback.from_user
    is_admin = settings.is_admin(user.id)
    if callback.message:
        try:
            await callback.message.edit_text(
                text=WELCOME_TEXT,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(is_admin=is_admin),
            )
        except Exception:
            await callback.message.answer(
                text=WELCOME_TEXT,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(is_admin=is_admin),
            )
    await callback.answer()


@router.message(Command("help"))
@router.callback_query(F.data == "menu_guide")
async def handle_guide(event: Message | CallbackQuery) -> None:
    """Display platform instructions and user guide."""
    if isinstance(event, CallbackQuery):
        if event.message:
            await event.message.edit_text(
                text=HOW_IT_WORKS_TEXT,
                parse_mode="HTML",
                reply_markup=back_to_menu_keyboard(),
            )
        await event.answer()
    else:
        await event.answer(
            text=HOW_IT_WORKS_TEXT,
            parse_mode="HTML",
            reply_markup=back_to_menu_keyboard(),
        )
