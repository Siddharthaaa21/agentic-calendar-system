# app/agents/intent_agent.py

from app.core.llm import call_llm


RULE_INTENTS = {

    "GET_TODAY": [
        "today",
        "schedule",
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

    "RESCHEDULE_EVENT": [
        "move",
        "reschedule",
        "shift"
    ],

    "DELETE_EVENT": [
        "delete",
        "remove",
        "cancel"
    ],

    "OPTIMIZE_DAY": [
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


def detect_rule_intent(message: str):

    msg = message.lower().strip()

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

                if phrase in msg:

                    return {
                        "intent": intent,
                        "source": "RULE"
                    }

    return None


def detect_llm_intent(message: str):

    prompt = f"""
You are an intent classifier.

Return ONLY one intent from this list:

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