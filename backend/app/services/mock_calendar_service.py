"""
In-memory mock calendar backend used when DEMO_MODE=true.

Mirrors the function signatures of calendar_service.py so the rest of the
app (agents, orchestrator) doesn't need to know whether it's talking to
Google Calendar or this mock. Lets recruiters/visitors try the full
chat -> plan -> approve -> execute loop on a public deployment without
needing a Google account or OAuth credentials.

State lives in a module-level list and resets when the server restarts.
"""

import uuid
from datetime import datetime, timedelta, timezone


def _today_at(hour: int, minute: int = 0) -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat().replace("+00:00", "Z")


def _seed_events():
    return [
        {
            "id": "demo-1",
            "title": "Team Standup",
            "start": _today_at(9, 0),
            "end": _today_at(9, 30),
            "description": "Daily sync with the team",
            "status": "confirmed",
        },
        {
            "id": "demo-2",
            "title": "Interview Prep",
            "start": _today_at(10, 0),
            "end": _today_at(11, 30),
            "description": "Mock interview practice",
            "status": "confirmed",
        },
        {
            "id": "demo-3",
            "title": "Lunch",
            "start": _today_at(12, 30),
            "end": _today_at(13, 30),
            "description": "",
            "status": "confirmed",
        },
        {
            "id": "demo-4",
            "title": "Project Sync",
            "start": _today_at(13, 0),
            "end": _today_at(14, 0),
            "description": "Overlaps with lunch on purpose to demo conflict detection",
            "status": "confirmed",
        },
        {
            "id": "demo-5",
            "title": "Gym",
            "start": _today_at(18, 0),
            "end": _today_at(19, 0),
            "description": "",
            "status": "confirmed",
        },
    ]


_EVENTS = _seed_events()


def get_service():
    return None


def get_today_events():
    return [normalize_event(e) for e in _EVENTS if e.get("status") != "cancelled"]


def normalize_event(event):
    return {
        "id": event.get("id"),
        "title": event.get("title", "No Title"),
        "start": event.get("start"),
        "end": event.get("end"),
        "description": event.get("description", ""),
        "status": event.get("status"),
    }


def cancel_event(event_id: str):
    for e in _EVENTS:
        if e["id"] == event_id:
            e["status"] = "cancelled"
            return {"status": "cancelled", "event_id": event_id}
    return {"status": "FAILED", "event_id": event_id, "error": "Event not found"}


def reschedule_event(event_id: str, new_start: str, new_end: str):
    for e in _EVENTS:
        if e["id"] == event_id:
            e["start"] = new_start
            e["end"] = new_end
            return normalize_event(e)
    return {"status": "FAILED", "event_id": event_id, "error": "Event not found"}


def create_event(title: str, start_time: str, end_time: str, description: str = ""):
    event = {
        "id": f"demo-{uuid.uuid4().hex[:8]}",
        "title": title,
        "start": start_time,
        "end": end_time,
        "description": description,
        "status": "confirmed",
    }
    _EVENTS.append(event)
    return normalize_event(event)
