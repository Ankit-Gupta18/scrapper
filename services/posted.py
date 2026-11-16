"""Turns the heterogeneous `posted_date` values scrapers return (ISO strings, epoch seconds or
milliseconds, 'Posted 3 Days Ago', '11/05/2026', ...) into one readable string in IST.
Returns None when a site gives no usable value, so the email can say so instead of guessing."""
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
_RELATIVE = re.compile(r"posted\s+(today|yesterday|(\d+)\+?\s*days?\s+ago)", re.I)
_NAIVE_FORMATS = (
    ("%Y-%m-%d %I:%M %p", True),        # 2026-11-09 12:21 PM
    ("%Y-%m-%d %H:%M:%S", True),
    ("%Y-%m-%dT%H:%M:%S", True),
    ("%m/%d/%Y", False),                # Zoho Recruit
    ("%d %b %Y", False),                # 3 Nov 2026 (SuccessFactors)
    ("%d %B %Y", False),
    ("%b %d, %Y", False),
    ("%Y-%m-%d", False),
)


def _fmt(dt: datetime, with_time: bool, tz_label: str = "") -> str:
    text = dt.strftime("%d %b %Y, %I:%M %p") if with_time else dt.strftime("%d %b %Y")
    return f"{text} {tz_label}".strip()


def _ago(dt: datetime, now: Optional[datetime]) -> str:
    """'25 min ago' / '3 hr 10 min ago' / '2 days ago' for a timezone-aware timestamp."""
    minutes = int(((now or datetime.now(timezone.utc)) - dt).total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    if minutes < 24 * 60:
        hours, mins = divmod(minutes, 60)
        return f"{hours} hr {mins} min ago" if mins else f"{hours} hr ago"
    days = minutes // (24 * 60)
    return f"{days} day{'s' if days != 1 else ''} ago"


def _exact(dt: datetime, now: Optional[datetime]) -> str:
    """Absolute IST time-stamp with how long ago it was, e.g. '25 min ago (16 Nov 2026, 09:10 PM IST)'."""
    return f"{_ago(dt, now)} ({_fmt(dt.astimezone(IST), True, 'IST')})"


def _from_epoch(value: float, now: Optional[datetime] = None) -> Optional[str]:
    if value > 1e14:      # microseconds
        value /= 1e6
    elif value > 1e11:    # milliseconds
        value /= 1e3
    if value < 1e9:       # not a plausible timestamp
        return None
    return _exact(datetime.fromtimestamp(value, tz=timezone.utc), now)


def _from_iso(text: str, now: Optional[datetime] = None) -> Optional[str]:
    iso = text.strip()
    if iso.endswith(("Z", "z")):
        iso = iso[:-1] + "+00:00"
    iso = re.sub(r"(\.\d{6})\d+", r"\1", iso)          # >6 fractional digits
    iso = re.sub(r"\.(\d{1,5})(?=[+-]|$)", lambda m: "." + m.group(1).ljust(6, "0"), iso)
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    has_time = "T" in iso or " " in iso
    if dt.tzinfo:
        if has_time:
            return _exact(dt, now)
        return _fmt(dt.astimezone(IST), False)
    return _fmt(dt, has_time)


def format_posted(raw: Any, now: Optional[datetime] = None) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in ("0", "none", "null", "nan"):
        return None

    try:
        return _from_epoch(float(text), now)
    except ValueError:
        pass

    rel = _RELATIVE.search(text)
    if rel:
        today = (now or datetime.now(IST)).astimezone(IST).date()
        kind = rel.group(1).lower()
        if kind == "today":
            return f"{today.strftime('%d %b %Y')} (today)"
        if kind == "yesterday":
            return f"{(today - timedelta(days=1)).strftime('%d %b %Y')} (yesterday)"
        days = int(rel.group(2))
        if "+" in rel.group(1):
            return f"over {days} days ago"
        return f"{(today - timedelta(days=days)).strftime('%d %b %Y')} ({days} days ago)"

    iso = _from_iso(text, now)
    if iso:
        return iso
    for fmt, with_time in _NAIVE_FORMATS:
        try:
            return _fmt(datetime.strptime(text, fmt), with_time)
        except ValueError:
            continue
    return None
