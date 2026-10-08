"""Formatting utilities for premium visual layout and colorful modern Telegram styling."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from database.models import Giveaway, Winner, User, utcnow


def make_progress_bar(current: int, total: int, length: int = 8) -> str:
    """Render a sleek block progress bar: ▰▰▰▰▰▱▱▱."""
    if total <= 0:
        return "▱" * length
    ratio = min(1.0, max(0.0, current / total))
    filled = int(ratio * length)
    return "▰" * filled + "▱" * (length - filled)


def format_time_remaining(end_time: datetime) -> str:
    """Format remaining time in a clean, human-readable format."""
    now = utcnow()
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    
    if end_time <= now:
        return "Ended 🏁"

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
    """Render a colorful, high-conversion visual card."""
    time_left = format_time_remaining(giveaway.end_time)
    is_live = giveaway.status == "active" and "Ended" not in time_left
    status_badge = "🟢 <b>LIVE NOW</b>" if is_live else "🔴 <b>CLOSED</b>"

    lines = [
        "💎 <b>JOHN'S OFFICIAL GIVEAWAY</b> 💎",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🎁 <b>{giveaway.title.upper()}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 <b>Prize Pool:</b> <code>{giveaway.prize}</code>",
        f"🏆 <b>Total Winners:</b> <b>{giveaway.winners_count}</b>",
        f"👥 <b>Participants:</b> <b>{participants_count:,}</b>",
        f"⏳ <b>Time Left:</b> {time_left} ({status_badge})",
    ]

    if giveaway.description:
        lines.append("")
        lines.append(f"📝 <i>{giveaway.description}</i>")

    lines.append("")
    lines.append("⚡ <b>ENTRY MULTIPLIERS:</b>")
    lines.append("• 🎟️ Base Entry: <b>+1 Ticket</b>")
    if giveaway.referral_bonus > 0:
        lines.append(f"• 👥 Per Referral: <b>+{giveaway.referral_bonus} Bonus Tickets 🚀</b>")
    lines.append(f"• 🔒 Max Entry Cap: <b>{giveaway.max_entries_per_user} Tickets</b>")

    if requirements_count > 0:
        lines.append(f"• 📢 Required Channels: <b>{requirements_count} community task(s)</b>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if is_joined:
        entries_display = user_entries if user_entries is not None else 1
        p_bar = make_progress_bar(entries_display, giveaway.max_entries_per_user)
        lines.append(f"✅ <b>YOU ARE ENTERED!</b>")
        lines.append(f"🎟️ Your Tickets: <b>{entries_display} Entries</b> <code>[{p_bar}]</code>")
    else:
        lines.append("🚀 <i>Tap the button below to complete tasks & claim your free ticket!</i>")

    return "\n".join(lines)


def format_winners_card(giveaway: Giveaway, winners: List[Winner]) -> str:
    """Render transparent and official winners list."""
    lines = [
        "👑 <b>JOHN'S HALL OF WINNERS</b> 👑",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🎁 <b>{giveaway.title.upper()}</b>",
        f"💰 <b>Prize:</b> <code>{giveaway.prize}</code>",
        f"🎯 <b>Total Drawn:</b> {len(winners)} Winner(s)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if not winners:
        lines.append("<i>No winners have been selected yet.</i>")
    else:
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for idx, w in enumerate(winners):
            rank_icon = medals[idx] if idx < len(medals) else f"<b>#{w.rank}</b>"
            user_display = f"User <code>{w.user_id}</code>"
            if w.user and w.user.username:
                user_display = f"@{w.user.username}"
            elif w.user and w.user.first_name:
                user_display = w.user.first_name

            lines.append(f"{rank_icon} {user_display} — 🎟️ <b>{w.entries_count} tickets</b>")

    if winners and winners[0].selection_hash:
        lines.append("")
        lines.append(f"🔐 <b>Cryptographic Proof:</b> <code>{winners[0].selection_hash[:16]}...</code>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def format_profile_card(stats: Dict[str, Any]) -> str:
    """Format modern colorful user profile overview."""
    user: User = stats["user"]
    rank_tier = "💎 VIP Member" if stats["total_entries"] >= 10 else "🌟 Contender"
    p_bar = make_progress_bar(stats["valid_referrals"], 10)

    lines = [
        "╔══════════════════════════════╗",
        f"║   👤 <b>MY ACCOUNT OVERVIEW</b>     ║",
        "╚══════════════════════════════╝",
        f"<b>Name:</b> {user.full_name}",
        f"<b>Username:</b> @{user.username}" if user.username else "<b>Username:</b> <i>None</i>",
        f"<b>User ID:</b> <code>{user.id}</code>",
        f"<b>Status:</b> {rank_tier}",
        "",
        "📊 <b>YOUR STATS & TICKETS:</b>",
        f"🎟️ <b>Total Tickets Held:</b> <b>{stats['total_entries']:,}</b>",
        f"🎁 <b>Giveaways Joined:</b> <b>{stats['giveaways_joined']}</b>",
        f"👑 <b>Giveaways Won:</b> <b>{stats['wins_count']}</b>",
        f"👥 <b>Friends Invited:</b> <b>{stats['total_referrals']}</b>",
        f"✅ <b>Verified Referrals:</b> <b>{stats['valid_referrals']}</b>",
        f"📈 <b>Referral Tier:</b> <code>[{p_bar}]</code>",
        "",
        "🔗 <b>Your Exclusive Viral Invite Link:</b>",
        f"<code>{stats['referral_link']}</code>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(lines)


def format_stats_card(stats: Dict[str, Any]) -> str:
    """Format platform-wide analytics dashboard."""
    lines = [
        "╔══════════════════════════════╗",
        "║  📊 <b>JOHN'S ANALYTICS HUB</b>    ║",
        "╚══════════════════════════════╝",
        f"👥 <b>Total Users:</b> <code>{stats['total_users']:,}</code>",
        f"🎁 <b>Active Giveaways:</b> <code>{stats['active_giveaways']}</code>",
        f"🏁 <b>Completed Giveaways:</b> <code>{stats['ended_giveaways']}</code>",
        f"🎟️ <b>Total Entries In Circulation:</b> <code>{stats['total_entries']:,}</code>",
        f"👑 <b>Winners Crowned:</b> <code>{stats['total_winners']:,}</code>",
        f"👥 <b>Valid Referrals:</b> <code>{stats['valid_referrals']:,}</code>",
        f"🚫 <b>Suspended Accounts:</b> <code>{stats['banned_users']}</code>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(lines)
