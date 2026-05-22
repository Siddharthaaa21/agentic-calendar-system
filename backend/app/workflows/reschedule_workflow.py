from app.services.formatter_service import pretty_time


def reschedule_workflow(message, context):

    events = context["events"]

    low_priority = []

    for e in events:

        priority = e.get("priority", "MED")

        if priority == "LOW":
            low_priority.append(e)

    if not low_priority:

        return {
            "reply": (
                "I couldn't find any low-priority meetings "
                "that are safe to move."
            ),
            "events": events,
            "actions": []
        }

    suggestions = []
    free_slot = context.get("free_slot")
    suggested_time = pretty_time(free_slot[0]) if free_slot else "8PM"

    for e in low_priority:

        suggestions.append({
            "action": "RESCHEDULE",
            "event_id": e.get("id"),
            "event_title": e["title"],
            "title": e["title"],
            "new_time": suggested_time,
            "detail": (
                f"Move this event to around {suggested_time} "
                "to reduce schedule fragmentation."
            )
        })

    reply = (
        f"I found {len(low_priority)} low-priority "
        f"meeting(s) that could be rescheduled "
        f"to improve your focus time."
    )

    return {
        "reply": reply,
        "events": events,
        "actions": suggestions
    }