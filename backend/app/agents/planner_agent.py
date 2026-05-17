# app/agents/planner_agent.py

import json

from app.core.llm import call_llm
from app.core.personas import PLANNER_PERSONA


# =========================================================
# EVENT ENRICHMENT
# =========================================================
def enrich_event(event):

    prompt = f"""
{PLANNER_PERSONA}

Event:
{event}
"""

    response = call_llm(prompt)

    try:

        return json.loads(response)

    except Exception:

        return {

            "type": "other",
            "importance_hint": "medium",
            "requires_prep": False
        }


# =========================================================
# STRUCTURE EVENTS
# =========================================================
def structure_events(events):

    structured = []

    for e in events:

        # skip cancelled events
        if e.get("status") == "cancelled":
            continue

        # -------------------------------
        # normalize start
        # -------------------------------
        start = e.get("start")

        if isinstance(start, dict):

            start = (
                start.get("dateTime")
                or start.get("datetime")
                or start.get("date")
            )

        # -------------------------------
        # normalize end
        # -------------------------------
        end = e.get("end")

        if isinstance(end, dict):

            end = (
                end.get("dateTime")
                or end.get("datetime")
                or end.get("date")
            )

        # -------------------------------
        # base normalized event
        # -------------------------------
        base = {

            "id": e.get("id"),

            "title":
                e.get("summary")
                or e.get("title")
                or "No Title",

            "start": start,

            "end": end,

            "description":
                e.get("description") or ""
        }

        # remove nested recursion
        if "events" in e:

            e.pop("events", None)

        # enrichment (optional metadata)
        enrichment = enrich_event(base)

        # merge
        base.update(enrichment)

        structured.append(base)

    return structured


# =========================================================
# FIND MATCHING EVENT
# =========================================================
def find_matching_event(events, event_title):

    if not event_title:

        return None

    event_title = event_title.lower().strip()

    for e in events:

        title = e.get("title", "").lower()

        if event_title in title:

            return e

    return None


# =========================================================
# DETECT SIMPLE CONFLICTS
# =========================================================
def detect_conflict(events, new_time):

    if not new_time:

        return None

    for e in events:

        existing_start = str(e.get("start", "")).lower()

        if new_time in existing_start:

            return e

    return None


# =========================================================
# BUILD ACTION PLAN
# =========================================================
def build_action_plan(intent, entities, events):

    matched_event = find_matching_event(
        events,
        entities.get("event_title")
    )

    # =====================================================
    # RESCHEDULE EVENT
    # =====================================================
    if intent == "RESCHEDULE_EVENT":

        if not matched_event:

            return {

                "status": "ERROR",

                "message": "Event not found"
            }

        conflict = detect_conflict(
            events,
            entities.get("time")
        )

        if conflict:

            return {

                "status": "CONFLICT",

                "message":
                    f"Time conflicts with "
                    f"{conflict.get('title')}",

                "conflict_event":
                    conflict.get("title"),

                "suggestions": [

                    "30 mins later",
                    "1 hour later"
                ]
            }

        return {

            "status": "READY",

            "action": "RESCHEDULE",

            "event_id":
                matched_event.get("id"),

            "target_event":
                matched_event.get("title"),

            "old_time":
                matched_event.get("start"),

            "new_time":
                entities.get("time"),

            "requires_approval": True
        }

    # =====================================================
    # DELETE EVENT
    # =====================================================
    if intent == "DELETE_EVENT":

        if not matched_event:

            return {

                "status": "ERROR",

                "message": "Event not found"
            }

        return {

            "status": "READY",

            "action": "DELETE",

            "event_id":
                matched_event.get("id"),

            "target_event":
                matched_event.get("title"),

            "requires_approval": True
        }

    # =====================================================
    # GET TODAY
    # =====================================================
    if intent == "GET_TODAY":

        return {

            "status": "INFO",

            "events": events
        }

    # =====================================================
    # SHOW CONFLICTS
    # =====================================================
    if intent == "SHOW_CONFLICTS":

        conflicts = []

        for i in range(len(events) - 1):

            current = events[i]
            nxt = events[i + 1]

            current_end = str(current.get("end"))
            next_start = str(nxt.get("start"))

            if current_end == next_start:

                conflicts.append({

                    "event_1": current.get("title"),
                    "event_2": nxt.get("title")
                })

        return {

            "status": "INFO",

            "conflicts": conflicts
        }

    # =====================================================
    # FREE SLOT
    # =====================================================
    if intent == "GET_FREE_SLOTS":

        return {

            "status": "INFO",

            "message":
                "Free slot detection not implemented yet"
        }

    # =====================================================
    # OPTIMIZE DAY
    # =====================================================
    if intent == "OPTIMIZE_DAY":

        suggestions = []

        if len(events) >= 6:

            suggestions.append(
                "Your day looks overloaded."
            )

        for e in events:

            if e.get("importance_hint") == "high":

                suggestions.append(
                    f"Prepare early for "
                    f"{e.get('title')}"
                )

        return {

            "status": "INFO",

            "suggestions": suggestions
        }

    # =====================================================
    # APPROVE ACTIONS
    # =====================================================
    if intent == "APPROVE_ACTIONS":

        return {

            "status": "APPROVED"
        }

    # =====================================================
    # REJECT ACTIONS
    # =====================================================
    if intent == "REJECT_ACTIONS":

        return {

            "status": "REJECTED"
        }

    # =====================================================
    # FALLBACK
    # =====================================================
    return {

        "status": "NO_ACTION",

        "message": "Unknown intent"
    }