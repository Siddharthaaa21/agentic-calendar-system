import logging
import os
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.orchestrator.workflow import run_agentic_workflow
from app.orchestrator.context_builder import compute_load, invalidate_event_cache
from app.orchestrator.response_formatter import format_schedule_summary
from app.core.guardrails import sanitize_output
from app.core.session_context import set_session

from app.services.calendar_service import get_today_events
from app.agents.planner_agent import structure_events
from app.agents.prioritizer_agent import assign_priority

from app.memory.short_term import get_session, save_session
from app.tasks.scheduler import find_free_slot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Axon — Agentic Calendar System")

# Default to localhost-only so a fresh deployment isn't a wide-open,
# credential-free calendar-mutation API. Set ALLOWED_ORIGINS (comma-separated)
# to the deployed frontend origin(s) in production.
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allowed_origins == "*" else [o.strip() for o in _allowed_origins.split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cap how many actions a single request may queue/execute — prevents a
# malicious or buggy client from burning the Google Calendar API quota.
MAX_ACTIONS_PER_REQUEST = 25


# ── Request models ────────────────────────────────────────────────────────────

class ActionRequest(BaseModel):
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    session_id: str = "default"


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok", "service": "axon-calendar"}


# ── Today pipeline ────────────────────────────────────────────────────────────

@app.get("/today")
def today_events(session_id: str = "default"):
    """
    Full pipeline: fetch → structure → prioritize → detect conflicts → return.
    Also persists events to session so /chat and /approve can reference them.
    """
    set_session(session_id)
    try:
        raw = get_today_events()
        if not raw:
            return {"events": [], "conflicts": [], "suggestions": "No events today.", "actions": [], "load_pct": 0}

        structured = structure_events(raw)
        prioritized = assign_priority(structured)

        sorted_evs = sorted(prioritized, key=lambda x: str(x.get("start", "")))
        conflicts = []
        for i in range(len(sorted_evs) - 1):
            if str(sorted_evs[i].get("end", "")) > str(sorted_evs[i + 1].get("start", "")):
                conflicts.append({
                    "title": f"{sorted_evs[i]['title']} overlaps with {sorted_evs[i + 1]['title']}"
                })

        free_slot = find_free_slot(prioritized, 60)
        load_pct = compute_load(prioritized)

        save_session({
            "last_events": prioritized,
            "pending_actions": [],
            "last_suggestions": "",
        })
        invalidate_event_cache()

        context = {
            "events": prioritized,
            "conflicts": conflicts,
            "free_slot": free_slot,
            "load_pct": load_pct,
        }

        return {
            "events": prioritized,
            "conflicts": conflicts,
            "suggestions": format_schedule_summary(context),
            "actions": [],
            "load_pct": load_pct,
            "free_slot": free_slot,
        }

    except Exception:
        logger.exception("/today failed")
        return {"events": [], "conflicts": [], "suggestions": "Couldn't fetch your schedule right now.", "actions": [], "load_pct": 0}


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(req: dict):
    set_session(req.get("session_id", "default"))
    message = req.get("message", "").strip()
    history = req.get("history", [])

    if not message:
        return {
            "status": "error",
            "reply": "Please type a message so I can help.",
            "intent": "UNKNOWN",
            "events": [], "conflicts": [], "actions": [],
            "load_pct": 0, "requires_confirmation": False, "suggestions": [],
        }

    message = message[:800]

    response = run_agentic_workflow(message, conversation_history=history) or {
        "status": "error",
        "reply": "An unexpected error occurred.",
        "intent": "UNKNOWN",
        "events": [], "conflicts": [], "actions": [],
        "load_pct": 0, "requires_confirmation": False, "suggestions": [],
    }

    response["reply"] = sanitize_output(response.get("reply", ""))
    return response


# ── Execute (queue actions) ───────────────────────────────────────────────────

@app.post("/execute")
def execute(payload: ActionRequest):
    set_session(payload.session_id)
    if len(payload.actions) > MAX_ACTIONS_PER_REQUEST:
        raise HTTPException(
            status_code=413,
            detail=f"Too many actions (max {MAX_ACTIONS_PER_REQUEST}).",
        )
    session = get_session()
    session["pending_actions"] = payload.actions
    save_session(session)
    return {"message": "Actions queued for approval", "pending_actions": payload.actions}


# ── Approve (HITL gate) ───────────────────────────────────────────────────────

@app.post("/approve")
def approve(req: dict):
    set_session(req.get("session_id", "default"))
    if req.get("approval") != "yes":
        session = get_session()
        session["pending_actions"] = []
        save_session(session)
        return {"message": "Actions rejected"}

    from app.agents.execution_agent import execute_actions
    session = get_session()
    actions = session.get("pending_actions", [])
    results = execute_actions(actions)

    session["pending_actions"] = []
    save_session(session)
    invalidate_event_cache()

    return {"message": "Actions executed", "results": results}
