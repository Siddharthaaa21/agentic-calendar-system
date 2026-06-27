from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple


def _parse_time(t: str) -> datetime:
    """Parse an ISO-8601 string (datetime or date-only) into a UTC-aware datetime."""
    cleaned = t.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        dt = datetime.fromisoformat(cleaned + "T00:00:00+00:00")
    # Ensure always timezone-aware so arithmetic never mixes naive/aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _format_time(t: datetime) -> str:
    return t.isoformat().replace("+00:00", "Z")


def find_free_slot(events: list, duration_minutes: int) -> Optional[Tuple[str, str]]:
    """
    Return the first (start, end) gap of at least `duration_minutes` in the day,
    searching between 09:00 and 22:00 local to the first event's date.
    Returns None if no gap is found or events list is empty.
    """
    if not events:
        return None

    valid = []
    for e in events:
        try:
            valid.append((
                _parse_time(str(e["start"])),
                _parse_time(str(e["end"])),
            ))
        except Exception:
            continue

    if not valid:
        return None

    valid.sort(key=lambda x: x[0])

    ref_date = valid[0][0].date()
    tz = valid[0][0].tzinfo or timezone.utc
    day_start = datetime(ref_date.year, ref_date.month, ref_date.day, 9, 0, tzinfo=tz)
    day_end = datetime(ref_date.year, ref_date.month, ref_date.day, 22, 0, tzinfo=tz)
    duration = timedelta(minutes=duration_minutes)

    cursor = day_start
    for start, end in valid:
        if start - cursor >= duration:
            return _format_time(cursor), _format_time(cursor + duration)
        cursor = max(cursor, end)

    if day_end - cursor >= duration:
        return _format_time(cursor), _format_time(cursor + duration)

    return None
