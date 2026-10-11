from app.orchestrator.response_formatter import format_schedule_summary
from app.services.formatter_service import pretty_time


def today_workflow(message, context):
    events = context.get("events", [])
    msg = message.lower()

    # If the user asked about a specific event's timing (e.g. "when is gym", "timing of lunch")
    for e in events:
        title = e.get("title", "").strip().lower()
        if title and title in msg:
            start_str = pretty_time(e.get("start"))
            end_str = pretty_time(e.get("end"))
            priority = e.get("priority", "medium")
            return {
                "reply": f"**{e['title']}** is scheduled for **{start_str} – {end_str}** today (Priority: {priority}).",
                "events": events,
                "conflicts": context.get("conflicts", []),
                "actions": [],
                "load_pct": context.get("load_pct", 0)
            }

    return {
        "reply": format_schedule_summary(context),
        "events": events,
        "conflicts": context.get("conflicts", []),
        "actions": [],
        "load_pct": context.get("load_pct", 0)
    }