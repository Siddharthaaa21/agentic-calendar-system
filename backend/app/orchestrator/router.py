from app.workflows.today_workflow import today_workflow
from app.workflows.focus_workflow import focus_workflow
from app.workflows.reschedule_workflow import (
    reschedule_workflow
)
from app.agents.entity_agent import extract_entities
from app.memory.session_memory import get_memory
from app.memory.session_memory import save_memory


def route_intent(intent, message, context):

    routes = {

        "GET_TODAY": today_workflow,

        "GET_FREE_SLOTS": focus_workflow,

        "OPTIMIZE_DAY": focus_workflow,

        "RESCHEDULE_EVENT": reschedule_workflow,
    }

    workflow = routes.get(intent)

    if not workflow:

        if intent == "DELETE_EVENT":
            entities = extract_entities(message)
            event_title = entities.get("event_title")

            if not event_title:
                return {
                    "reply": "Sure — which event should I remove?",
                    "intent": intent,
                    "events": context["events"],
                    "conflicts": context.get("conflicts", []),
                    "actions": [],
                    "load_pct": context.get("load_pct", 0),
                }

            matched = None
            for event in context.get("events", []):
                title = (event.get("title") or "").lower()
                if event_title.lower() in title:
                    matched = event
                    break

            if not matched:
                return {
                    "reply": f"I couldn't find '{event_title}' in your calendar.",
                    "intent": intent,
                    "events": context["events"],
                    "conflicts": context.get("conflicts", []),
                    "actions": [],
                    "load_pct": context.get("load_pct", 0),
                }

            action = {
                "action": "delete",
                "event_id": matched.get("id"),
                "event_title": matched.get("title"),
                "title": matched.get("title"),
                "detail": "Remove this event from calendar",
            }
            return {
                "reply": f"I can remove {matched.get('title')}. Approve when you’re ready.",
                "intent": intent,
                "events": context["events"],
                "conflicts": context.get("conflicts", []),
                "actions": [action],
                "load_pct": context.get("load_pct", 0),
            }

        if intent == "CREATE_EVENT":
            entities = extract_entities(message)
            event_title = entities.get("event_title")
            new_time = entities.get("time")

            if event_title in {"it", "this", "that"}:
                draft = get_memory("draft_create_event") or {}
                event_title = draft.get("title")

            if event_title:
                save_memory("draft_create_event", {"title": event_title})

            if not event_title:
                return {
                    "reply": "Sure — what should I call the event?",
                    "intent": intent,
                    "events": context["events"],
                    "conflicts": context.get("conflicts", []),
                    "actions": [],
                    "load_pct": context.get("load_pct", 0),
                }

            if not new_time:
                return {
                    "reply": f"Got it. What time should I schedule {event_title}?",
                    "intent": intent,
                    "events": context["events"],
                    "conflicts": context.get("conflicts", []),
                    "actions": [],
                    "load_pct": context.get("load_pct", 0),
                }

            action = {
                "action": "create",
                "event_title": event_title,
                "title": event_title,
                "new_time": new_time,
                "detail": f"Create this event at {new_time}",
            }
            return {
                "reply": f"I can add {event_title} at {new_time}. Approve when you’re ready.",
                "intent": intent,
                "events": context["events"],
                "conflicts": context.get("conflicts", []),
                "actions": [action],
                "load_pct": context.get("load_pct", 0),
            }

        if intent == "SHOW_CONFLICTS":
            conflicts = context.get("conflicts", [])
            if not conflicts:
                return {
                    "reply": "No conflicts found in your schedule.",
                    "intent": intent,
                    "events": context["events"],
                    "conflicts": [],
                    "actions": [],
                    "load_pct": context.get("load_pct", 0),
                }

            conflict_lines = [f"• {item['title']}" for item in conflicts]
            return {
                "reply": "I found these conflicts:\n\n" + "\n".join(conflict_lines),
                "intent": intent,
                "events": context["events"],
                "conflicts": conflicts,
                "actions": [],
                "load_pct": context.get("load_pct", 0),
            }

        if intent in {"APPROVE_ACTIONS", "REJECT_ACTIONS"}:
            return {
            "reply": "I got it. Use the action buttons to safely apply this change.",
                "intent": intent,
                "events": context["events"],
                "conflicts": context.get("conflicts", []),
                "actions": [],
                "load_pct": context.get("load_pct", 0),
            }

        return {
            "reply": (
                "I understood your request "
                "but don't support it yet."
            ),
            "intent": intent,
            "events": context["events"],
            "conflicts": context.get("conflicts", []),
            "load_pct": context.get("load_pct", 0),
            "actions": []
        }

    result = workflow(message, context)
    result.setdefault("intent", intent)
    result.setdefault("conflicts", context.get("conflicts", []))
    result.setdefault("load_pct", context.get("load_pct", 0))
    return result