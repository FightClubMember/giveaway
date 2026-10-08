"""Formatting utilities for premium visual layout and UI styling."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from database.models import Giveaway, Winner, User, utcnow


def format_time_remaining(end_time: datetime) -> str:
    """Format remaining time in a clean, human-readable format."""
    now = utcnow()
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    
    if end_time <= now:
        return "Ended"

    diff = end_time - now
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")

    return " ".join(parts)


def format_giveaway_card(
    giveaway: Giveaway,
    participants_count: int,
    user_entries: Optional[int] = None,
    is_joined: bool = False,
    requirements_count: int = 0,
) -> str:
    """Render a clean, high-conversion giveaway card."""
    time_left = format_time_remaining(giveaway.end_time)
    status_emoji = "🟢" if giveaway.status == "active" and time_left != "Ended" else "🔴"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🎁 <b>{giveaway.title.upper()}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 <b>Prize:</b> {giveaway.prize}",
        f"🏆 <b>Winners:</b> {giveaway.winners_count}",
        f"👥 <b>Participants:</b> {participants_count:,}",
        f"⏳ <b>Time Left:</b> {time_left} ({status_emoji} {giveaway.status.capitalize()})",
    ]

    if giveaway.description:
        lines.append("")
        lines.append(f"📝 {giveaway.description}")

    lines.append("")
    lines.append("<b>Entry Rules & Rewards:</b>")
    lines.append(f"• Base Entry: <b>+1 Entry</b>")
    if giveaway.referral_bonus > 0:
        lines.append(f"• Per Referral: <b>+{giveaway.referral_bonus} Entries</b>")
    lines.append(f"• Maximum Cap: <b>{giveaway.max_entries_per_user} Entries</b>")

    if requirements_count > 0:
        lines.append(f"• Mandatory Channels: <b>{requirements_count} required</b>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    if is_joined:
        entries_display = user_entries if user_entries is not None else 1
        lines.append(f"✅ <b>You're in this giveaway!</b> (Your Entries: <b>{entries_display}</b>)")
    else:
        lines.append("⚡ <i>Click the button below to complete requirements and enter!</i>")

    return "\n".join(lines)


def format_winners_card(giveaway: Giveaway, winners: List[Winner]) -> str:
    """Render transparent and official winners list."""
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🏆 <b>OFFICIAL WINNERS: {giveaway.title.upper()}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 <b>Prize:</b> {giveaway.prize}",
        f"🎯 <b>Total Winners Drawn:</b> {len(winners)}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if not winners:
        lines.append("<i>No winners were drawn for this giveaway.</i>")
    else:
        medals = ["🥇", "🥈", "🥉"]
        for idx, w in enumerate(winners):
            rank_icon = medals[idx] if idx < len(medals) else f"<b>#{w.rank}</b>"
            user_display = f"User <code>{w.user_id}</code>"
            if w.user and w.user.username:
                user_display = f"@{w.user.username}"
            elif w.user and w.user.first_name:
                user_display = w.user.first_name

            lines.append(f"{rank_icon} {user_display} — <i>{w.entries_count} entries</i>")

    if winners and winners[0].selection_hash:
        lines.append("")
        lines.append(f"🔐 <b>Audit Hash:</b> <code>{winners[0].selection_hash[:16]}...</code>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def format_profile_card(stats: Dict[str, Any]) -> str:
    """Format modern profile overview."""
    user: User = stats["user"]
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "👤 <b>MY PROFILE</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"<b>Name:</b> {user.full_name}",
        f"<b>Username:</b> @{user.username}" if user.username else "<b>Username:</b> <i>None</i>",
        f"<b>Telegram ID:</b> <code>{user.id}</code>",
        "",
        "📊 <b>Your Activity & Statistics:</b>",
        f"🎟 <b>Total Entries Held:</b> {stats['total_entries']:,}",
        f"🎁 <b>Giveaways Joined:</b> {stats['giveaways_joined']}",
        f"🏆 <b>Giveaways Won:</b> {stats['wins_count']}",
        f"👥 <b>Total Invited:</b> {stats['total_referrals']}",
        f"✅ <b>Valid Referrals:</b> {stats['valid_referrals']}",
        "",
        "🔗 <b>Your Invite Link:</b>",
        f"<code>{stats['referral_link']}</code>",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(lines)


def format_stats_card(stats: Dict[str, Any]) -> str:
    """Format platform-wide statistics for the admin dashboard."""
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📊 <b>PLATFORM ANALYTICS DASHBOARD</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"👥 <b>Total Registered Users:</b> {stats['total_users']:,}",
        f"🎁 <b>Active Giveaways:</b> {stats['active_giveaways']}",
        f"🏁 <b>Completed Giveaways:</b> {stats['ended_giveaways']}",
        f"🎟 <b>Total Entries Accumulated:</b> {stats['total_entries']:,}",
        f"🏆 <b>Total Winners Crowned:</b> {stats['total_winners']:,}",
        f"👥 <b>Valid Referral Actions:</b> {stats['valid_referrals']:,}",
        f"🚫 <b>Banned Accounts:</b> {stats['banned_users']}",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(lines)
