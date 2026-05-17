import re

VALID_ACTIONS = {"reschedule", "cancel"}

def parse_actions(suggestions: str):
    """
    Extract simple actions from LLM text
    """
    actions = []

    lines = suggestions.lower().split("\n")

    for line in lines:
        if "reschedule" in line:
            actions.append({"action": "reschedule", "target": line})

        elif "cancel" in line:
            actions.append({"action": "cancel", "target": line})

    return actions


def match_event(target_text, events):
    target_text = target_text.lower().strip()

    for event in events:
        title = event.get("title", "").lower().strip()

        if target_text in title:
            return event

    return None

def build_actions(events, actions_from_llm):
    final_actions = []

    for act in actions_from_llm:
        action_type = act.get("action", "").lower()

        if action_type not in VALID_ACTIONS:
            continue

        title = act.get("event_title", "").lower().strip()

        event = match_event(title, events)

        if not event:
            print(f"⚠️ No match for: {title}")
            continue

        final_actions.append({
            "action": action_type,
            "event_id": event["id"],
            "title": event["title"],
            "status": "DRY_RUN"
        })

    return final_actions