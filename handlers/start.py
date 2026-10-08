"""Start command, onboarding, and general info handlers in casual, friendly Hinglish."""

import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from config import settings
from database.database import get_session
from database.repositories import UserRepository
from services.referral_service import ReferralService
from services.poster_service import PosterService
from keyboards.user import main_menu_keyboard, main_reply_keyboard, back_to_menu_keyboard, quick_actions_inline_keyboard
from handlers.giveaways import handle_active_giveaways
from handlers.referrals import handle_referrals
from handlers.profile import handle_profile, handle_my_entries
from handlers.leaderboard import handle_leaderboard_referrals
from handlers.admin import handle_admin_dashboard, require_admin
from handlers.ai_assistant import start_ask_ai_flow
from services.giveaway_service import GiveawayService
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)
router = Router(name="start")


WELCOME_TEXT = (
    "🎁 <b>ARRE BHAI! WELCOME TO JOHN'S GIVEAWAY BOT 🔥</b>\n\n"
    "Kya scene hai boss! Ye hai tumhara apna <b>John's Giveaway Hub</b> — jahan free me participate karke "
    "tum jeet sakte ho tagde prizes jaise <b>UPI Cash 💰, Telegram Premium ⭐, Crypto USDT 💎, aur Gaming Passes</b>!\n\n"
    "🚀 <b>Scene Ekdum Simple Hai:</b>\n"
    "• 1-Click me giveaways me enter karo\n"
    "• Dosto ko invite karo aur tickets 10x badhao\n"
    "• Roz ka daily bonus ticket claim karo\n"
    "• 100% fair random lucky draw se jeeto!\n\n"
    "🤖 <i>Kuch samajh na aaye toh neeche <b>🤖 John Bhai Ka AI</b> se direct baat karo!</i>\n\n"
    "Neeche menu buttons pe tap karo aur loot shuru karo 👇"
)

HOW_IT_WORKS_TEXT = (
    "ℹ️ <b>BHAI, YE GIVEAWAY KAISE KAAM KARTA HAI? EK DUM EASY GUIDE:</b>\n\n"
    "<b>1️⃣ Live Giveaway Chunno 🎁</b>\n"
    "Neeche <b>Live Giveaways</b> pe click karo. Wahan dekh lo kitna cash/prize hai aur kitne winners banenge.\n\n"
    "<b>2️⃣ 1-Click Task Karo & Entry Pao 🎟️</b>\n"
    "Sirf partner channels ko join karo aur <b>Check Karo</b> dabao. Tumhara <b>1 Lottery Ticket (Entry)</b> turant confirm ho jayega!\n\n"
    "<b>3️⃣ Apni Jeetne Ki Chance 10x Karo 🚀</b>\n"
    "• <b>Dost Bulao (Referral):</b> Apna link dosto ko bhejo. Har dost ke judne pe tumhe <b>+1 Extra Ticket</b> milegi!\n"
    "• <b>Daily Free Ticket:</b> Roz 24 ghante me aao aur free ticket claim karo bina kisi task ke.\n"
    "• <b>Secret Promo Vouchers:</b> Humare channels me aane wale secret code daalke bonus tickets loot lo!\n\n"
    "<b>4️⃣ 100% Fair Computer Lucky Draw 🎰</b>\n"
    "Time pura hote hi computer algorithm bina kisi cheating ke randomly winners choose karta hai. "
    "Agar tum jeete, bot tumhe instant private alert bhejega aur prize direct tumhare paas!\n\n"
    "🔥 <i>Toh der kis baat ki? Neeche se giveaway join karo abhi!</i>"
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

    is_admin = require_admin(user.id)
    # Send high-definition welcome poster with persistent bottom reply keyboard attached
    try:
        user_display_name = user.first_name or "Bhai"
        poster_io = PosterService.generate_welcome_poster(user_name=user_display_name)
        banner_file = BufferedInputFile(poster_io.getvalue(), filename="welcome_banner.png")
        await message.answer_photo(
            photo=banner_file,
            caption=WELCOME_TEXT,
            parse_mode="HTML",
            reply_markup=main_reply_keyboard(is_admin=is_admin),
        )
    except Exception as e:
        logger.warning("Falling back to text welcome message: %s", e)
        await message.answer(
            text=WELCOME_TEXT,
            parse_mode="HTML",
            reply_markup=main_reply_keyboard(is_admin=is_admin),
        )


# --- REPLY KEYBOARD ROUTERS (Both Hinglish & English Supported) ---
@router.message(F.text.in_(["🎁 Live Giveaways", "🎁 Active Giveaways"]))
async def handle_reply_active_giveaways(message: Message) -> None:
    await handle_active_giveaways(message)


@router.message(F.text.in_(["🎟 Meri Tickets", "🎟 My Entries"]))
async def handle_reply_my_entries(message: Message) -> None:
    await handle_profile(message)


@router.message(F.text.in_(["👥 Dost Bulao (Refer)", "👥 Refer & Earn"]))
async def handle_reply_referrals(message: Message) -> None:
    await handle_referrals(message)


@router.message(F.text.in_(["🏆 Topper List", "🏆 Leaderboard"]))
async def handle_reply_leaderboard(message: Message) -> None:
    await handle_leaderboard_referrals(message)


@router.message(F.text.in_(["🔥 Daily Free Ticket", "🔥 Daily Bonus"]))
async def handle_reply_daily_bonus(message: Message) -> None:
    async with get_session() as session:
        success, msg, _ = await GiveawayService.claim_daily_bonus(session, message.from_user.id)
    # Casual Hinglish response
    if success:
        reply = f"🎉 <b>Badhai ho bhai!</b> {msg}\nKal fir aana aur ek aur free ticket le jaana! 🔥"
    else:
        reply = f"⏳ <b>Arre ruko bhai!</b> {msg}"
    await message.reply(reply, parse_mode="HTML")


@router.message(F.text.in_(["🤖 John Bhai Ka AI", "🤖 Ask John's AI"]))
async def handle_reply_ai(message: Message, state: FSMContext) -> None:
    from handlers.ai_assistant import AskAIStates
    await state.set_state(AskAIStates.waiting_for_question)
    await message.reply(
        "🤖 <b>John Bhai Ka AI Concierge Active Hai!</b>\n\n"
        "Bolo bhai, kya jaanna hai? Bindaas pooch:\n"
        "• <i>Jeetne ka chance kaise badhau?</i>\n"
        "• <i>Dost bulane pe ticket kaise milti hai?</i>\n"
        "• <i>Winners kaise chune jaate hain?</i>\n\n"
        "💬 <i>Apna sawaal neeche type karke bhejo:</i>",
        parse_mode="HTML",
    )


@router.message(F.text.in_(["👤 Meri Profile", "👤 My Profile"]))
async def handle_reply_profile(message: Message) -> None:
    await handle_profile(message)


@router.message(F.text.in_(["ℹ️ Kaise Kaam Karta Hai?", "ℹ️ How It Works"]))
async def handle_reply_guide(message: Message) -> None:
    await handle_guide(message)


@router.message(F.text.in_(["⚙️ Admin Adda (Boss)", "⚙️ Admin Dashboard", "⚙️ Admin Control Center", "⚙️ Admin Panel"]))
async def handle_reply_admin(message: Message, state: FSMContext) -> None:
    await handle_admin_dashboard(message, state)


@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery) -> None:
    """Return user back to the primary hub menu."""
    await callback.answer()
    user = callback.from_user
    is_admin = require_admin(user.id)
    if callback.message:
        try:
            await callback.message.edit_text(
                text=WELCOME_TEXT,
                parse_mode="HTML",
                reply_markup=quick_actions_inline_keyboard(is_admin=is_admin),
            )
        except Exception:
            await callback.message.answer(
                text=WELCOME_TEXT,
                parse_mode="HTML",
                reply_markup=quick_actions_inline_keyboard(is_admin=is_admin),
            )


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
