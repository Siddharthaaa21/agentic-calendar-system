MAX_EVENTS = 15
MAX_REPLY_LENGTH = 1500


def validate_events(events: list) -> list:
    """Filter malformed events; preserve all original fields including id."""
    if not isinstance(events, list):
        return []
    cleaned = []
    for e in events:
        if not isinstance(e, dict):
            continue
        if not e.get("start") or not e.get("end"):
            continue
        cleaned.append(e)
        if len(cleaned) >= MAX_EVENTS:
            break
    return cleaned


def sanitize_output(output: str) -> str:
    """Trim excessively long replies and de-duplicate repeated lines."""
    if not output or not isinstance(output, str):
        return "I'm not sure how to help with that."
    output = output.strip()
    if len(output) > MAX_REPLY_LENGTH:
        cut = output[:MAX_REPLY_LENGTH].rsplit(" ", 1)[0]
        output = cut + "…"
    lines = output.split("\n")
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        key = line.strip()
        if not key:
            unique.append(line)
        elif key not in seen:
            seen.add(key)
            unique.append(line)
    return "\n".join(unique)
