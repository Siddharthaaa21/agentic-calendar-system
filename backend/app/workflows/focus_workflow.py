from app.services.formatter_service import pretty_time
from app.memory.session_memory import save_memory

def focus_workflow(message, context):

    slot = context["free_slot"]

    if not slot:

        if not context.get("events"):
            reply = "Your calendar is clear today — you've got open time whenever you need it."
        else:
            reply = "Your calendar is heavily packed today — I couldn't find an open focus window."

        return {
            "reply": reply,
            "events": context["events"],
            "actions": []
        }

    start, end = slot

    save_memory("last_focus_slot", {
        "start": start,
        "end": end
    })

    reply = (
        "I found a strong focus window for deep work.\n\n"

        f"Recommended focus slot:\n"
        f"{pretty_time(start)} → {pretty_time(end)}\n\n"

        "Why this works:\n"
        "- Minimal meeting interruptions\n"
        "- Good cognitive spacing\n"
        "- Reduces context switching"
    )

    return {
        "reply": reply,
        "events": context["events"],
        "actions": []
    }