import json
from datetime import datetime

from app.core.llm import call_llm_safe
from app.core.personas import PRIORITIZER_PERSONA
from app.memory.long_term import get_patterns


def _compute_duration(event: dict) -> int:
    """Return event duration in minutes, or 0 if unparseable."""
    try:
        start = event.get("start", "")
        end = event.get("end", "")
        if start and end and "T" in str(start):
            s = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
            e = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
            return max(0, int((e - s).total_seconds() / 60))
    except Exception:
        pass
    return 0


def _rule_priority(event: dict) -> str:
    title = (event.get("title") or "").lower()
    importance = (event.get("importance_hint") or "").lower()
    duration = event.get("duration", 0)

    if any(kw in title for kw in ("interview", "client", "deadline", "demo", "launch")):
        return "high"
    if importance == "high":
        return "high"
    if importance == "low":
        return "low"
    if duration and duration < 20:
        return "low"
    if not event.get("description") and duration and duration < 30:
        return "low"
    return "medium"


def _batch_llm_priorities(events: list) -> list[str]:
    """Single LLM call to refine priorities for all events at once."""
    if not events:
        return []

    lines = [
        f"{i + 1}. {e.get('title', '')} | {e.get('duration', 0)}min | rule={e.get('priority', 'medium')}"
        for i, e in enumerate(events)
    ]

    prompt = f"""{PRIORITIZER_PERSONA}

Events:
{chr(10).join(lines)}

Return a JSON array of {len(events)} strings."""

    raw = call_llm_safe(prompt, fallback="")
    try:
        cleaned = raw.strip()
        if "```" in cleaned:
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and len(parsed) == len(events):
            valid = {"high", "medium", "low"}
            return [p if p in valid else events[i].get("priority", "medium") for i, p in enumerate(parsed)]
    except Exception:
        pass

    return [e.get("priority", "medium") for e in events]


def assign_priority(events: list) -> list:
    patterns = get_patterns()

    for event in events:
        event["duration"] = _compute_duration(event)
        event["priority"] = _rule_priority(event)

        title = (event.get("title") or "").lower()
        if title in patterns:
            data = patterns[title]
            if data.get("count", 0) > 5:
                event["priority"] = "high"
            if data.get("cancelled", 0) > data.get("count", 1) * 0.7:
                event["priority"] = "low"

    refined = _batch_llm_priorities(events)
    for event, priority in zip(events, refined):
        event["priority"] = priority

    return events
