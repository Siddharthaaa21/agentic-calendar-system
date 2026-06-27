import json
from pathlib import Path

_STORE_FILE = Path(__file__).parent / "store.json"


def _load() -> dict:
    if not _STORE_FILE.exists():
        return {"patterns": {}}
    try:
        content = _STORE_FILE.read_text().strip()
        return json.loads(content) if content else {"patterns": {}}
    except Exception:
        return {"patterns": {}}


def _save(data: dict) -> None:
    _STORE_FILE.write_text(json.dumps(data, indent=2))


def update_pattern(event_title: str, action: str = None) -> None:
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
