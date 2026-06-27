from app.services.formatter_service import pretty_time


def reschedule_workflow(_message: str, context: dict) -> dict:
    """
    Suggest which low-priority events could be rescheduled.
    Called when the user asks vaguely ('what should I move?', 'optimize my day').
    For specific reschedules ('move standup to 3pm') the router handles it inline.
    """
    events = context["events"]
    low_priority = [e for e in events if (e.get("priority") or "medium") == "low"]

    if not low_priority:
        return {
            "reply": "I couldn't find any low-priority meetings that are safe to move.",
            "events": events,
            "actions": [],
        }

    free_slot = context.get("free_slot")
    suggested_time = pretty_time(free_slot[0]) if free_slot else "later today"

    actions = [
        {
            "action": "reschedule",
            "event_id": e.get("id"),
            "event_title": e["title"],
            "title": e["title"],
            "new_time": suggested_time,
            "detail": f"Move to {suggested_time} to reduce schedule fragmentation.",
        }
        for e in low_priority
    ]

    reply = (
        f"I found {len(low_priority)} low-priority meeting(s) that could be rescheduled "
        f"to improve your focus time."
    )

    return {
        "reply": reply,
        "events": events,
        "actions": actions,
    }
