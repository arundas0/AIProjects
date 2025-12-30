# assistant/timeparse.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import dateparser

DEFAULT_TZ = "America/Los_Angeles"

@dataclass
class ParsedWhen:
    dt: datetime
    tz: str
    text: str

def parse_natural_datetime(text: str, tz: str = DEFAULT_TZ, base: datetime | None = None) -> ParsedWhen | None:
    """
    Parse user-friendly text like:
      - "next Tue at 5"
      - "tomorrow morning"
      - "in 2 hours"
    Returns timezone-aware datetime or None.
    """
    zone = ZoneInfo(tz)
    base = base or datetime.now(tz=zone)

    settings = {
        "RETURN_AS_TIMEZONE_AWARE": True,
        "TIMEZONE": tz,
        "TO_TIMEZONE": tz,
        "RELATIVE_BASE": base,
        # Prefer future dates when ambiguous: "Tuesday" => next Tuesday
        "PREFER_DATES_FROM": "future",
    }

    dt = dateparser.parse(text, settings=settings)
    if dt is None:
        return None

    # Ensure tz-aware in our target tz
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zone)
    else:
        dt = dt.astimezone(zone)

    return ParsedWhen(dt=dt, tz=tz, text=text)
