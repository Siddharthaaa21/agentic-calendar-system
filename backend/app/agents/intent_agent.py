# app/agents/intent_agent.py

import re
import logging

from app.core.llm import call_llm

logger = logging.getLogger(__name__)


# Whole-message affirmations → approve the pending action. Anchored at both
# ends so partial commands ("okay add gym...") never match.
_AFFIRM_RE = re.compile(
    r"^(yes|yeah|yea|ya+|yep|yup|y|ok|okay|k|sure|sounds good|sounds great|"
    r"absolutely|definitely|please|approve[d]?|confirm(ed)?|go|go ahead|"
    r"go for it|go on|do it|do that|let'?s do it|lets do it|proceed|"
    r"yes please|please do|make it so|perfect)"
    r"(\s+(do|go)\s+(it|ahead|that|on|for it))?\s*[!.…]*$",
    re.IGNORECASE,
)

_REJECT_RE = re.compile(
    r"^(no|nope|nah|n|don'?t|do not|cancel|cancel that|reject|stop|never\s?mind|"
    r"forget it|no thanks|not now|no don'?t|leave it)\s*[!.…]*$",
    re.IGNORECASE,
)


RULE_INTENTS = {

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

    # Free-slot / conflict / optimize keywords are checked BEFORE GET_TODAY so
    # phrasings that also contain "today" ("any gaps today?", "conflicts today")
    # route to the more specific intent instead of a generic day summary.
    "SHOW_CONFLICTS": [
        "conflict",
        "overlap"
    ],

    "GET_FREE_SLOTS": [
        "free slot",
        "available",
        "free time",
        "gap",
        "open slot",
        "open time",
        "focus time",
        "focus window"
    ],

    "GET_TODAY": [
        "today",
        "schedule",
        "tasks",
        "all tasks",
        "todays tasks",
        "today's tasks",
        "what's today",
        "plans today",
        "the plan",
        "my day"
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
    ],

    "WHY_EXPLAIN": [
        "why",
        "why?",
        "why is that",
        "how come",
        "reason",
        "explain"
    ]
}


VALID_INTENTS = (
    "CREATE_EVENT",
    "GET_TODAY",
    "SHOW_CONFLICTS",
    "GET_FREE_SLOTS",
    "RESCHEDULE_EVENT",
    "DELETE_EVENT",
    "OPTIMIZE_DAY",
    "APPROVE_ACTIONS",
    "REJECT_ACTIONS",
    "WHY_EXPLAIN",
    "UNKNOWN",
)


def _contains_phrase(msg: str, phrase: str):
    phrase_pattern = re.escape(phrase).replace(r"\ ", r"\s+")
    # allow a trailing "s" so plural forms (e.g. "conflicts", "free slots")
    # still match singular rule phrases ("conflict", "free slot")
    pattern = rf"\b{phrase_pattern}s?\b"
    return re.search(pattern, msg) is not None


def detect_rule_intent(message: str):

    msg = message.lower().strip()

    # Approval / rejection — match the WHOLE message so natural affirmations
    # ("ya do it", "yeah go ahead", "ok do that", "sounds good") are caught,
    # while a longer command that merely starts with "ok"/"yes" ("okay add gym
    # to the slot") is NOT swallowed as an approval.
    if _AFFIRM_RE.match(msg):
        return {"intent": "APPROVE_ACTIONS", "source": "RULE"}

    if _REJECT_RE.match(msg):
        return {"intent": "REJECT_ACTIONS", "source": "RULE"}

    if (
        "best possible" in msg
        or "best way" in msg
        or "optimize" in msg
        or "optimise" in msg
        or "schedule every task" in msg
        or "what could i change" in msg
        or "what should i change" in msg
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


def detect_llm_intent(message: str, context: dict = None):

    context = context or {}
    last_intent = context.get("last_intent", "UNKNOWN")
    recent_history = context.get("conversation_history", [])[-3:]
    history_text = "\n".join([f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in recent_history])

    prompt = f"""
You are an intent classifier for a calendar assistant.

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
WHY_EXPLAIN
UNKNOWN

Important:
- CREATE_EVENT/RESCHEDULE_EVENT/DELETE_EVENT are for explicit COMMANDS that
  name a concrete action ("add X", "move X to Y", "cancel X").
- Questions that merely mention scheduling words ("where could I add time
  for X", "what's the best time", "you tell me", "what was that task?")
  are NOT commands. If the user is asking the assistant to find/suggest a
  time or slot, use GET_FREE_SLOTS or OPTIMIZE_DAY. If the user is asking
  about something said earlier, use WHY_EXPLAIN. If unsure, use UNKNOWN.

Examples:
"where could I add time for prepping for ai-103" -> GET_FREE_SLOTS
"you tell me what is the best time" -> OPTIMIZE_DAY
"what was this task we were adding?" -> WHY_EXPLAIN
"add dentist appointment at 3pm" -> CREATE_EVENT

Last assistant intent: {last_intent}
Recent conversation:
{history_text}

Current message:
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

        logger.warning("LLM intent detection failed: %s", e)

        return {
            "intent": "UNKNOWN",
            "source": "LLM"
        }


def detect_intent(message: str, context: dict = None):

    # STEP 1 → RULE DETECTION
    rule_result = detect_rule_intent(message)

    if rule_result:

        return rule_result

    # STEP 2 → LLM FALLBACK (with context)
    return detect_llm_intent(message, context=context)