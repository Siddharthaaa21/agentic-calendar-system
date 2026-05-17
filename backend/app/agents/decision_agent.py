from asyncio import events
import json
from app.core.llm import call_llm

VALID_ACTIONS = {"reschedule", "cancel"}


def safe_parse_json(response: str):
    """
    Extract JSON safely from LLM response
    """
    try:
        return json.loads(response)
    except:
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except:
            return None


def rule_based_decision(events):
    """
    Deterministic fallback logic
    """
    suggestions = []
    actions = []

    events = sorted(events, key=lambda x: x["start"])

    # ---- Back-to-back detection ----
    for i in range(len(events) - 1):
        if events[i]["end"] == events[i + 1]["start"]:
            suggestions.append(
                f"Back-to-back meetings: {events[i]['title']} and {events[i+1]['title']}"
            )

    # ---- High priority overload ----
    high_streak = 0
    max_streak = 0

    for e in events:
        if e["priority"] == "high":
            high_streak += 1
            max_streak = max(max_streak, high_streak)
        else:
            high_streak = 0

    if max_streak >= 3:
        suggestions.append("Too many high-priority events consecutively")

    # ---- Low priority candidates ----
    low_events = [e for e in events if e["priority"] == "low"]

    if low_events:
        suggestions.append(
            f"Low priority events: {[e['title'] for e in low_events]}"
        )

        actions.append({
            "action": "reschedule",
            "event_title": low_events[0]["title"]
        })

    # 🔥 NEW: fallback for high-priority overload
    elif max_streak >= 3 and len(events) > 1:
        suggestions.append("Reschedule one event to reduce overload")

        actions.append({
            "action": "reschedule",
            "event_title": events[1]["title"]  # pick middle event
        })

    return {
        "suggestions": "\n".join(suggestions),
        "actions": actions
    }


def validate_actions(actions):
    """
    Ensure only valid actions pass through
    """
    valid = []

    for act in actions:
        action = act.get("action", "").lower()
        title = act.get("event_title")

        if action not in VALID_ACTIONS:
            continue

        if not title:
            continue

        valid.append({
            "action": action,
            "event_title": title
        })

    return valid


def generate_decision(events):
    # ---- Step 1: Rule-based baseline ----
    base = rule_based_decision(events)

    # ---- Step 2: LLM enhancement ----
    prompt = f"""
You are a strict scheduling assistant.

Given events:
{events}

Base suggestions:
{base['suggestions']}

Rules:
- Only choose from: "reschedule" OR "cancel"
- DO NOT write "reschedule or cancel"
- Use EXACT event titles
- Output ONLY JSON

Rules:

- ONLY return JSON

- NO text outside JSON

- MUST include at least one action if conflict exists

- Use EXACT event titles

- Allowed actions: "reschedule", "cancel"

Return:

{{

  "suggestions": "clear explanation",

  "actions": [

    {{

      "action": "reschedule",

      "event_title": "exact title"

    }}

  ]

}}
"""

    base = rule_based_decision(events)

    # 🔒 HARD LOCK — NO LLM influence on logic

    if not base["actions"]:

        return {

            "suggestions": "",

            "actions": []

        }

    # OPTIONAL: LLM only improves wording

    try:

        prompt = f"""

Improve this explanation:

{base['suggestions']}

Do NOT add new issues.

Do NOT change meaning.

"""

        improved = call_llm(prompt)

    except:

        improved = base["suggestions"]

    return {

        "suggestions": improved,

        "actions": base["actions"]

    
    }