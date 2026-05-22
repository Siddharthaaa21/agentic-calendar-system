from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import logging

from app.orchestrator.workflow import run_agentic_workflow
from app.core.guardrails import sanitize_output

from app.services.calendar_service import get_today_events
from app.agents.planner_agent import structure_events
from app.agents.prioritizer_agent import assign_priority
from app.agents.decision_agent import generate_decision
from app.agents.action_agent import build_actions
from app.agents.execution_agent import execute_actions

from app.memory.short_term import get_session, save_session
from app.memory.long_term import update_pattern


# ------------------ CONFIG ------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agentic Calendar System")


# ------------------ MODELS ------------------
class ActionRequest(BaseModel):
    actions: List[Dict[str, Any]] = Field(default_factory=list)


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

        # 6. Save session (IMPORTANT for approval)
        save_session({
            "pending_actions": actions,
            "last_events": prioritized,
            "last_suggestions": suggestions,
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
    current_events = session.get("last_events", [])
    if not current_events:
        current_events = get_today_events()

    updated_session = {
        "last_events": current_events,
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
    history = req.get("history", [])

    if not message:
        return {
            "status": "error",
            "reply": "Please type a message so I can help.",
            "intent": "UNKNOWN",
            "events": [],
            "conflicts": [],
            "actions": [],
            "load_pct": 0,
            "requires_confirmation": False,
            "suggestions": [],
        }

    if len(message) > 800:
        message = message[:800]

    response = run_agentic_workflow(message, conversation_history=history)
    response["reply"] = sanitize_output(response.get("reply", ""))

    return response