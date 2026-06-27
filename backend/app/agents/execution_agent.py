from app.services.calendar_service import (
    cancel_event,
    reschedule_event,
    create_event,
)

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.memory.short_term import get_session
from app.memory.long_term import update_pattern


# Local timezone the user's spoken times ("8pm") are interpreted in.
# Defaults to UTC; override with APP_TIMEZONE (e.g. "America/New_York").
def _local_tz():
    try:
        return ZoneInfo(os.getenv("APP_TIMEZONE", "UTC"))
    except Exception:
        return timezone.utc


# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

def convert_time_to_iso(time_str):
    """Convert a spoken time like "8pm" into an RFC3339 UTC timestamp.

    The clock time is interpreted in the user's local timezone (APP_TIMEZONE)
    and then converted to UTC, so a reschedule to "8pm" lands at 8pm local —
    not 8pm UTC. A leading "tomorrow" shifts the date forward one day.
    """
    raw = (time_str or "").strip().lower()
    day_offset = 0
    if raw.startswith("tomorrow"):
        day_offset = 1
        raw = raw[len("tomorrow"):].strip()

    cleaned = raw.replace(" ", "").upper()

    parsed = None
    for pattern in ["%I:%M%p", "%I%p", "%H:%M"]:
        try:
            parsed = datetime.strptime(cleaned, pattern)
            break
        except ValueError:
            continue

    if parsed is None:
        raise ValueError(f"Unsupported time format: {time_str}")

    tz = _local_tz()
    target_date = (datetime.now(tz) + timedelta(days=day_offset)).date()
    local_dt = datetime.combine(target_date, parsed.time(), tzinfo=tz)

    return local_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def find_event_by_title(events, title):

    title = title.lower().strip()

    for e in events:

        event_title = (
            e.get("title", "")
            .lower()
        )

        if title in event_title:
            return e

    return None


def _event_duration_minutes(event, default=60):
    """Original duration of an event in minutes, or `default` if unparseable."""
    try:
        s = datetime.fromisoformat(str(event.get("start")).replace("Z", "+00:00"))
        e = datetime.fromisoformat(str(event.get("end")).replace("Z", "+00:00"))
        mins = int((e - s).total_seconds() / 60)
        return mins if mins > 0 else default
    except Exception:
        return default


def should_reschedule(event):

    priority = event.get(
        "priority",
        "medium"
    )

    if priority == "high":
        return False

    return True


# ---------------------------------------------------
# MAIN EXECUTOR
# ---------------------------------------------------

def execute_actions(actions):

    results = []

    session = get_session()

    events = session.get(
        "last_events",
        []
    )

    for action in actions:

        try:

            action_type = (
                action.get("action", "")
                .lower()
            )

            # ===================================================
            # DELETE EVENT
            # ===================================================

            if action_type == "delete":

                event_title = action.get("event_title") or action.get("title")

                event = None
                if action.get("event_id"):
                    event = next((item for item in events if item.get("id") == action.get("event_id")), None)
                if not event and event_title:
                    event = find_event_by_title(events, event_title)

                if not event:
                    raise Exception(
                        "Event not found"
                    )

                response = cancel_event(
                    event["id"]
                )

                # Record so the prioritizer can learn frequently-cancelled events.
                update_pattern((event.get("title") or "").lower(), action="cancel")

                results.append({
                    "status": "EXECUTED",
                    "action": "DELETE",
                    "event": event_title,
                    "response": response
                })

            # ===================================================
            # RESCHEDULE EVENT
            # ===================================================

            elif action_type == "reschedule":

                event_title = action.get("event_title") or action.get("title")

                new_time = action.get(
                    "new_time"
                )

                if not new_time:
                    raise Exception(
                        "Missing new_time"
                    )

                event = None
                if action.get("event_id"):
                    event = next((item for item in events if item.get("id") == action.get("event_id")), None)
                if not event and event_title:
                    event = find_event_by_title(events, event_title)

                if not event:
                    raise Exception(
                        "Event not found"
                    )

                if not should_reschedule(event):
                    raise Exception(
                        "High priority event cannot be moved"
                    )

                # -----------------------------------------
                # CONVERT 8pm -> ISO DATETIME
                # -----------------------------------------

                new_start = convert_time_to_iso(
                    new_time
                )

                start_dt = datetime.fromisoformat(
                    new_start.replace("Z", "")
                )

                # Preserve the event's original duration instead of forcing 1h.
                duration = _event_duration_minutes(event)
                end_dt = start_dt + timedelta(minutes=duration)

                new_end = (
                    end_dt.isoformat() + "Z"
                )

                # -----------------------------------------
                # EXECUTE GOOGLE CALENDAR UPDATE
                # -----------------------------------------

                response = reschedule_event(
                    event["id"],
                    new_start,
                    new_end
                )

                update_pattern((event.get("title") or "").lower(), action="reschedule")

                results.append({
                    "status": "EXECUTED",
                    "action": "RESCHEDULE",
                    "event": event_title,
                    "new_start": new_start,
                    "new_end": new_end,
                    "response": response
                })

            # ===================================================
            # CREATE EVENT
            # ===================================================

            elif action_type in {"create", "create_event"}:

                event_title = action.get("event_title") or action.get("title") or "New Event"
                start_time = action.get("start")
                end_time = action.get("end")

                if (not start_time or not end_time) and action.get("new_time"):
                    start_time = convert_time_to_iso(action.get("new_time"))
                    start_dt = datetime.fromisoformat(start_time.replace("Z", ""))
                    end_time = (start_dt + timedelta(hours=1)).isoformat() + "Z"

                if not start_time or not end_time:
                    raise Exception("Missing start/end for create action")

                response = create_event(
                    title=event_title,
                    start_time=start_time,
                    end_time=end_time,
                    description=action.get("detail", "")
                )

                results.append({
                    "status": "EXECUTED",
                    "action": "CREATE",
                    "event": event_title,
                    "response": response
                })

            # ===================================================
            # UNKNOWN ACTION
            # ===================================================

            else:

                results.append({
                    "status": "FAILED",
                    "error": (
                        f"Unknown action: "
                        f"{action_type}"
                    )
                })

        except Exception as e:

            results.append({
                "status": "FAILED",
                "error": str(e),
                "action": action
            })

    return results