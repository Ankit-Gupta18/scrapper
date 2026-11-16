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


def _from_epoch(value: float) -> Optional[str]:
    if value > 1e14:      # microseconds
        value /= 1e6
    elif value > 1e11:    # milliseconds
        value /= 1e3
    if value < 1e9:       # not a plausible timestamp
        return None
    return _fmt(datetime.fromtimestamp(value, tz=timezone.utc).astimezone(IST), True, "IST")


def _from_iso(text: str) -> Optional[str]:
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
        return _fmt(dt.astimezone(IST), has_time, "IST" if has_time else "")
    return _fmt(dt, has_time)


def format_posted(raw: Any, now: Optional[datetime] = None) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in ("0", "none", "null", "nan"):
        return None

    try:
        return _from_epoch(float(text))
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

    iso = _from_iso(text)
    if iso:
        return iso
    for fmt, with_time in _NAIVE_FORMATS:
        try:
            return _fmt(datetime.strptime(text, fmt), with_time)
        except ValueError:
            continue
    return None
