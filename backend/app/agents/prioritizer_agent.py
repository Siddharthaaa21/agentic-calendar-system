from datetime import datetime
from app.core.llm import call_llm
from app.core.personas import PRIORITIZER_PERSONA
from app.memory.long_term import get_patterns


def llm_adjust_priority(event):
    prompt = f"""
{PRIORITIZER_PERSONA}
Event:
{event}
Current priority: {event['priority']}
"""

    response = call_llm(prompt).strip().lower()

    if response in ["high", "medium", "low"]:
        return response

    return event["priority"]


def assign_priority(events):
    result = []

    patterns = get_patterns()  

    for event in events:
        priority = "medium"

        title = (event.get("title") or "").lower()
        description = (event.get("description") or "").lower()
        start = event.get("start")
        end = event.get("end")

        duration = 0
        try:
            if start and "T" in start:
                s = datetime.fromisoformat(start.replace("Z", "+00:00"))
                e = datetime.fromisoformat(end.replace("Z", "+00:00"))
                duration = (e - s).total_seconds() / 60
        except:
            pass

        # ---- RULES ----
        if "interview" in title or "client" in title:
            priority = "high"
        elif duration and duration < 30:
            priority = "low"
        elif not description:
            priority = "low"

        event["priority"] = priority
        event["duration"] = int(duration)

        if title in patterns:
            data = patterns[title]

            # frequent event → boost
            if data["count"] > 5:
                event["priority"] = "high"

            # frequently cancelled → lower importance
            if data["cancelled"] > data["count"] * 0.7:
                event["priority"] = "low"

        event["priority"] = llm_adjust_priority(event)

        result.append(event)

    return result