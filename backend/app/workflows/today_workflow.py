from app.orchestrator.response_formatter import (
    format_schedule_summary
)


def today_workflow(message, context):

    return {
        "reply": format_schedule_summary(context),
        "events": context["events"],
        "conflicts": context["conflicts"],
        "actions": [],
        "load_pct": context["load_pct"]
    }