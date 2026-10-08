"""Giveaways browsing, participation, verification, and daily bonus handlers."""

import logging
import math
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database.database import get_session
from database.repositories import (
    GiveawayRepository,
    ParticipantRepository,
    EntryRepository,
    RequirementRepository,
)
from services.giveaway_service import GiveawayService
from services.notification_service import NotificationService
from keyboards.user import (
    giveaways_pagination_keyboard,
    giveaway_detail_keyboard,
    channel_verification_keyboard,
    back_to_menu_keyboard,
)
from utils.formatting import format_giveaway_card

logger = logging.getLogger(__name__)
router = Router(name="giveaways")
PAGE_SIZE = 5


@router.message(Command("giveaways"))
@router.callback_query(F.data == "menu_active")
async def handle_active_giveaways(event: Message | CallbackQuery) -> None:
    """Display paginated list of active giveaways."""
    if isinstance(event, CallbackQuery):
        await event.answer()
    await render_giveaways_page(event, page=1)


@router.callback_query(F.data.startswith("gw_page_"))
async def handle_giveaway_pagination(callback: CallbackQuery) -> None:
    """Handle page navigation in active giveaways list."""
    await callback.answer()
    page = int(callback.data.split("_")[2])
    await render_giveaways_page(callback, page=page)


async def render_giveaways_page(event: Message | CallbackQuery, page: int = 1) -> None:
    async with get_session() as session:
        giveaway_repo = GiveawayRepository(session)
        total_count = await giveaway_repo.count_active()
        total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
        offset = (page - 1) * PAGE_SIZE

        giveaways = await giveaway_repo.get_active_giveaways(offset=offset, limit=PAGE_SIZE)

    text = (
        "🎁 <b>ACTIVE GIVEAWAYS</b>\n\n"
        f"There are currently <b>{total_count}</b> active giveaways running.\n"
        "Tap a giveaway below to view prizes, requirements, and enter:"
    )
    keyboard = giveaways_pagination_keyboard(giveaways, page=page, total_pages=total_pages)

    if isinstance(event, CallbackQuery):
        if event.message:
            try:
                await event.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                await event.message.answer(text=text, parse_mode="HTML", reply_markup=keyboard)
        try:
            await event.answer()
        except Exception:
            pass
    else:
        await event.answer(text=text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("gw_view_"))
async def handle_view_giveaway(callback: CallbackQuery) -> None:
    """View detailed card for a single giveaway."""
    await callback.answer()
    giveaway_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    async with get_session() as session:
        giveaway_repo = GiveawayRepository(session)
        participant_repo = ParticipantRepository(session)
        entry_repo = EntryRepository(session)
        req_repo = RequirementRepository(session)

        giveaway = await giveaway_repo.get_by_id(giveaway_id)
        if not giveaway:
            await callback.answer("Giveaway not found or expired.", show_alert=True)
            return

        participants_count = await participant_repo.count_for_giveaway(giveaway_id)
        is_joined = await participant_repo.is_participant(giveaway_id, user_id)
        user_entries = await entry_repo.get_user_entries_for_giveaway(giveaway_id, user_id) if is_joined else 0
        requirements = await req_repo.get_for_giveaway(giveaway_id)

    card_text = format_giveaway_card(
        giveaway=giveaway,
        participants_count=participants_count,
        user_entries=user_entries,
        is_joined=is_joined,
        requirements_count=len(requirements),
    )
    keyboard = giveaway_detail_keyboard(
        giveaway_id=giveaway_id,
        is_joined=is_joined,
        user_entries=user_entries,
    )

    if callback.message:
        try:
            await callback.message.edit_text(text=card_text, parse_mode="HTML", reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text=card_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("gw_join_"))
async def handle_join_giveaway(callback: CallbackQuery, bot: Bot) -> None:
    """Process join attempt, channel checks, and entry allocation."""
    giveaway_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    async with get_session() as session:
        result = await GiveawayService.join_giveaway(
            bot=bot,
            session=session,
            giveaway_id=giveaway_id,
            user_id=user_id,
        )

        giveaway_repo = GiveawayRepository(session)
        giveaway = await giveaway_repo.get_by_id(giveaway_id)

    if result.status_code == "MISSING_REQUIREMENTS":
        # Show required channels
        text = (
            "❌ <b>Requirements Incomplete!</b>\n\n"
            "You haven't joined all mandatory community channels yet.\n"
            "Please join the channels listed below and tap <b>Verify Again</b>:"
        )
        keyboard = channel_verification_keyboard(
            giveaway_id=giveaway_id,
            missing_requirements=result.missing_requirements,
        )
        if callback.message:
            await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer("Please join all required channels.", show_alert=True)
        return

    elif result.status_code == "ALREADY_JOINED":
        await callback.answer("You are already entered in this giveaway!", show_alert=True)
        return

    elif not result.success:
        await callback.answer(result.message, show_alert=True)
        return

    # Success!
    if result.referrer_rewarded_id and giveaway:
        # Asynchronously alert the referrer
        await NotificationService.notify_referrer_reward(
            bot=bot,
            referrer_id=result.referrer_rewarded_id,
            giveaway_title=giveaway.title,
            bonus_entries=giveaway.referral_bonus,
        )

    success_text = (
        "🎉 <b>YOU'RE SUCCESSFULLY ENTERED!</b>\n\n"
        f"Giveaway: <b>{giveaway.title if giveaway else 'Giveaway'}</b>\n"
        f"Prize: <b>{giveaway.prize if giveaway else ''}</b>\n\n"
        f"Your Current Entries:\n"
        f"🎟 <b>{result.total_entries} Entry</b>\n\n"
        "💡 <i>Tip: Invite friends with your referral link to multiply your winning chance!</i>"
    )
    keyboard = giveaway_detail_keyboard(
        giveaway_id=giveaway_id,
        is_joined=True,
        user_entries=result.total_entries,
    )

    if callback.message:
        await callback.message.edit_text(text=success_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer("Entry confirmed! 🎉")


@router.callback_query(F.data.startswith("gw_stats_"))
async def handle_giveaway_stats(callback: CallbackQuery) -> None:
    """View granular breakdown of user's entries in a specific giveaway."""
    await callback.answer()
    giveaway_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    async with get_session() as session:
        stats = await GiveawayService.get_user_giveaway_stats(session, giveaway_id, user_id)
        giveaway_repo = GiveawayRepository(session)
        giveaway = await giveaway_repo.get_by_id(giveaway_id)

    title = giveaway.title if giveaway else "Giveaway"
    text = (
        f"📊 <b>YOUR ENTRY STATS: {title.upper()}</b>\n\n"
        f"🎟 <b>Total Entries:</b> {stats['total_entries']}\n\n"
        f"<b>Breakdown:</b>\n"
        f"• Base Entry: <b>+{stats['base_entries']}</b>\n"
        f"• Referral Entries: <b>+{stats['referral_entries']}</b>\n"
        f"• Daily Bonus Entries: <b>+{stats['daily_entries']}</b>\n"
        f"• Special Tasks: <b>+{stats['custom_entries']}</b>\n\n"
        "<i>Every extra entry increases your odds of being chosen by the random draw algorithm!</i>"
    )
    keyboard = giveaway_detail_keyboard(giveaway_id=giveaway_id, is_joined=True, user_entries=stats["total_entries"])

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("gw_rules_"))
async def handle_giveaway_rules(callback: CallbackQuery) -> None:
    """View detailed rules and terms for a giveaway."""
    await callback.answer()
    giveaway_id = int(callback.data.split("_")[2])

    async with get_session() as session:
        giveaway_repo = GiveawayRepository(session)
        giveaway = await giveaway_repo.get_by_id(giveaway_id)

    if not giveaway:
        if callback.message:
            await callback.message.answer("Giveaway not found.")
        return

    rules_content = giveaway.rules or "Standard fair-play rules apply. Duplicate and bot accounts are banned."
    text = (
        f"📜 <b>OFFICIAL RULES & TERMS</b>\n"
        f"<b>{giveaway.title}</b>\n\n"
        f"{rules_content}\n\n"
        f"• Winners Count: <b>{giveaway.winners_count}</b>\n"
        f"• Cap: <b>{giveaway.max_entries_per_user} entries per user</b>\n"
        f"• Draw Type: <b>Weighted Cryptographic Randomness</b>"
    )
    keyboard = giveaway_detail_keyboard(giveaway_id=giveaway_id, is_joined=False)

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "user_daily_bonus")
async def handle_daily_bonus(callback: CallbackQuery) -> None:
    """User taps to claim daily bonus entry."""
    user_id = callback.from_user.id
    async with get_session() as session:
        success, message, _ = await GiveawayService.claim_daily_bonus(session, user_id)

    await callback.answer(message, show_alert=True)
