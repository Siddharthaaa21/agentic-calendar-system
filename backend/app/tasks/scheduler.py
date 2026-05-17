from datetime import datetime, timedelta


def parse_time(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def format_time(t):
    return t.isoformat().replace("+00:00", "Z")


def find_free_slot(events, duration_minutes):
    """
    Find next available slot in the day
    """

    if not events:
        return None

    # sort events by start time
    events_sorted = sorted(events, key=lambda e: e["start"])

    day_start = parse_time(events_sorted[0]["start"]).replace(hour=9, minute=0)
    day_end = parse_time(events_sorted[0]["start"]).replace(hour=22, minute=0)

    duration = timedelta(minutes=duration_minutes)

    prev_end = day_start

    for event in events_sorted:
        start = parse_time(event["start"])
        end = parse_time(event["end"])

        # gap found
        if start - prev_end >= duration:
            return format_time(prev_end), format_time(prev_end + duration)

        prev_end = max(prev_end, end)

    # check after last event
    if day_end - prev_end >= duration:
        return format_time(prev_end), format_time(prev_end + duration)

    return None