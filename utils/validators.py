"""Input validation and parsing utilities."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from database.models import utcnow


def parse_duration_to_datetime(text: str) -> Optional[datetime]:
    """Parse text duration like '24h', '2d', '30m', '7 days' or date format 'YYYY-MM-DD HH:MM'.
    
    Returns a UTC datetime object or None if invalid.
    """
    text = text.strip().lower()
    now = utcnow()

    # Pattern: 10m, 24h, 3d, 1w
    match = re.match(r"^(\d+)\s*(m|min|minute|minutes|h|hr|hour|hours|d|day|days|w|week|weeks)$", text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)

        if unit in ("m", "min", "minute", "minutes"):
            return now + timedelta(minutes=amount)
        elif unit in ("h", "hr", "hour", "hours"):
            return now + timedelta(hours=amount)
        elif unit in ("d", "day", "days"):
            return now + timedelta(days=amount)
        elif unit in ("w", "week", "weeks"):
            return now + timedelta(weeks=amount)

    # Date format: YYYY-MM-DD HH:MM
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M"):
        try:
            dt = datetime.strptime(text, fmt)
            # Treat as UTC
            dt = dt.replace(tzinfo=timezone.utc)
            if dt > now:
                return dt
        except ValueError:
            continue

    return None


def clean_chat_identifier(text: str) -> str:
    """Clean channel input string (e.g. 'https://t.me/channel' or '@channel')."""
    text = text.strip()
    if text.startswith("https://t.me/"):
        text = "@" + text.replace("https://t.me/", "").rstrip("/")
    elif text.startswith("t.me/"):
        text = "@" + text.replace("t.me/", "").rstrip("/")
    return text
