# assistant/recurrence.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr

DEFAULT_TZ = "America/Los_Angeles"

@dataclass
class Recurrence:
    rrule: str
    dtstart: datetime
    tz: str

def compute_next_run(rrule: str, dtstart: datetime, after: datetime) -> datetime | None:
    """
    Given an RRULE string and dtstart, return the next occurrence strictly after `after`.
    """
    rule = rrulestr(rrule, dtstart=dtstart)
    nxt = rule.after(after, inc=False)
    return nxt

def ensure_tz(dt: datetime, tz: str) -> datetime:
    zone = ZoneInfo(tz)
    return dt if dt.tzinfo else dt.replace(tzinfo=zone)

# Optional: tiny phrase-to-rrule fallback for a couple phrases you called out.
def phrase_to_rrule(phrase: str) -> str | None:
    p = phrase.strip().lower()

    # "every other friday"
    if p == "every other friday":
        # Weekly, interval=2, Friday
        return "FREQ=WEEKLY;INTERVAL=2;BYDAY=FR"

    # "last weekday" (last Mon-Fri of the month)
    if p == "last weekday":
        return "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1"

    return None
