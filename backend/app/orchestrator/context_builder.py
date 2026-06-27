import time
from datetime import datetime

from app.core.session_context import current_session
from app.services.calendar_service import get_today_events
from app.tasks.scheduler import find_free_slot
from app.memory.state_manager import load_preferences
from app.memory.session_memory import get_recent_turns
from app.core.guardrails import validate_events
from app.agents.planner_agent import structure_events
from app.agents.prioritizer_agent import assign_priority

# ---------------------------------------------------------------------------
# Event cache: avoid hitting the Google Calendar API on every chat message.
# Keyed per session so one user's calendar never leaks into another user's
# context/replies on a shared backend (real multi-user, non-demo mode).
# ---------------------------------------------------------------------------
_cache: dict = {}  # session_id -> {"events": list, "ts": float}
_CACHE_TTL = 300  # seconds (5 minutes)


def invalidate_event_cache() -> None:
    """Call this after a calendar mutation so the next request fetches fresh data."""
    _cache.pop(current_session(), None)


def _get_events() -> list:
    now = time.monotonic()
    session = current_session()
    entry = _cache.get(session)
    if entry is None or (now - entry["ts"]) > _CACHE_TTL:
        # Enrich + prioritize here too (not just in /today) so the chat path's
        # events carry a `priority` field. Without this, the high-priority
        # reschedule guard and the optimize/reschedule workflows can't see it.
        # Result is cached for _CACHE_TTL so the extra LLM calls don't run per
        # message.
        structured = structure_events(get_today_events())
        entry = {"events": validate_events(assign_priority(structured)), "ts": now}
        _cache[session] = entry
    return entry["events"]


# ---------------------------------------------------------------------------
# Load percentage — based on actual meeting minutes vs a 10-hour workday
# ---------------------------------------------------------------------------
def compute_load(events: list) -> int:
    workday_minutes = 10 * 60
    total = 0
    for e in events:
        try:
            s = datetime.fromisoformat(str(e["start"]).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(e["end"]).replace("Z", "+00:00"))
            total += max(0, int((end - s).total_seconds() / 60))
        except Exception:
            total += 30
    return min(int(total / workday_minutes * 100), 100)


# ---------------------------------------------------------------------------
# Conversation preference inference
# ---------------------------------------------------------------------------
def _infer_conversation_prefs(history: list) -> dict:
    if not history:
        return {}
    recent_user = [
        item.get("content", "")
        for item in history
        if item.get("role") == "user"
    ][-5:]
    merged = " ".join(recent_user).lower()
    return {
        "prefers_brief": any(t in merged for t in ("short", "brief", "quick", "tldr")),
        "wants_explanation": any(t in merged for t in ("why", "explain", "reason")),
    }


# ---------------------------------------------------------------------------
# Main context builder
# ---------------------------------------------------------------------------
def build_context(conversation_history: list = None) -> dict:
    conversation_history = conversation_history or get_recent_turns(limit=8)

    events = _get_events()

    sorted_events = sorted(events, key=lambda x: str(x.get("start", "")))
    conflicts = []
    for i in range(len(sorted_events) - 1):
        curr_end = str(sorted_events[i].get("end", ""))
        next_start = str(sorted_events[i + 1].get("start", ""))
        if curr_end > next_start:
            conflicts.append({
                "title": (
                    f"{sorted_events[i]['title']} overlaps with "
                    f"{sorted_events[i + 1]['title']}"
                )
            })

    free_slot = find_free_slot(events, 60)
    load_pct = compute_load(events)

    return {
        "events": events,
        "conflicts": conflicts,
        "free_slot": free_slot,
        "load_pct": load_pct,
        "preferences": load_preferences(),
        "conversation_history": conversation_history,
        "conversation_prefs": _infer_conversation_prefs(conversation_history),
    }
