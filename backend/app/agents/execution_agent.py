from app.services.calendar_service import (
    cancel_event,
    reschedule_event
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

    parsed = datetime.strptime(
        cleaned,
        "%I%p"
    )

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

                event_title = action.get(
                    "event_title"
                )

                event = find_event_by_title(
                    events,
                    event_title
                )

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

                event_title = action.get(
                    "event_title"
                )

                new_time = action.get(
                    "new_time"
                )

                if not new_time:
                    raise Exception(
                        "Missing new_time"
                    )

                event = find_event_by_title(
                    events,
                    event_title
                )

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