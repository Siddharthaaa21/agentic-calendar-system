"""In-memory conversation state, isolated per session.

Each session id gets its own bucket so one user's draft event, awaited title,
or conversation turns never leak into another's. The active session is read
from `current_session()` (set per request at the API entry point).
"""

from app.core.session_context import current_session

# session_id -> {key: value, "turns": [...]}
_sessions: dict = {}


def _new_bucket() -> dict:
    return {
        "last_focus_slot": None,
        "last_suggested_action": None,
        "last_intent": None,
        "turns": [],
    }


def _bucket() -> dict:
    return _sessions.setdefault(current_session(), _new_bucket())


def save_memory(key, value):
    _bucket()[key] = value


def get_memory(key):
    return _bucket().get(key)


def append_turn(role, content):
    bucket = _bucket()
    turns = bucket.get("turns", [])
    turns.append({"role": role, "content": content})
    bucket["turns"] = turns[-20:]


def get_recent_turns(limit=8):
    return _bucket().get("turns", [])[-limit:]


def reset_session(session_id: str = None) -> None:
    """Drop a session's state (used by tests and explicit resets)."""
    from app.core.session_context import current_session as _cs
    _sessions.pop(session_id or _cs(), None)
