from app.services.calendar_service import get_today_events
from app.tasks.scheduler import find_free_slot
from app.memory.state_manager import load_preferences
from app.memory.session_memory import get_recent_turns
from app.core.guardrails import validate_events


def _infer_conversation_prefs(conversation_history):
    if not conversation_history:
        return {}

    recent_user = [
        item.get("content", "")
        for item in conversation_history
        if item.get("role") == "user"
    ][-5:]
    merged = " ".join(recent_user).lower()

    return {
        "prefers_brief": any(token in merged for token in ["short", "brief", "quick", "tldr"]),
        "wants_explanation": any(token in merged for token in ["why", "explain", "reason"]),
    }


def build_context(conversation_history=None):

    conversation_history = conversation_history or get_recent_turns(limit=8)

    events = validate_events(get_today_events())

    conflicts = []
    free_slot = find_free_slot(events, 60)

    sorted_events = sorted(
        events,
        key=lambda x: x["start"]
    )

    for i in range(len(sorted_events) - 1):

        current_end = sorted_events[i]["end"]
        next_start = sorted_events[i + 1]["start"]

        if current_end > next_start:

            conflicts.append({
                "title": (
                    f"{sorted_events[i]['title']} overlaps with "
                    f"{sorted_events[i + 1]['title']}"
                )
            })

    load_pct = min(len(events) * 18, 100)

    return {
        "events": events,
        "conflicts": conflicts,
        "free_slot": free_slot,
        "load_pct": load_pct,
        "preferences": load_preferences(),
        "conversation_history": conversation_history,
        "conversation_prefs": _infer_conversation_prefs(conversation_history),
    }