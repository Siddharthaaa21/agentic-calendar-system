import re
import json

from app.core.llm import call_llm


# =====================================================
# RULE EXTRACTION
# =====================================================

TIME_REGEX = r'(\d{1,2}(?::\d{2})?\s?(?:am|pm))'


def extract_rule_entities(message: str):

    msg = message.lower()

    entities = {}

    # -----------------------------------------
    # TIME
    # -----------------------------------------

    time_match = re.search(TIME_REGEX, msg)

    if time_match:

        entities["time"] = time_match.group(1)

    # -----------------------------------------
    # EVENT TITLE
    # -----------------------------------------

    trigger_words = [
        "move",
        "reschedule",
        "shift",
        "delete",
        "remove",
        "cancel"
    ]

    words = msg.split()

    for trigger in trigger_words:

        if trigger in words:

            idx = words.index(trigger)

            remaining = words[idx + 1:]

            filtered = []

            stop_words = [
                "to",
                "at",
                "on"
            ]

            for w in remaining:

                if w in stop_words:
                    break

                filtered.append(w)

            if filtered:

                entities["event_title"] = " ".join(filtered)

            break

    return entities


# =====================================================
# LLM EXTRACTION
# =====================================================

def extract_llm_entities(message: str):

    prompt = f"""
Extract entities from the message.

Return ONLY valid JSON.

Format:
{{
    "event_title": "...",
    "time": "..."
}}

Message:
{message}
"""

    try:

        result = call_llm(prompt)

        cleaned = result.strip()

        parsed = json.loads(cleaned)

        return parsed

    except Exception as e:

        print("LLM entity extraction failed:", e)

        return {}


# =====================================================
# HYBRID
# =====================================================

def extract_entities(message: str):

    rule_entities = extract_rule_entities(message)

    llm_entities = extract_llm_entities(message)

    merged = {
        **llm_entities,
        **rule_entities
    }

    merged["source"] = "HYBRID"

    return merged