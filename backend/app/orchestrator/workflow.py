import re

from app.orchestrator.context_builder import build_context, invalidate_event_cache
from app.agents.intent_agent import detect_intent
from app.agents.entity_agent import extract_entities
from app.orchestrator.router import route_intent
from app.orchestrator.response_formatter import style_reply
from app.core.guardrails import sanitize_output

from app.memory.session_memory import get_memory, save_memory, append_turn, get_recent_turns
from app.memory.short_term import get_session, save_session
from app.agents.execution_agent import execute_actions


def _normalize_response(payload: dict, intent: str) -> dict:
    payload = payload or {}
    actions = payload.get("actions") or []
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


def run_agentic_workflow(message: str, conversation_history: list = None) -> dict:
    append_turn("user", message)
    conversation_history = conversation_history or get_recent_turns(limit=8)
    lower_msg = message.lower().strip()

    # ------------------------------------------------------------------
    # Small-talk fast paths — skip context build for trivial messages
    # ------------------------------------------------------------------
    _greetings = re.compile(r"^(hi|hello|hey|yo|good\s+morning|good\s+evening)[!.?]*$")
    _thanks = re.compile(r"^(thanks|thank\s+you|thx)[!.?]*$")

    if _greetings.fullmatch(lower_msg):
        response = _normalize_response({
            "reply": "Hey — I'm with you. Want a quick summary of today, or should I suggest what to move first?",
            "intent": "UNKNOWN",
        }, "UNKNOWN")
        append_turn("assistant", response["reply"])
        return response

    if _thanks.fullmatch(lower_msg):
        response = _normalize_response({
            "reply": "Anytime — happy to help. Want me to keep optimizing the rest of your day?",
            "intent": "UNKNOWN",
        }, "UNKNOWN")
        append_turn("assistant", response["reply"])
        return response

    if "how are you" in lower_msg:
        response = _normalize_response({
            "reply": "Doing great — ready to plan with you. Should we review your current load or tweak your schedule?",
            "intent": "UNKNOWN",
        }, "UNKNOWN")
        append_turn("assistant", response["reply"])
        return response

    # ------------------------------------------------------------------
    # Multi-turn draft: user provides time for a previously named event
    # ------------------------------------------------------------------
    entities = extract_entities(message, context={"conversation_history": conversation_history})
    draft_create = get_memory("draft_create_event") or {}

    # ------------------------------------------------------------------
    # Answer to "what should I call the event?" — the bot just asked for
    # a title, so treat this message as the title even if it doesn't
    # contain a command verb (e.g. "ai-900").
    # ------------------------------------------------------------------
    if get_memory("awaiting_event_title"):
        _cancel_words = {"cancel", "nevermind", "never mind", "stop", "no", "skip", "nothing"}
        candidate = entities.get("event_title") or message.strip()
        candidate_clean = candidate.strip().strip("?.! ")

        if candidate_clean.lower() in _cancel_words:
            save_memory("awaiting_event_title", False)
            response = _normalize_response({
                "reply": "No problem — let me know if you'd like to add something else.",
                "intent": "CREATE_EVENT",
            }, "CREATE_EVENT")
            append_turn("assistant", response["reply"])
            return response

        if candidate_clean and not re.match(r"^(what|why|how|who|when|where|which)\b", candidate_clean, re.IGNORECASE) and len(candidate_clean.split()) <= 8:
            save_memory("draft_create_event", {"title": candidate_clean})
            save_memory("awaiting_event_title", False)

            t = entities.get("time")
            if t:
                response = _normalize_response({
                    "reply": f"I can add **{candidate_clean}** at {t}. Approve when you're ready.",
                    "intent": "CREATE_EVENT",
                    "actions": [{
                        "action": "create",
                        "event_title": candidate_clean,
                        "title": candidate_clean,
                        "new_time": t,
                        "detail": f"Create event at {t}",
                    }],
                }, "CREATE_EVENT")
            else:
                response = _normalize_response({
                    "reply": f"Got it. What time should I schedule **{candidate_clean}**?",
                    "intent": "CREATE_EVENT",
                }, "CREATE_EVENT")
            append_turn("assistant", response["reply"])
            return response

    has_time = entities.get("time") and entities["time"].lower() != "unknown"
    create_verb = bool(re.search(r"\b(add|create|schedule)\b", lower_msg))
    pronoun_target = bool(re.search(r"\b(it|this|that)\b", lower_msg))
    time_only_followup = has_time and len(lower_msg.split()) <= 3 and not create_verb
    explicit_new_create = create_verb and not pronoun_target

    if (
        draft_create.get("title")
        and has_time
        and (time_only_followup or pronoun_target or "then" in lower_msg)
        and not explicit_new_create
    ):
        title = draft_create["title"]
        t = entities["time"]
        response = _normalize_response({
            "reply": f"Perfect — I can schedule **{title}** at {t}. Approve when you're ready.",
            "intent": "CREATE_EVENT",
            "actions": [{
                "action": "create",
                "event_title": title,
                "title": title,
                "new_time": t,
                "detail": f"Create event at {t}",
            }],
        }, "CREATE_EVENT")
        append_turn("assistant", response["reply"])
        return response

    # "add/create/schedule it/this/that" → ask for time
    if draft_create.get("title") and re.search(r"\b(add|create|schedule)\s+(it|this|that)\b", lower_msg):
        response = _normalize_response({
            "reply": f"Got it. What time should I schedule **{draft_create['title']}**?",
            "intent": "CREATE_EVENT",
        }, "CREATE_EVENT")
        append_turn("assistant", response["reply"])
        return response

    # Multi-turn reschedule: user provides time for a previously identified event
    draft_reschedule = get_memory("draft_reschedule_event") or {}
    if draft_reschedule.get("title") and has_time and not create_verb:
        title = draft_reschedule["title"]
        t = entities["time"]
        action = {
            "action": "reschedule",
            "event_id": draft_reschedule.get("id"),
            "event_title": title,
            "title": title,
            "new_time": t,
            "detail": f"Move to {t}",
        }
        response = _normalize_response({
            "reply": f"Perfect — I can move **{title}** to {t}. Approve when you're ready.",
            "intent": "RESCHEDULE_EVENT",
            "actions": [action],
        }, "RESCHEDULE_EVENT")
        append_turn("assistant", response["reply"])
        return response

    # Focus-window follow-up: "add X to that slot / this window"
    if re.search(r"\b(that time|that slot|focus window|this window)\b", lower_msg):
        slot = get_memory("last_focus_slot")
        if slot:
            title_match = re.search(
                r"\b(?:add|schedule|create)\s+(.+?)\s+(?:to|in|at|for)\b", lower_msg
            )
            if title_match:
                title = title_match.group(1).strip().title()
            else:
                title = (get_memory("draft_create_event") or {}).get("title", "Focus Task")
            save_memory("draft_create_event", {"title": title})
            response = _normalize_response({
                "reply": f"I can schedule **{title}** from {slot['start']} to {slot['end']}. Approve?",
                "intent": "CREATE_EVENT",
                "actions": [{
                    "action": "create",
                    "event_title": title,
                    "title": title,
                    "start": slot["start"],
                    "end": slot["end"],
                }],
            }, "CREATE_EVENT")
            append_turn("assistant", response["reply"])
            return response

    # ------------------------------------------------------------------
    # Normal workflow
    # ------------------------------------------------------------------
    context = build_context(conversation_history=conversation_history)

    intent_data = detect_intent(message, context={
        "last_intent": get_memory("last_intent"),
        "conversation_history": conversation_history,
    })
    intent = intent_data.get("intent", "UNKNOWN")

    session = get_session()

    # Keep the executable event set in sync with what the chat path just built.
    # execute_actions() resolves event ids/titles against session["last_events"],
    # which previously only /today ever populated — so approving a delete or
    # reschedule from a pure chat session (without loading /today first) failed
    # with "Event not found". Persisting here keeps both approval paths working.
    session["last_events"] = context.get("events", [])
    save_session(session)

    # Approval / rejection handled here to access pending_actions from session
    if intent == "APPROVE_ACTIONS":
        pending = session.get("pending_actions", [])
        if not pending:
            response = _normalize_response({
                "reply": "There's nothing pending approval right now.",
                "events": context.get("events", []),
                "conflicts": context.get("conflicts", []),
                "load_pct": context.get("load_pct", 0),
            }, intent)
        else:
            results = execute_actions(pending)
            session["pending_actions"] = []
            save_session(session)
            save_memory("draft_create_event", None)
            save_memory("draft_reschedule_event", None)
            invalidate_event_cache()
            failed = [r for r in results if r.get("status") == "FAILED"]
            response = _normalize_response({
                "status": "partial" if failed else "ok",
                "reply": (
                    f"I applied your actions, but {len(failed)} failed."
                    if failed else "Done — all actions applied to your calendar."
                ),
                "events": context.get("events", []),
                "conflicts": context.get("conflicts", []),
                "load_pct": context.get("load_pct", 0),
                "suggestions": ["Say 'show conflicts' to review any remaining issues."],
            }, intent)
        response["reply"] = style_reply(response["reply"], context, intent=intent)
        append_turn("assistant", response["reply"])
        return response

    if intent == "REJECT_ACTIONS":
        session["pending_actions"] = []
        save_session(session)
        save_memory("draft_create_event", None)
        save_memory("draft_reschedule_event", None)
        response = _normalize_response({
            "reply": "Done — I discarded the pending actions.",
            "events": context.get("events", []),
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

    response = route_intent(intent, message, context) or {
        "reply": "I understood your request but encountered an error.",
        "intent": intent,
        "events": context.get("events", []),
        "conflicts": context.get("conflicts", []),
        "actions": [],
        "load_pct": context.get("load_pct", 0),
    }

    if response.get("actions"):
        session["pending_actions"] = response["actions"]
        save_session(session)

    response = _normalize_response(response, intent)
    response["reply"] = style_reply(response.get("reply", ""), context, intent=intent)
    append_turn("assistant", response["reply"])
    return response
