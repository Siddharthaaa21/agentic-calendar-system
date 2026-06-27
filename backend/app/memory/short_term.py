"""Persisted short-term session store (last events, pending actions).

The JSON file holds one entry per session id so concurrent users don't share a
single `pending_actions` queue. The active session is read from
`current_session()`. A lock guards the read-modify-write of the shared file.
"""

import json
import threading
from pathlib import Path

from app.core.session_context import current_session

_SESSION_FILE = Path(__file__).parent / "session_store.json"
_lock = threading.Lock()

_DEFAULTS: dict = {
    "last_events": [],
    "pending_actions": [],
    "last_suggestions": "",
}


def _read_all() -> dict:
    try:
        content = _SESSION_FILE.read_text().strip()
        return json.loads(content) if content else {}
    except Exception:
        return {}


def save_session(data: dict) -> None:
    with _lock:
        all_sessions = _read_all()
        all_sessions[current_session()] = data
        with open(_SESSION_FILE, "w") as f:
            json.dump(all_sessions, f, indent=2)


def get_session() -> dict:
    sess = _read_all().get(current_session())
    if not isinstance(sess, dict):
        return dict(_DEFAULTS)
    return {**_DEFAULTS, **sess}
