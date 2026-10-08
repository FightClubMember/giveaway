"""Comprehensive Administration Dashboard and Control Center."""

import asyncio
import logging
import math
from typing import Set, Dict, Any, List, Optional
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import settings
from database.database import get_session
from database.models import GiveawayStatus, ClaimStatus, utcnow
from database.repositories import (
    UserRepository,
    GiveawayRepository,
    RequirementRepository,
    ParticipantRepository,
    EntryRepository,
    WinnerRepository,
    WinnerClaimRepository,
    ReferralRepository,
    AdminLogRepository,
    PromoRepository,
)
from services.winner_service import WinnerService
from services.broadcast_service import BroadcastService
from services.notification_service import NotificationService
from services.ai_service import GroqAIService
from services.poster_service import PosterService
from services.promo_service import PromoService
from keyboards.admin import (
    admin_menu_keyboard,
    admin_giveaway_manage_keyboard,
    admin_claim_action_keyboard,
    admin_channels_keyboard,
    admin_cancel_keyboard,
)
from keyboards.user import main_menu_keyboard
from utils.formatting import format_stats_card, format_time_remaining
from utils.validators import parse_duration_to_datetime, clean_chat_identifier

logger = logging.getLogger(__name__)
router = Router(name="admin")

ADMIN_PAGE_SIZE = 5


# --- FSM STATES ---
class CreateGiveawayFSM(StatesGroup):
    title = State()
    description = State()
    prize = State()
    winners_count = State()
    duration = State()
    referral_bonus = State()
    max_entries = State()
    rules = State()


class BroadcastFSM(StatesGroup):
    message_content = State()
    confirmation = State()


class AddChannelFSM(StatesGroup):
    chat_identifier = State()
    title = State()
    invite_link = State()


class BanUserFSM(StatesGroup):
    user_id = State()
    reason = State()


class CreatePromoFSM(StatesGroup):
    code = State()
    amount = State()
    max_uses = State()


# Runtime administrator cache to prevent initial lockout
RUNTIME_ADMINS: Set[int] = set()

def require_admin(user_id: int) -> bool:
    if settings.is_admin(user_id):
        return True
    if user_id in RUNTIME_ADMINS:
        return True
    # Auto-authorize if placeholder ADMIN_IDS is still active so owner isn't locked out
    if settings.admin_id_list == [123456789] or not settings.admin_id_list:
        RUNTIME_ADMINS.add(user_id)
        logger.info("Auto-authorized first user %d as administrator (placeholder ADMIN_IDS detected)", user_id)
        return True
    return False


@router.message(Command("claimadmin"))
async def handle_claim_admin(message: Message) -> None:
    """Allow bot owner to claim administrator privileges."""
    user = message.from_user
    if not user:
        return
    RUNTIME_ADMINS.add(user.id)
    await message.reply(
        f"👑 <b>Admin Access Granted!</b>\n\n"
        f"Your Telegram ID: <code>{user.id}</code> has been authorized as an administrator for this session.\n\n"
        "👉 To make it permanent on Render, set:\n"
        f"<code>ADMIN_IDS={user.id}</code>\n\n"
        "Tap /admin to access the control panel now!",
        parse_mode="HTML",
    )


# --- DASHBOARD HOME ---
@router.message(Command("admin"))
@router.callback_query(F.data == "admin_hub")
async def handle_admin_dashboard(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Master administration hub overview."""
    user = event.from_user
    if not user:
        return

    # Check permission
    if not require_admin(user.id):
        unauth_text = (
            "👑 <b>ADMIN ACCESS REQUIRED</b>\n\n"
            f"Your Telegram User ID is: <code>{user.id}</code>\n\n"
            "To grant yourself permanent admin access on Render:\n"
            "1. Open <b>Render Dashboard</b> ➔ Your Service ➔ <b>Environment</b>\n"
            f"2. Set <code>ADMIN_IDS={user.id}</code>\n"
            "3. Click <b>Save Changes</b>\n\n"
            "💡 <i>Or type /claimadmin to temporarily claim access right now.</i>"
        )
        if isinstance(event, Message):
            await event.reply(unauth_text, parse_mode="HTML")
        else:
            await event.answer("👑 Admin authorization required. Check message instructions.", show_alert=True)
            if event.message:
                await event.message.answer(unauth_text, parse_mode="HTML")
        return

    await state.clear()
    admin_name = f"@{user.username}" if user.username else (user.full_name or f"Admin #{user.id}")
    text = (
        "⚙️ <b>ADMINISTRATION CONTROL PANEL</b>\n\n"
        f"Welcome, Administrator <b>{admin_name}</b>!\n"
        "Manage active giveaways, inspect analytics, dispatch broadcasts, and review claims."
    )
    keyboard = admin_menu_keyboard()

    if isinstance(event, CallbackQuery):
        if event.message:
            try:
                await event.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                await event.message.answer(text=text, parse_mode="HTML", reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text=text, parse_mode="HTML", reply_markup=keyboard)


# Cancel any active FSM
@router.callback_query(F.data == "adm_cancel_fsm")
async def handle_cancel_fsm(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Operation cancelled.", reply_markup=admin_menu_keyboard())
    await callback.answer("Cancelled")


# --- PLATFORM STATISTICS ---
@router.message(Command("stats"))
@router.callback_query(F.data == "adm_stats")
async def handle_admin_stats(event: Message | CallbackQuery) -> None:
    """Detailed analytics aggregation."""
    user = event.from_user
    if not user or not require_admin(user.id):
        return

    async with get_session() as session:
        user_repo = UserRepository(session)
        gw_repo = GiveawayRepository(session)
        entry_repo = EntryRepository(session)
        winner_repo = WinnerRepository(session)
        ref_repo = ReferralRepository(session)

        stats = {
            "total_users": await user_repo.count_users(),
            "active_giveaways": await gw_repo.count_active(),
            "ended_giveaways": await gw_repo.count_ended(),
            "total_entries": await entry_repo.count_total_all_entries(),
            "total_winners": await winner_repo.count_total_winners(),
            "valid_referrals": await ref_repo.count_all_valid(),
            "banned_users": await user_repo.count_banned_users(),
        }

    text = format_stats_card(stats)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Admin Hub", callback_data="admin_hub")]]
    )

    if isinstance(event, CallbackQuery):
        if event.message:
            await event.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text=text, parse_mode="HTML", reply_markup=keyboard)


# --- CREATE GIVEAWAY WIZARD ---
@router.message(Command("create"))
@router.callback_query(F.data == "adm_create_gw")
async def start_create_giveaway(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Initiate step-by-step giveaway creation."""
    user = event.from_user
    if not user or not require_admin(user.id):
        return

    await state.set_state(CreateGiveawayFSM.title)
    text = (
        "🎁 <b>CREATE NEW GIVEAWAY (Step 1/8)</b>\n\n"
        "Please enter the <b>Title</b> of the giveaway:\n"
        "<i>Example: iPhone 16 Pro Max Giveaway</i>"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, parse_mode="HTML", reply_markup=admin_cancel_keyboard())
        await event.answer()
    else:
        await event.answer(text=text, parse_mode="HTML", reply_markup=admin_cancel_keyboard())


@router.message(CreateGiveawayFSM.title)
async def process_gw_title(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text) < 3:
        await message.reply("Title must be at least 3 characters. Please enter a valid title:")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateGiveawayFSM.description)
    await message.reply(
        "📝 <b>Step 2/8: Description</b>\n\nEnter a short engaging description for participants:",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(CreateGiveawayFSM.description)
async def process_gw_desc(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(CreateGiveawayFSM.prize)
    await message.reply(
        "💰 <b>Step 3/8: Prize Details</b>\n\nEnter the prize description (e.g., <i>₹5,000 Cash UPI</i> or <i>100 USDT</i>):",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(CreateGiveawayFSM.prize)
async def process_gw_prize(message: Message, state: FSMContext) -> None:
    await state.update_data(prize=message.text.strip())
    await state.set_state(CreateGiveawayFSM.winners_count)
    await message.reply(
        "🏆 <b>Step 4/8: Number of Winners</b>\n\nEnter how many winners will be randomly selected (e.g. <i>5</i>):",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(CreateGiveawayFSM.winners_count)
async def process_gw_winners(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit() or int(message.text.strip()) <= 0:
        await message.reply("Please enter a valid positive number for winners count:")
        return
    await state.update_data(winners_count=int(message.text.strip()))
    await state.set_state(CreateGiveawayFSM.duration)
    await message.reply(
        "⏳ <b>Step 5/8: Duration / End Time</b>\n\n"
        "Enter how long the giveaway will run:\n"
        "• Relative: <code>24h</code>, <code>3d</code>, <code>45m</code>\n"
        "• Specific Date (UTC): <code>2026-10-25 18:00</code>",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(CreateGiveawayFSM.duration)
async def process_gw_duration(message: Message, state: FSMContext) -> None:
    end_time = parse_duration_to_datetime(message.text.strip())
    if not end_time:
        await message.reply(
            "⚠️ Invalid duration or date format. Try formats like <code>24h</code> or <code>3d</code>:"
        )
        return
    await state.update_data(end_time=end_time.isoformat())
    await state.set_state(CreateGiveawayFSM.referral_bonus)
    await message.reply(
        "👥 <b>Step 6/8: Referral Bonus Entries</b>\n\n"
        "How many extra entries does a user get per valid referred friend? (e.g. <code>1</code> or <code>2</code>):",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(CreateGiveawayFSM.referral_bonus)
async def process_gw_ref_bonus(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.reply("Please enter an integer (e.g. 1):")
        return
    await state.update_data(referral_bonus=int(message.text.strip()))
    await state.set_state(CreateGiveawayFSM.max_entries)
    await message.reply(
        "🎟 <b>Step 7/8: Maximum Entries Cap</b>\n\n"
        "Maximum entries any single user can accumulate? (e.g. <code>50</code>):",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(CreateGiveawayFSM.max_entries)
async def process_gw_max_entries(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit() or int(message.text.strip()) <= 0:
        await message.reply("Please enter a positive integer (e.g. 50):")
        return
    await state.update_data(max_entries_per_user=int(message.text.strip()))
    await state.set_state(CreateGiveawayFSM.rules)
    await message.reply(
        "📜 <b>Step 8/8: Rules & Notes</b>\n\nEnter rules text, or type <code>skip</code> for standard rules:",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(CreateGiveawayFSM.rules)
async def finish_create_giveaway(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    rules = message.text.strip() if message.text.strip().lower() != "skip" else "Standard community rules apply."
    from datetime import datetime
    end_time = datetime.fromisoformat(data["end_time"])

    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        admin_log_repo = AdminLogRepository(session)

        giveaway = await gw_repo.create(
            title=data["title"],
            description=data["description"],
            prize=data["prize"],
            winners_count=data["winners_count"],
            end_time=end_time,
            referral_bonus=data["referral_bonus"],
            max_entries_per_user=data["max_entries_per_user"],
            rules=rules,
            created_by=message.from_user.id,
        )

        await admin_log_repo.log(
            admin_id=message.from_user.id,
            action="create_giveaway",
            details=f"Created giveaway #{giveaway.id}: {giveaway.title}",
        )

    await state.clear()
    await message.reply(
        f"✅ <b>Giveaway #{giveaway.id} Created Successfully!</b>\n\n"
        f"🎁 <b>Title:</b> {giveaway.title}\n"
        f"💰 <b>Prize:</b> {giveaway.prize}\n"
        f"🏆 <b>Winners:</b> {giveaway.winners_count}\n"
        f"⏳ <b>Ends In:</b> {format_time_remaining(giveaway.end_time)}\n\n"
        "You can now manage, announce, or view this giveaway in the dashboard.",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )


# --- MANAGE GIVEAWAYS ---
@router.callback_query(F.data.startswith("adm_list_gw_"))
async def list_admin_giveaways(callback: CallbackQuery) -> None:
    """Paginated list of giveaways in administration mode."""
    user = callback.from_user
    if not require_admin(user.id):
        return

    page = int(callback.data.split("_")[3])
    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        total_count = await gw_repo.count_active()
        total_pages = max(1, math.ceil(total_count / ADMIN_PAGE_SIZE))
        offset = (page - 1) * ADMIN_PAGE_SIZE
        giveaways = await gw_repo.get_active_giveaways(offset=offset, limit=ADMIN_PAGE_SIZE)

    text = f"📋 <b>GIVEAWAY MANAGER (Page {page}/{total_pages})</b>\n\nSelect a giveaway to control:"
    buttons = []
    for gw in giveaways:
        buttons.append([
            InlineKeyboardButton(
                text=f"🎁 #{gw.id} {gw.title} [{gw.status.upper()}]",
                callback_data=f"adm_manage_{gw.id}",
            )
        ])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"adm_list_gw_{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"adm_list_gw_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="🔙 Back to Admin Hub", callback_data="admin_hub")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_manage_"))
async def manage_single_giveaway(callback: CallbackQuery) -> None:
    """Individual giveaway control card."""
    giveaway_id = int(callback.data.split("_")[2])

    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        part_repo = ParticipantRepository(session)
        entry_repo = EntryRepository(session)

        gw = await gw_repo.get_by_id(giveaway_id)
        if not gw:
            await callback.answer("Giveaway not found.", show_alert=True)
            return

        participants = await part_repo.count_for_giveaway(giveaway_id)
        entries = await entry_repo.count_for_giveaway(giveaway_id)

    text = (
        f"🎁 <b>GIVEAWAY #{gw.id} CONTROL</b>\n\n"
        f"<b>Title:</b> {gw.title}\n"
        f"<b>Status:</b> {gw.status.upper()}\n"
        f"<b>Prize:</b> {gw.prize}\n"
        f"<b>Winners:</b> {gw.winners_count}\n"
        f"<b>Participants:</b> {participants:,}\n"
        f"<b>Total Entries:</b> {entries:,}\n"
        f"<b>Ends:</b> {format_time_remaining(gw.end_time)}"
    )
    keyboard = admin_giveaway_manage_keyboard(giveaway_id=gw.id, status=gw.status)

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_pause_"))
async def handle_pause_giveaway(callback: CallbackQuery) -> None:
    giveaway_id = int(callback.data.split("_")[2])
    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        await gw_repo.update_status(giveaway_id, GiveawayStatus.PAUSED)
    await callback.answer("Giveaway paused ⏸")
    # Refresh single manage view
    callback.data = f"adm_manage_{giveaway_id}"
    await manage_single_giveaway(callback)


@router.callback_query(F.data.startswith("adm_resume_"))
async def handle_resume_giveaway(callback: CallbackQuery) -> None:
    giveaway_id = int(callback.data.split("_")[2])
    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        await gw_repo.update_status(giveaway_id, GiveawayStatus.ACTIVE)
    await callback.answer("Giveaway resumed ▶️")
    callback.data = f"adm_manage_{giveaway_id}"
    await manage_single_giveaway(callback)


@router.callback_query(F.data.startswith("adm_draw_"))
async def handle_manual_draw(callback: CallbackQuery, bot: Bot) -> None:
    """Manually trigger winner selection with thrilling live slot roulette animation."""
    giveaway_id = int(callback.data.split("_")[2])

    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        gw = await gw_repo.get_by_id(giveaway_id)
        if not gw:
            await callback.answer("Giveaway not found.", show_alert=True)
            return

        # Live slot roulette animation
        if callback.message:
            try:
                await callback.message.edit_text("🎰 <b>LUCKY DRAW INITIATED...</b>\n\n[ 🎲 🎲 🎲 ] <i>Gathering entries pool...</i>", parse_mode="HTML")
                await asyncio.sleep(0.8)
                await callback.message.edit_text("🎰 <b>SPINNING WINNER WHEEL...</b>\n\n[ 🍒 7 🔔 ] <i>Applying SHA-256 entropy seed...</i>", parse_mode="HTML")
                await asyncio.sleep(0.8)
                await callback.message.edit_text("🎰 <b>LOCKING WINNERS...</b>\n\n[ 💎 💎 💎 ] <i>Verifying audit hash proofs...</i>", parse_mode="HTML")
                await asyncio.sleep(0.6)
            except Exception:
                pass

        result = await WinnerService.select_winners(session, giveaway_id)

        # Notify drawn winners
        for w in result.winners:
            await NotificationService.notify_winner(
                bot=bot,
                user_id=w.user_id,
                giveaway_id=gw.id,
                giveaway_title=gw.title,
                prize=gw.prize,
                claim_hours=settings.CLAIM_WINDOW_HOURS,
            )

    await callback.answer(f"🎉 Selected {len(result.winners)} winners!", show_alert=True)
    if callback.message:
        await callback.message.edit_text(
            f"🏆 <b>DRAW COMPLETED FOR #{giveaway_id}</b>\n\n"
            f"Winners Drawn: <b>{len(result.winners)}</b>\n"
            f"Total Entries In Pool: <b>{result.total_entries}</b>\n"
            f"Audit Hash: <code>{result.selection_hash[:16]}...</code>\n\n"
            "Winners have been privately notified to claim their rewards.",
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )


# --- POSTER STUDIO & AI GENERATORS ---
@router.callback_query(F.data.startswith("adm_poster_"))
async def handle_generate_poster(callback: CallbackQuery) -> None:
    """Generate high-resolution promotional poster graphic."""
    giveaway_id = int(callback.data.split("_")[2])
    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        gw = await gw_repo.get_by_id(giveaway_id)
        if not gw:
            await callback.answer("Giveaway not found.", show_alert=True)
            return

    await callback.answer("🎨 Rendering HD Poster...")
    time_left = format_time_remaining(gw.end_time)
    poster_bytes = PosterService.generate_giveaway_poster(
        title=gw.title,
        prize=gw.prize,
        winners_count=gw.winners_count,
        time_left=time_left,
    )

    photo_file = BufferedInputFile(poster_bytes.getvalue(), filename=f"poster_gw_{gw.id}.png")
    caption = (
        f"🎨 <b>JOHN'S POSTER STUDIO</b>\n\n"
        f"<b>{gw.title}</b> • <b>{gw.prize}</b>\n"
        "High-definition poster generated on-the-fly for your announcements!"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Giveaway", callback_data=f"adm_manage_{gw.id}")],
        ]
    )
    if callback.message:
        await callback.message.answer_photo(photo=photo_file, caption=caption, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("adm_aicopy_"))
async def handle_ai_copy_giveaway(callback: CallbackQuery) -> None:
    """Generate viral marketing copy via Groq AI."""
    giveaway_id = int(callback.data.split("_")[2])
    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        gw = await gw_repo.get_by_id(giveaway_id)
        if not gw:
            await callback.answer("Giveaway not found.", show_alert=True)
            return

    await callback.answer("⚡ Groq AI is generating copy...")
    copy_text = await GroqAIService.generate_giveaway_copy(
        title=gw.title,
        prize=gw.prize,
        winners_count=gw.winners_count,
        duration=format_time_remaining(gw.end_time),
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Giveaway", callback_data=f"adm_manage_{gw.id}")],
        ]
    )
    if callback.message:
        await callback.message.answer(
            f"✨ <b>GROQ AI PROMOTIONAL COPY:</b>\n\n{copy_text}",
            parse_mode="HTML",
            reply_markup=keyboard,
        )


# --- PROMO CODE GENERATOR WIZARD ---
@router.callback_query(F.data == "adm_create_promo")
async def start_create_promo(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreatePromoFSM.code)
    text = (
        "🎟 <b>CREATE SECRET PROMO CODE (Step 1/3)</b>\n\n"
        "Enter the promo code string (e.g. <code>JOHNBONUS5</code> or <code>VIPWINNER</code>):"
    )
    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.message(CreatePromoFSM.code)
async def process_promo_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip().upper()
    await state.update_data(code=code)
    await state.set_state(CreatePromoFSM.amount)
    await message.reply(
        "🎟 <b>Step 2/3: Bonus Entries Amount</b>\n\nHow many entries should this code award? (e.g. <code>5</code>):",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(CreatePromoFSM.amount)
async def process_promo_amount(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.reply("Please enter a positive integer:")
        return
    await state.update_data(amount=int(message.text.strip()))
    await state.set_state(CreatePromoFSM.max_uses)
    await message.reply(
        "👥 <b>Step 3/3: Max Uses Limit</b>\n\nHow many unique users can redeem this code? (e.g. <code>100</code>):",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(CreatePromoFSM.max_uses)
async def finish_create_promo(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.reply("Please enter a positive integer:")
        return
    data = await state.get_data()
    max_uses = int(message.text.strip())

    async with get_session() as session:
        success, msg = await PromoService.create_code(
            session=session,
            code=data["code"],
            entries_amount=data["amount"],
            max_uses=max_uses,
            created_by=message.from_user.id,
        )

    await state.clear()
    await message.reply(f"✅ {msg}", parse_mode="HTML", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("adm_announce_"))
async def handle_announce_giveaway(callback: CallbackQuery, bot: Bot) -> None:
    """Broadcast an official announcement card for this giveaway to all users."""
    giveaway_id = int(callback.data.split("_")[2])

    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        gw = await gw_repo.get_by_id(giveaway_id)
        if not gw:
            await callback.answer("Giveaway not found.", show_alert=True)
            return

        announcement_text = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎁 <b>MEGA GIVEAWAY ANNOUNCEMENT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 <b>Prize:</b> {gw.prize}\n"
            f"🏆 <b>Winners:</b> {gw.winners_count}\n"
            f"⏳ <b>Ends In:</b> {format_time_remaining(gw.end_time)}\n\n"
            "🎟 <i>Join now and get your chance to win! Join required channels and invite friends for extra tickets.</i>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🎁 JOIN GIVEAWAY NOW", callback_data=f"gw_view_{gw.id}")]]
        )

        b_result = await BroadcastService.send_broadcast(
            bot=bot,
            session=session,
            admin_id=callback.from_user.id,
            text=announcement_text,
            reply_markup=markup,
        )

    await callback.answer(f"Announced! Sent to {b_result.sent} users.", show_alert=True)


@router.callback_query(F.data.startswith("adm_delete_"))
async def handle_delete_giveaway(callback: CallbackQuery) -> None:
    giveaway_id = int(callback.data.split("_")[2])
    async with get_session() as session:
        gw_repo = GiveawayRepository(session)
        await gw_repo.delete_giveaway(giveaway_id)
    await callback.answer(f"Giveaway #{giveaway_id} deleted.")
    callback.data = "adm_list_gw_1"
    await list_admin_giveaways(callback)


# --- REQUIRED CHANNELS MANAGEMENT ---
@router.callback_query(F.data == "adm_channels")
async def handle_manage_channels(callback: CallbackQuery) -> None:
    """Display channels that users are required to join."""
    user = callback.from_user
    if not require_admin(user.id):
        return

    async with get_session() as session:
        req_repo = RequirementRepository(session)
        channels = await req_repo.get_global_requirements()

    text = (
        "📣 <b>MANDATORY TELEGRAM CHANNELS</b>\n\n"
        "Users must be joined in these channels/groups to enter any giveaway.\n"
        "<i>Note: The bot must be added as an Administrator in these channels to verify membership!</i>"
    )
    keyboard = admin_channels_keyboard(channels)

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "adm_add_channel")
async def start_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddChannelFSM.chat_identifier)
    text = (
        "➕ <b>ADD MANDATORY CHANNEL (Step 1/3)</b>\n\n"
        "Enter the channel's <b>@username</b> or <b>Chat ID</b> (e.g. <code>@MyChannel</code> or <code>-1001234567890</code>):"
    )
    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.message(AddChannelFSM.chat_identifier)
async def process_channel_id(message: Message, state: FSMContext) -> None:
    chat_id = clean_chat_identifier(message.text.strip())
    await state.update_data(chat_id=chat_id)
    await state.set_state(AddChannelFSM.title)
    await message.reply(
        "📝 <b>Step 2/3: Channel Display Name</b>\n\nEnter the human-readable title (e.g. <i>Official Announcements</i>):",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(AddChannelFSM.title)
async def process_channel_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(AddChannelFSM.invite_link)
    await message.reply(
        "🔗 <b>Step 3/3: Join Link</b>\n\nEnter the t.me invite link or public URL (or type <code>skip</code> if public @username):",
        parse_mode="HTML",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(AddChannelFSM.invite_link)
async def finish_add_channel(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    invite = message.text.strip() if message.text.strip().lower() != "skip" else None

    async with get_session() as session:
        req_repo = RequirementRepository(session)
        await req_repo.add(
            chat_id=data["chat_id"],
            title=data["title"],
            invite_link=invite,
            is_mandatory=True,
        )

    await state.clear()
    await message.reply("✅ Channel added to mandatory verification list!", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("adm_rm_channel_"))
async def handle_remove_channel(callback: CallbackQuery) -> None:
    req_id = int(callback.data.split("_")[3])
    async with get_session() as session:
        req_repo = RequirementRepository(session)
        await req_repo.remove(req_id)
    await callback.answer("Channel removed.")
    await handle_manage_channels(callback)


# --- WINNER CLAIMS REVIEW ---
@router.callback_query(F.data == "adm_claims")
async def handle_review_claims(callback: CallbackQuery) -> None:
    """View pending winner claims."""
    user = callback.from_user
    if not require_admin(user.id):
        return

    async with get_session() as session:
        claim_repo = WinnerClaimRepository(session)
        claims = await claim_repo.get_pending_claims(limit=10)

    if not claims:
        text = "🏆 <b>PRIZE CLAIMS REVIEW</b>\n\n<i>No pending prize claims at this time!</i>"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Admin Hub", callback_data="admin_hub")]]
        )
    else:
        text = f"🏆 <b>PENDING PRIZE CLAIMS ({len(claims)})</b>\n\nSelect a claim to review and process:"
        buttons = []
        for c in claims:
            buttons.append([
                InlineKeyboardButton(
                    text=f"Claim #{c.id} (User: {c.user_id})",
                    callback_data=f"adm_view_claim_{c.id}",
                )
            ])
        buttons.append([InlineKeyboardButton(text="🔙 Back to Admin Hub", callback_data="admin_hub")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_view_claim_"))
async def handle_view_single_claim(callback: CallbackQuery) -> None:
    claim_id = int(callback.data.split("_")[3])

    async with get_session() as session:
        claim_repo = WinnerClaimRepository(session)
        gw_repo = GiveawayRepository(session)
        user_repo = UserRepository(session)

        claim = await claim_repo.get_by_id(claim_id)
        if not claim:
            await callback.answer("Claim not found.", show_alert=True)
            return

        gw = await gw_repo.get_by_id(claim.giveaway_id)
        user = await user_repo.get_by_id(claim.user_id)

    user_label = user.mention if (user and hasattr(user, 'mention')) else str(claim.user_id)
    text = (
        f"🏆 <b>CLAIM #{claim.id} DETAILS</b>\n\n"
        f"<b>Giveaway:</b> {gw.title if gw else 'N/A'}\n"
        f"<b>Prize:</b> {gw.prize if gw else 'N/A'}\n"
        f"<b>User:</b> {user_label} (<code>{claim.user_id}</code>)\n"
        f"<b>Status:</b> {claim.status.upper()}\n\n"
        f"<b>Claim Info Provided:</b>\n<code>{claim.claim_data}</code>"
    )
    keyboard = admin_claim_action_keyboard(claim_id)

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_claim_app_"))
async def handle_approve_claim(callback: CallbackQuery, bot: Bot) -> None:
    claim_id = int(callback.data.split("_")[3])

    async with get_session() as session:
        claim_repo = WinnerClaimRepository(session)
        claim = await claim_repo.get_by_id(claim_id)
        if claim:
            await claim_repo.update_status(claim_id, ClaimStatus.APPROVED, reviewed_by=callback.from_user.id)
            gw_repo = GiveawayRepository(session)
            gw = await gw_repo.get_by_id(claim.giveaway_id)
            title = gw.title if gw else "Giveaway"

            # Notify user
            await NotificationService.notify_claim_review(
                bot=bot,
                user_id=claim.user_id,
                giveaway_title=title,
                status="approved",
            )

    await callback.answer("Claim APPROVED ✅", show_alert=True)
    await handle_review_claims(callback)


@router.callback_query(F.data.startswith("adm_claim_rej_"))
async def handle_reject_claim(callback: CallbackQuery, bot: Bot) -> None:
    claim_id = int(callback.data.split("_")[3])

    async with get_session() as session:
        claim_repo = WinnerClaimRepository(session)
        claim = await claim_repo.get_by_id(claim_id)
        if claim:
            await claim_repo.update_status(claim_id, ClaimStatus.REJECTED, reviewed_by=callback.from_user.id)
            gw_repo = GiveawayRepository(session)
            gw = await gw_repo.get_by_id(claim.giveaway_id)
            title = gw.title if gw else "Giveaway"

            await NotificationService.notify_claim_review(
                bot=bot,
                user_id=claim.user_id,
                giveaway_title=title,
                status="rejected",
                notes="Details provided were invalid or unverified.",
            )

    await callback.answer("Claim REJECTED ❌", show_alert=True)
    await handle_review_claims(callback)


# --- BROADCAST SYSTEM ---
@router.message(Command("broadcast"))
@router.callback_query(F.data == "adm_broadcast")
async def start_broadcast(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Initiate broadcasting flow."""
    user = event.from_user
    if not user or not require_admin(user.id):
        return

    await state.set_state(BroadcastFSM.message_content)
    text = (
        "📢 <b>GLOBAL BROADCAST COMPOSER</b>\n\n"
        "Send the message (Text, Photo with caption, or HTML formatted message) "
        "that you want to dispatch to all registered users:"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text=text, parse_mode="HTML", reply_markup=admin_cancel_keyboard())
        await event.answer()
    else:
        await event.answer(text=text, parse_mode="HTML", reply_markup=admin_cancel_keyboard())


@router.message(BroadcastFSM.message_content)
async def process_broadcast_content(message: Message, state: FSMContext) -> None:
    text = message.text or message.caption or ""
    photo_id = message.photo[-1].file_id if message.photo else None

    async with get_session() as session:
        user_repo = UserRepository(session)
        recipients_count = len(await user_repo.get_all_active_user_ids())

    await state.update_data(text=text, photo_id=photo_id, recipients=recipients_count)
    await state.set_state(BroadcastFSM.confirmation)

    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 CONFIRM & SEND", callback_data="adm_broadcast_confirm"),
                InlineKeyboardButton(text="❌ CANCEL", callback_data="adm_cancel_fsm"),
            ]
        ]
    )
    await message.reply(
        f"📢 <b>BROADCAST PREVIEW & CONFIRMATION</b>\n\n"
        f"• Recipients Target: <b>{recipients_count:,} users</b>\n"
        f"• Contains Media: <b>{'Yes' if photo_id else 'No'}</b>\n\n"
        "Preview of your text:\n"
        f"<i>{text}</i>\n\n"
        "Are you ready to broadcast?",
        parse_mode="HTML",
        reply_markup=confirm_keyboard,
    )


@router.callback_query(F.data == "adm_broadcast_confirm", BroadcastFSM.confirmation)
async def execute_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()

    if callback.message:
        await callback.message.edit_text("⏳ Broadcasting in progress... Please do not interrupt.")

    async with get_session() as session:
        result = await BroadcastService.send_broadcast(
            bot=bot,
            session=session,
            admin_id=callback.from_user.id,
            text=data["text"],
            photo_id=data["photo_id"],
        )

    summary_text = (
        "✅ <b>BROADCAST COMPLETED!</b>\n\n"
        f"• Total Target: <b>{result.total:,}</b>\n"
        f"• Successfully Delivered: <b>{result.sent:,}</b>\n"
        f"• Blocked / Deactivated: <b>{result.blocked:,}</b>\n"
        f"• Other Failures: <b>{result.failed - result.blocked:,}</b>"
    )
    if callback.message:
        await callback.message.edit_text(text=summary_text, parse_mode="HTML", reply_markup=admin_menu_keyboard())
    await callback.answer("Broadcast finished!")


# --- USER BANNING & UNBANNING ---
@router.message(Command("ban"))
async def handle_ban_command(message: Message) -> None:
    if not message.from_user or not require_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("Usage: <code>/ban &lt;user_id&gt; [reason]</code>", parse_mode="HTML")
        return

    target_id = int(parts[1])
    reason = parts[2] if len(parts) > 2 else "Abuse / Multi-accounting"

    async with get_session() as session:
        user_repo = UserRepository(session)
        admin_log_repo = AdminLogRepository(session)
        banned = await user_repo.set_banned(target_id, is_banned=True, reason=reason)
        if banned:
            await admin_log_repo.log(
                admin_id=message.from_user.id,
                action="ban_user",
                details=f"Banned user {target_id}: {reason}",
            )
            await message.reply(f"🚫 User <code>{target_id}</code> has been banned. Reason: {reason}", parse_mode="HTML")
        else:
            await message.reply("User not found.")


@router.message(Command("unban"))
async def handle_unban_command(message: Message) -> None:
    if not message.from_user or not require_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("Usage: <code>/unban &lt;user_id&gt;</code>", parse_mode="HTML")
        return

    target_id = int(parts[1])
    async with get_session() as session:
        user_repo = UserRepository(session)
        admin_log_repo = AdminLogRepository(session)
        unbanned = await user_repo.set_banned(target_id, is_banned=False)
        if unbanned:
            await admin_log_repo.log(
                admin_id=message.from_user.id,
                action="unban_user",
                details=f"Unbanned user {target_id}",
            )
            await message.reply(f"✅ User <code>{target_id}</code> has been unbanned.", parse_mode="HTML")
        else:
            await message.reply("User not found.")


@router.callback_query(F.data == "adm_ban_manager")
async def handle_ban_manager_callback(callback: CallbackQuery) -> None:
    text = (
        "🚫 <b>USER BAN / UNBAN CONTROLS</b>\n\n"
        "To ban a user, send the command:\n"
        "<code>/ban &lt;user_id&gt; &lt;reason&gt;</code>\n\n"
        "To unban a user, send:\n"
        "<code>/unban &lt;user_id&gt;</code>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Admin Hub", callback_data="admin_hub")]]
    )
    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "adm_logs")
async def handle_view_logs(callback: CallbackQuery) -> None:
    async with get_session() as session:
        admin_log_repo = AdminLogRepository(session)
        logs = await admin_log_repo.get_recent(limit=15)

    if not logs:
        text = "📝 <b>RECENT AUDIT LOGS</b>\n\n<i>No actions logged yet.</i>"
    else:
        lines = ["📝 <b>RECENT AUDIT LOGS</b>\n"]
        for l in logs:
            lines.append(f"• <b>[{l.action}]</b> by <code>{l.admin_id}</code>: {l.details}")
        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Back to Admin Hub", callback_data="admin_hub")]]
    )
    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
