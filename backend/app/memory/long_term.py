import json
import os
import tempfile
import threading
from pathlib import Path

_STORE_FILE = Path(__file__).parent / "store.json"
# Guards the read-modify-write in update_pattern so concurrent requests don't
# clobber each other's increments.
_lock = threading.Lock()


def _load() -> dict:
    if not _STORE_FILE.exists():
        return {"patterns": {}}
    try:
        content = _STORE_FILE.read_text().strip()
        return json.loads(content) if content else {"patterns": {}}
    except Exception:
        return {"patterns": {}}


def _save(data: dict) -> None:
    # Atomic write: temp file + rename, so a crash mid-write can't truncate the
    # store into invalid JSON (which _load would silently reset, losing all
    # learned patterns).
    fd, tmp = tempfile.mkstemp(dir=str(_STORE_FILE.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _STORE_FILE)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def update_pattern(event_title: str, action: str = None) -> None:
    with _lock:
        data = _load()
        patterns = data.setdefault("patterns", {})
        entry = patterns.setdefault(
            event_title, {"count": 0, "cancelled": 0, "rescheduled": 0}
        )
        entry["count"] += 1
        if action == "cancel":
            entry["cancelled"] += 1
        elif action == "reschedule":
            entry["rescheduled"] += 1
        _save(data)


def get_patterns() -> dict:
    return _load().get("patterns", {})
