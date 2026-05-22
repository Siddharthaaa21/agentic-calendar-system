from app.services.calendar_service import (
    cancel_event,
    reschedule_event,
    create_event,
)

from datetime import datetime, timedelta

from app.memory.short_term import get_session


# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

def convert_time_to_iso(time_str):

    today = datetime.utcnow().date()

    cleaned = (
        time_str
        .replace(" ", "")
        .upper()
    )

    parsed = None
    for pattern in ["%I:%M%p", "%I%p", "%H:%M"]:
        try:
            parsed = datetime.strptime(cleaned, pattern)
            break
        except ValueError:
            continue

    if parsed is None:
        raise ValueError(f"Unsupported time format: {time_str}")

    final_dt = datetime.combine(
        today,
        parsed.time()
    )

    return final_dt.isoformat() + "Z"


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

                end_dt = (
                    start_dt +
                    timedelta(hours=1)
                )

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