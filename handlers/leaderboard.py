"""Community Leaderboards: Top referrers and entry champions."""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.database import get_session
from database.repositories import LeaderboardRepository
from keyboards.user import back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="leaderboard")

MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


@router.message(Command("leaderboard"))
@router.callback_query(F.data.in_(["menu_leaderboard", "lb_referrals"]))
async def handle_leaderboard_referrals(event: Message | CallbackQuery) -> None:
    """Display top viral referrers."""
    async with get_session() as session:
        lb_repo = LeaderboardRepository(session)
        top_referrers = await lb_repo.get_top_referrers(limit=10)

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "🏆 <b>JOHN'S HALL OF FAME: TOP REFERRERS</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "Our community leaders who have invited the most verified friends:\n",
    ]

    if not top_referrers:
        lines.append("<i>No referral leaders yet! Share your invite link to take the #1 spot!</i>")
    else:
        for idx, (user, count) in enumerate(top_referrers):
            icon = MEDALS[idx] if idx < len(MEDALS) else f"#{idx+1}"
            name = f"@{user.username}" if user.username else user.full_name
            lines.append(f"{icon} <b>{name}</b> — <code>{count:,} valid invites</code>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 <i>Invite friends to climb the leaderboard and unlock exclusive VIP perks!</i>")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎟 View Top Ticket Holders", callback_data="lb_tickets"),
                InlineKeyboardButton(text="👥 My Referral Link", callback_data="menu_referral"),
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main"),
            ],
        ]
    )

    if isinstance(event, CallbackQuery):
        if event.message:
            await event.message.edit_text(text="\n".join(lines), parse_mode="HTML", reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text="\n".join(lines), parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "lb_tickets")
async def handle_leaderboard_tickets(callback: CallbackQuery) -> None:
    """Display top total giveaway entry holders."""
    async with get_session() as session:
        lb_repo = LeaderboardRepository(session)
        top_tickets = await lb_repo.get_top_ticket_holders(limit=10)

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "🎟 <b>TOP TICKET HOLDERS</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "Users with the highest total accumulated giveaway entries:\n",
    ]

    if not top_tickets:
        lines.append("<i>No entries recorded yet. Join active giveaways to be #1!</i>")
    else:
        for idx, (user, count) in enumerate(top_tickets):
            icon = MEDALS[idx] if idx < len(MEDALS) else f"#{idx+1}"
            name = f"@{user.username}" if user.username else user.full_name
            lines.append(f"{icon} <b>{name}</b> — <code>{count:,} tickets</code>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 View Top Referrers", callback_data="lb_referrals"),
                InlineKeyboardButton(text="🔥 Claim Daily Bonus", callback_data="user_daily_bonus"),
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Main Hub", callback_data="back_to_main"),
            ],
        ]
    )

    if callback.message:
        await callback.message.edit_text(text="\n".join(lines), parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
