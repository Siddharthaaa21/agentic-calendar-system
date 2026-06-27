import json

from app.core.llm import call_llm_safe
from app.core.personas import PLANNER_PERSONA


def _batch_enrich(events: list) -> list[dict]:
    """One LLM call to classify all events instead of N separate calls."""
    if not events:
        return []

    lines = [
        f"{i + 1}. title={e.get('title', '')} | desc={str(e.get('description', ''))[:80]}"
        for i, e in enumerate(events)
    ]

    prompt = f"""{PLANNER_PERSONA}

Events:
{chr(10).join(lines)}

Return a JSON array with exactly {len(events)} objects."""

    raw = call_llm_safe(prompt, fallback="")
    try:
        cleaned = raw.strip()
        if "```" in cleaned:
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and len(parsed) == len(events):
            return parsed
    except Exception:
        pass

    return [
        {"type": "other", "importance_hint": "medium", "requires_prep": False}
    ] * len(events)


def structure_events(events: list) -> list:
    """Normalize raw Google Calendar events and enrich with a single batched LLM call."""
    normalized = []

    for e in events:
        if e.get("status") == "cancelled":
            continue

        start = e.get("start")
        if isinstance(start, dict):
            start = start.get("dateTime") or start.get("datetime") or start.get("date")

        end = e.get("end")
        if isinstance(end, dict):
            end = end.get("dateTime") or end.get("datetime") or end.get("date")

        normalized.append({
            "id": e.get("id"),
            "title": e.get("summary") or e.get("title") or "No Title",
            "start": start,
            "end": end,
            "description": e.get("description") or "",
            "status": e.get("status", "confirmed"),
        })

    if not normalized:
        return []

    enrichments = _batch_enrich(normalized)
    for event, meta in zip(normalized, enrichments):
        if isinstance(meta, dict):
            event.update(meta)

    return normalized


def find_matching_event(events: list, event_title: str):
    if not event_title:
        return None
    query = event_title.lower().strip()
    for e in events:
        if query in (e.get("title") or "").lower():
            return e
    return None
