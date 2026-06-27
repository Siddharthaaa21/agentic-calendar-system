"""Persisted short-term session store (last events, pending actions).

The JSON file holds one entry per session id so concurrent users don't share a
single `pending_actions` queue. The active session is read from
`current_session()`. A lock guards the read-modify-write of the shared file.
"""

import json
import os
import tempfile
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


def _atomic_write(payload: dict) -> None:
    """Write JSON to a temp file in the same dir, then atomically rename it in.

    os.replace is atomic on POSIX/Windows, so a crash mid-write can never leave
    a truncated file that _read_all would silently treat as empty (wiping state).
    """
    fd, tmp = tempfile.mkstemp(dir=str(_SESSION_FILE.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, _SESSION_FILE)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def save_session(data: dict) -> None:
    with _lock:
        all_sessions = _read_all()
        all_sessions[current_session()] = data
        _atomic_write(all_sessions)


def get_session() -> dict:
    sess = _read_all().get(current_session())
    if not isinstance(sess, dict):
        return dict(_DEFAULTS)
    return {**_DEFAULTS, **sess}
