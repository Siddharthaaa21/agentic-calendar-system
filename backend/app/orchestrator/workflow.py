import re

from app.orchestrator.context_builder import build_context
from app.agents.intent_agent import detect_intent
from app.agents.entity_agent import extract_entities
from app.orchestrator.router import route_intent
from app.orchestrator.response_formatter import style_reply
from app.core.guardrails import sanitize_output

from app.memory.session_memory import get_memory
from app.memory.session_memory import save_memory
from app.memory.session_memory import append_turn
from app.memory.session_memory import get_recent_turns
from app.memory.short_term import get_session, save_session
from app.agents.execution_agent import execute_actions


def _normalize_response(payload, intent):
    payload = payload or {}
    actions = payload.get("actions", []) or []
    return {
        "status": payload.get("status", "ok"),
        "reply": sanitize_output(payload.get("reply", "I can help with that.")),
        "intent": payload.get("intent", intent),
        "events": payload.get("events", []),
        "conflicts": payload.get("conflicts", []),
        "actions": actions,
        "load_pct": payload.get("load_pct", 0),
        "requires_confirmation": bool(actions),
        "suggestions": payload.get("suggestions", []),
    }


def run_agentic_workflow(message, conversation_history=None):

    append_turn("user", message)

    conversation_history = conversation_history or get_recent_turns(limit=8)

    # -----------------------------------
    # FOLLOW-UP MEMORY HANDLING
    # -----------------------------------

    lower_msg = message.lower()
    entities = extract_entities(message)
    draft_create = get_memory("draft_create_event") or {}

    create_verb = re.search(r"\b(add|create|schedule)\b", lower_msg) is not None
    pronoun_target = re.search(r"\b(it|this|that)\b", lower_msg) is not None
    time_only_followup = (
        entities.get("time")
        and len(lower_msg.split()) <= 3
        and not create_verb
    )
    explicit_new_create = create_verb and not pronoun_target

    if (
        draft_create.get("title")
        and entities.get("time")
        and entities.get("time", "").lower() != "unknown"
        and (time_only_followup or pronoun_target or "then" in lower_msg)
        and not explicit_new_create
    ):
        return {
            "status": "ok",
            "reply": f"Perfect — I can schedule {draft_create['title']} at {entities['time']}. Approve when you’re ready.",
            "intent": "CREATE_EVENT",
            "events": [],
            "conflicts": [],
            "actions": [
                {
                    "action": "create",
                    "event_title": draft_create["title"],
                    "title": draft_create["title"],
                    "new_time": entities["time"],
                    "detail": f"Create this event at {entities['time']}",
                }
            ],
            "load_pct": 0,
            "requires_confirmation": True,
            "suggestions": [],
        }

    if draft_create.get("title") and re.search(r"\b(add|create|schedule)\s+(it|this|that)\b", lower_msg):
        return {
            "status": "ok",
            "reply": f"Got it. What time should I schedule {draft_create['title']}?",
            "intent": "CREATE_EVENT",
            "events": [],
            "conflicts": [],
            "actions": [],
            "load_pct": 0,
            "requires_confirmation": False,
            "suggestions": [],
        }

    if (
        "that time" in lower_msg
        or "that slot" in lower_msg
        or "focus window" in lower_msg
        or "this window" in lower_msg
        or "add dsa" in lower_msg
    ):

        slot = get_memory("last_focus_slot")

        if slot:
            title = "DSA Practice"
            title_match = re.search(
                r"(?:add|create|schedule)\s+(.+?)\s+(?:to|in|for|at)\s+(?:this\s+)?(?:focus\s+window|window)",
                lower_msg,
            )
            if title_match and title_match.group(1).strip():
                title = title_match.group(1).strip().title()

            save_memory("draft_create_event", {"title": title})

            return {
                "reply": (
                    f"I can schedule {title} from "
                    f"{slot['start']} to {slot['end']}. "
                    f"Do you want me to create it?"
                ),

                "actions": [
                    {
                        "action": "create",
                        "event_title": title,
                        "title": title,
                        "start": slot["start"],
                        "end": slot["end"]
                    }
                ]
            }

    # -----------------------------------
    # NORMAL WORKFLOW
    # -----------------------------------

    context = build_context(conversation_history=conversation_history)

    intent_data = detect_intent(message)

    intent = intent_data.get(
        "intent",
        "UNKNOWN"
    )

    session = get_session()

    if intent == "APPROVE_ACTIONS":
        pending_actions = session.get("pending_actions", [])
        if not pending_actions:
            response = {
                "status": "ok",
                "reply": "There’s nothing pending approval right now.",
                "events": context.get("events", []),
                "actions": [],
                "conflicts": context.get("conflicts", []),
                "load_pct": context.get("load_pct", 0),
            }
        else:
            results = execute_actions(pending_actions)
            session["pending_actions"] = []
            save_session(session)
            save_memory("draft_create_event", None)
            failed = [item for item in results if item.get("status") == "FAILED"]
            response = {
                "status": "partial" if failed else "ok",
                "reply": "I applied your approved actions." if not failed else f"I applied actions, but {len(failed)} failed.",
                "events": context.get("events", []),
                "actions": [],
                "conflicts": context.get("conflicts", []),
                "load_pct": context.get("load_pct", 0),
                "suggestions": ["Say 'show conflicts' to review remaining issues."],
            }

        response = _normalize_response(response, intent)
        response["reply"] = style_reply(response["reply"], context, intent=intent)
        append_turn("assistant", response["reply"])
        return response

    if intent == "REJECT_ACTIONS":
        session["pending_actions"] = []
        save_session(session)
        save_memory("draft_create_event", None)
        response = _normalize_response({
            "status": "ok",
            "reply": "Done — I discarded the pending actions.",
            "events": context.get("events", []),
            "actions": [],
            "conflicts": context.get("conflicts", []),
            "load_pct": context.get("load_pct", 0),
        }, intent)
        response["reply"] = style_reply(response["reply"], context, intent=intent)
        append_turn("assistant", response["reply"])
        return response

    last_intent = get_memory("last_intent")
    save_memory("last_intent", intent)
    context["conversation_history"] = conversation_history[-8:]
    context["last_intent"] = last_intent

    response = route_intent(
        intent,
        message,
        context
    )

    if response.get("actions"):
        session["pending_actions"] = response["actions"]
        save_session(session)

    response = _normalize_response(response, intent)
    response["reply"] = style_reply(
        response.get("reply", "I can help with that."),
        context,
        intent=intent,
    )

    append_turn("assistant", response["reply"])

    return response