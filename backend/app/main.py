import logging
import os
import secrets
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
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
if _allowed_origins == "*":
    # Wildcard CORS lets any website call this API from a victim's browser.
    # Combined with an unset API_KEY that means a fully open, drive-able
    # calendar-mutation API — only acceptable for a throwaway local demo.
    logger.warning(
        "ALLOWED_ORIGINS='*' — CORS is wide open. Set it to your frontend "
        "origin(s) for any real deployment."
    )
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


# ── Auth ────────────────────────────────────────────────────────────────────
# Optional shared-secret auth. When API_KEY is set, every endpoint requires a
# matching `X-API-Key` header. When it's unset (e.g. local dev / DEMO_MODE
# public demo), the API stays open so visitors can try it freely.
_API_KEY = os.getenv("API_KEY", "").strip()
_DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: str = Security(_api_key_header)) -> None:
    if not _API_KEY:
        return  # auth disabled (only reachable in DEMO_MODE — see fail-closed check below)
    # Constant-time compare to avoid leaking the key via timing.
    if not provided or not secrets.compare_digest(provided, _API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


# Fail closed: a real (non-demo) deployment must not boot wide open. Without an
# API_KEY the mutation endpoints would let anyone read/edit/delete the connected
# calendar, so we refuse to start instead of silently exposing it. DEMO_MODE
# uses an in-memory mock calendar, so leaving it open there is harmless.
if not _API_KEY:
    if not _DEMO_MODE:
        raise RuntimeError(
            "API_KEY is not set and DEMO_MODE is off. Refusing to start an "
            "UNAUTHENTICATED API against a real calendar. Set API_KEY (generate "
            "one with: python -c 'import secrets; print(secrets.token_urlsafe(32))') "
            "or set DEMO_MODE=true for a throwaway demo."
        )
    logger.warning(
        "API_KEY is not set — the API is UNAUTHENTICATED (allowed because "
        "DEMO_MODE=true). Never run a real calendar this way."
    )


# ── Request models ────────────────────────────────────────────────────────────

class ActionRequest(BaseModel):
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    session_id: str = "default"


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok", "service": "axon-calendar"}


# ── Today pipeline ────────────────────────────────────────────────────────────

@app.get("/today", dependencies=[Depends(require_api_key)])
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

@app.post("/chat", dependencies=[Depends(require_api_key)])
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

@app.post("/execute", dependencies=[Depends(require_api_key)])
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

@app.post("/approve", dependencies=[Depends(require_api_key)])
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
