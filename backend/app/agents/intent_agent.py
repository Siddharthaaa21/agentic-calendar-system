# app/agents/intent_agent.py

import re

from app.core.llm import call_llm


RULE_INTENTS = {

    "CREATE_EVENT": [
        "add",
        "create",
    ],

    "RESCHEDULE_EVENT": [
        "reschedule",
        "move",
        "shift",
        "replace"
    ],

    "DELETE_EVENT": [
        "delete",
        "remove",
        "cancel"
    ],

    "GET_TODAY": [
        "today",
        "schedule",
        "tasks",
        "all tasks",
        "todays tasks",
        "today's tasks",
        "what's today",
        "plans today"
    ],

    "SHOW_CONFLICTS": [
        "conflict",
        "overlap"
    ],

    "GET_FREE_SLOTS": [
        "free slot",
        "available",
        "free time",
        "gap"
    ],

    "OPTIMIZE_DAY": [
        "suggestion",
        "suggest",
        "optimize",
        "improve",
        "packed",
        "too many meetings"
    ],

    "APPROVE_ACTIONS": [
        "yes",
        "approve",
        "do it"
    ],

    "REJECT_ACTIONS": [
        "no",
        "reject"
    ]
}


VALID_INTENTS = {

    "CREATE_EVENT",
    "GET_TODAY",
    "SHOW_CONFLICTS",
    "GET_FREE_SLOTS",
    "RESCHEDULE_EVENT",
    "DELETE_EVENT",
    "OPTIMIZE_DAY",
    "APPROVE_ACTIONS",
    "REJECT_ACTIONS",
    "UNKNOWN"
}


def _contains_phrase(msg: str, phrase: str):
    phrase_pattern = re.escape(phrase).replace(r"\ ", r"\s+")
    pattern = rf"\b{phrase_pattern}\b"
    return re.search(pattern, msg) is not None


def detect_rule_intent(message: str):

    msg = message.lower().strip()

    if (
        "best possible" in msg
        or "best way" in msg
        or "optimize" in msg
        or "schedule every task" in msg
    ):
        return {"intent": "OPTIMIZE_DAY", "source": "RULE"}

    # explicit scheduling verbs should map to action intents first
    if msg.startswith("reschedule ") or msg.startswith("move ") or msg.startswith("shift "):
        return {"intent": "RESCHEDULE_EVENT", "source": "RULE"}

    if msg.startswith("add ") or msg.startswith("create "):
        return {"intent": "CREATE_EVENT", "source": "RULE"}

    if msg.startswith("delete ") or msg.startswith("remove "):
        return {"intent": "DELETE_EVENT", "source": "RULE"}

    for intent, phrases in RULE_INTENTS.items():

        for phrase in phrases:

            # exact match for approval/rejection
            if intent in ["APPROVE_ACTIONS", "REJECT_ACTIONS"]:

                if msg == phrase:

                    return {
                        "intent": intent,
                        "source": "RULE"
                    }

            else:

                if _contains_phrase(msg, phrase):

                    return {
                        "intent": intent,
                        "source": "RULE"
                    }

    return None


def detect_llm_intent(message: str):

    prompt = f"""
You are an intent classifier.

Return ONLY one intent from this list:

CREATE_EVENT
GET_TODAY
SHOW_CONFLICTS
GET_FREE_SLOTS
RESCHEDULE_EVENT
DELETE_EVENT
OPTIMIZE_DAY
APPROVE_ACTIONS
REJECT_ACTIONS
UNKNOWN

Message:
{message}
"""

    try:

        result = call_llm(prompt)

        cleaned = result.strip().upper()

        for intent in VALID_INTENTS:

            if intent in cleaned:

                return {
                    "intent": intent,
                    "source": "LLM"
                }

        return {
            "intent": "UNKNOWN",
            "source": "LLM"
        }

    except Exception as e:

        print("LLM intent detection failed:", e)

        return {
            "intent": "UNKNOWN",
            "source": "LLM"
        }


def detect_intent(message: str):

    # STEP 1 → RULE DETECTION
    rule_result = detect_rule_intent(message)

    if rule_result:

        return rule_result

    # STEP 2 → LLM FALLBACK
    return detect_llm_intent(message)