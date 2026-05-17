from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import logging

from app.services.calendar_service import get_today_events
from app.agents.planner_agent import structure_events
from app.agents.prioritizer_agent import assign_priority
from app.agents.decision_agent import generate_decision
from app.agents.action_agent import build_actions
from app.agents.execution_agent import execute_actions

from app.memory.short_term import get_session, save_session
from app.memory.long_term import update_pattern
from app.memory.conversation_state import (
    set_pending_action,
    get_pending_action,
    clear_pending_action
)
from app.agents.intend_agent import detect_intent
from app.agents.entity_agent import extract_entities
from app.tasks.scheduler import find_free_slot


# ------------------ CONFIG ------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agentic Calendar System")


# ------------------ MODELS ------------------
class ActionRequest(BaseModel):
    actions: List[Dict[str, Any]] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    approval: str = Field(..., description="yes / no")


# ------------------ HEALTH ------------------
@app.get("/")
def read_root():
    return {"status": "ok", "service": "agentic-calendar"}


# ------------------ MAIN PIPELINE ------------------
@app.get("/today")
def today_events():
    try:
        # 1. Fetch
        events = get_today_events()
        if not events:
            return {
                "events": [],
                "suggestions": "No events for today",
                "actions": []
            }

        # 2. Structure
        structured = structure_events(events)

        # 3. Prioritize
        prioritized = assign_priority(structured)

        # 4. Decision (LLM)
        decision = generate_decision(prioritized)

        if not isinstance(decision, dict):
            logger.warning("Invalid decision format")
            decision = {"suggestions": "", "actions": []}

        suggestions = decision.get("suggestions", "")
        raw_actions = decision.get("actions", [])

        # 5. Build Actions
        actions = build_actions(prioritized, raw_actions)
        print(" RAW ACTIONS:", raw_actions)

        print("FINAL ACTIONS:", actions)

        # 6. Save session (IMPORTANT for approval)
        save_session({
                 "pending_actions": actions,
                "last_events": prioritized,
               "last_suggestions": suggestions
})
        # 7. Update long-term memory
        for e in prioritized:
            try:
                update_pattern(e.get("title", ""))
            except Exception as mem_err:
                logger.warning(f"Memory update failed: {mem_err}")

        return {
            "events": prioritized,
            "suggestions": suggestions,
            "actions": actions
        }

    except Exception as e:
        logger.exception("Error in /today")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------ DIRECT EXECUTION ------------------
@app.post("/execute")
def execute(payload: ActionRequest):
    session = get_session()

    updated_session = {
        "last_events": session.get("last_events", []),
        "pending_actions": payload.actions,
        "last_suggestions": session.get("last_suggestions", "")
    }

    save_session(updated_session)

    return {
        "message": "Actions queued for approval",
        "pending_actions": payload.actions
    }
# ------------------ APPROVAL (HITL) ------------------
@app.post("/approve")
def approve(req: dict):
    session = get_session()

    if req.get("approval") != "yes":
        return {"message": "Actions rejected"}

    actions = session.get("pending_actions", [])

    results = execute_actions(actions)

    # clear pending after execution
    session["pending_actions"] = []
    save_session(session)

    return {
        "message": "Actions executed",
        "results": results
    }
@app.post("/chat")
async def chat(req: dict):

    message = req.get("message", "").strip()

    # -----------------------------------
    # FETCH EVENTS
    # -----------------------------------
    events = get_today_events()

    # -----------------------------------
    # PENDING MEMORY
    # -----------------------------------
    pending = get_pending_action()

    # -----------------------------------
    # YES / APPROVE
    # -----------------------------------
    if pending["awaiting_confirmation"]:

        if message.lower() in ["yes", "approve", "do it"]:

            action = pending["pending_action"]

            results = execute_actions([action])

            clear_pending_action()

            updated_events = get_today_events()

            return {
                "reply": "Done. Calendar updated successfully.",
                "events": updated_events,
                "actions": [],
                "results": results
            }

        # -----------------------------------
        # NO / REJECT
        # -----------------------------------
        if message.lower() in ["no", "reject", "cancel"]:

            clear_pending_action()

            return {
                "reply": "Okay, I discarded the action.",
                "events": events,
                "actions": []
            }

        # -----------------------------------
        # FOLLOW-UP TIME
        # Example:
        # "actually 9pm"
        # -----------------------------------
        entities = extract_entities(message)

        if entities.get("time"):

            pending_action = pending["pending_action"]

            pending_action["new_time"] = entities["time"]

            set_pending_action(pending_action)

            return {
                "reply": (
                    f"Updated. Move "
                    f"{pending_action['event_title']} "
                    f"to {entities['time']}?"
                ),
                "events": events,
                "actions": [pending_action]
            }

    # -----------------------------------
    # INTENT DETECTION
    # -----------------------------------
    intent_data = detect_intent(message)

    intent = intent_data.get("intent", "UNKNOWN")

    # -----------------------------------
    # GET TODAY
    # -----------------------------------
    if intent == "GET_TODAY":

        if not events:
            return {
                "reply": "You have no events scheduled today.",
                "events": [],
                "actions": []
            }

        formatted = []

        for e in events:

            title = e.get("summary") or e.get("title")

            start = e.get("start", "Unknown")
            if isinstance(start, dict):
                start = start.get("dateTime", "Unknown")

            formatted.append(
                f"• {title} at {start}"
            )

        return {
            "reply": (
                "Here’s your schedule for today:\n\n"
                + "\n".join(formatted)
            ),
            "events": events,
            "actions": []
        }

    # -----------------------------------
    # SHOW CONFLICTS
    # -----------------------------------
    elif intent == "SHOW_CONFLICTS":

        conflicts = []

        sorted_events = sorted(
            events,
            key=lambda x: x["start"])

        for i in range(len(sorted_events) - 1):

            current_event = sorted_events[i]
            next_event = sorted_events[i + 1]

            current_end = current_event["end"]
            next_start = next_event["start"]
            if isinstance(current_end, dict):
                current_end = current_end.get("dateTime")
            if isinstance(next_start, dict):
                next_start = next_start.get("dateTime")

            if current_end > next_start:

                conflicts.append(
                    f"{current_event['title']} "
                    f"overlaps with "
                    f"{next_event['title']}"
                )

        if not conflicts:

            return {
                "reply": "No conflicts found in your schedule.",
                "events": events,
                "actions": []
            }

        return {
            "reply": (
                "I found these conflicts:\n\n"
                + "\n".join(conflicts)
            ),
            "events": events,
            "conflicts": conflicts,
            "actions": []
        }

    # -----------------------------------
    # FREE SLOTS
    # -----------------------------------
    elif intent == "GET_FREE_SLOTS":

        free_slot = find_free_slot(events, 60)

        if not free_slot:

            return {
                "reply": "I couldn't find a free slot today.",
                "events": events,
                "actions": []
            }

        start, end = free_slot

        return {
            "reply": (
                f"You have a free slot from "
                f"{start} to {end}."
            ),
            "events": events,
            "actions": []
        }

    # -----------------------------------
    # RESCHEDULE EVENT
    # -----------------------------------
    elif intent == "RESCHEDULE_EVENT":

        entities = extract_entities(message)

        event_title = entities.get("event_title")
        new_time = entities.get("time")

        if not event_title:

            return {
                "reply": "Which event do you want to move?",
                "events": events,
                "actions": []
            }

        matched_event = None

        for e in events:

            title = (
                e.get("title", "")
                .lower()
            )

            if event_title.lower() in title:

                matched_event = e
                break

        if not matched_event:

            return {
                "reply": (
                    f"I couldn't find "
                    f"'{event_title}' "
                    f"in your calendar."
                ),
                "events": events,
                "actions": []
            }

        pending_action = {
            "intent": "RESCHEDULE_EVENT",
            "action": "reschedule",
            "event_id": matched_event["id"],
            "event_title": matched_event["title"],
            "new_time": new_time
        }

        set_pending_action(pending_action)

        return {
            "reply": (
                f"Do you want me to move "
                f"{matched_event['title']} "
                f"to {new_time}?"
            ),
            "events": events,
            "actions": [pending_action]
        }

    # -----------------------------------
    # DELETE EVENT
    # -----------------------------------
    elif intent == "DELETE_EVENT":

        entities = extract_entities(message)

        event_title = entities.get("event_title")

        if not event_title:

            return {
                "reply": "Which event should I delete?",
                "events": events,
                "actions": []
            }

        matched_event = None

        for e in events:

            title = (
                e.get("title", "")
                .lower()
            )

            if event_title.lower() in title:

                matched_event = e
                break

        if not matched_event:

            return {
                "reply": (
                    f"I couldn't find "
                    f"{event_title}."
                ),
                "events": events,
                "actions": []
            }

        pending_action = {
            "intent": "DELETE_EVENT",
            "action": "delete",
            "event_id": matched_event["id"],
            "event_title": matched_event["title"]
        }

        set_pending_action(pending_action)

        return {
            "reply": (
                f"Do you want me to delete "
                f"{matched_event['title']}?"
            ),
            "events": events,
            "actions": [pending_action]
        }

    # -----------------------------------
    # OPTIMIZE DAY
    # -----------------------------------
    elif intent == "OPTIMIZE_DAY":

        decision = generate_decision(events)

        suggestions = decision.get("suggestions", [])
        actions = decision.get("actions", [])

        return {
            "reply": (
                "I analyzed your schedule "
                "and found optimization suggestions."
            ),
            "events": events,
            "suggestions": suggestions,
            "actions": actions
        }

    # -----------------------------------
    # UNKNOWN
    # -----------------------------------
    return {
        "reply": (
            "I couldn't understand that request."
        ),
        "events": events,
        "actions": []
    }