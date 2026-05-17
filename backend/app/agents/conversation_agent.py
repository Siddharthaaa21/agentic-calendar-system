# app/agents/conversation_agent.py

from app.agents.intend_agent import detect_intent
from app.agents.entity_agent import extract_entities

from app.memory.short_term import get_session, save_session

from app.services.calendar_service import (
    get_today_events,
    cancel_event,
    reschedule_event
)

from app.agents.planner_agent import structure_events
from app.agents.prioritizer_agent import assign_priority

from app.agents.execution_agent import execute_actions

from app.tasks.scheduler import find_free_slot


# =========================================================
# HELPERS
# =========================================================

def summarize_today(events):

    if not events:
        return "You have no events scheduled for today."

    lines = []

    for e in events:

        title = e.get("title", "Untitled")
        start = e.get("start", "")
        end = e.get("end", "")

        lines.append(f"• {title} ({start} → {end})")

    return "\n".join(lines)


def summarize_conflicts(events):

    conflicts = []

    for i in range(len(events) - 1):

        current = events[i]
        nxt = events[i + 1]

        current_end = current.get("end")
        next_start = nxt.get("start")

        if current_end and next_start:

            if current_end > next_start:

                conflicts.append(
                    f"{current['title']} overlaps with {nxt['title']}"
                )

    return conflicts


# =========================================================
# MAIN ORCHESTRATOR
# =========================================================

def process_message(message: str):

    # -----------------------------------------------------
    # SESSION
    # -----------------------------------------------------

    session = get_session()

    # -----------------------------------------------------
    # INTENT
    # -----------------------------------------------------

    intent_data = detect_intent(message)

    intent = intent_data.get("intent", "UNKNOWN")

    # -----------------------------------------------------
    # ENTITIES
    # -----------------------------------------------------

    entities = extract_entities(message)

    # -----------------------------------------------------
    # FETCH EVENTS
    # -----------------------------------------------------

    raw_events = get_today_events()

    structured = structure_events(raw_events)

    prioritized = assign_priority(structured)

    # save latest events in memory
    session["last_events"] = prioritized
    save_session(session)

    # =====================================================
    # GET TODAY
    # =====================================================

    if intent == "GET_TODAY":

        summary = summarize_today(prioritized)

        return {
            "reply": f"Here’s your schedule for today:\n\n{summary}",
            "events": prioritized,
            "actions": [],
            "conflicts": []
        }

    # =====================================================
    # SHOW CONFLICTS
    # =====================================================

    elif intent == "SHOW_CONFLICTS":

        conflicts = summarize_conflicts(prioritized)

        if not conflicts:

            reply = "No conflicts found in your schedule."

        else:

            bullets = "\n".join([f"• {c}" for c in conflicts])

            reply = f"I found these conflicts:\n\n{bullets}"

        return {
            "reply": reply,
            "events": prioritized,
            "actions": [],
            "conflicts": conflicts
        }

    # =====================================================
    # GET FREE SLOTS
    # =====================================================

    elif intent == "GET_FREE_SLOTS":

        slot = find_free_slot(prioritized, 60)

        if not slot:

            reply = "I couldn't find a free slot today."

        else:

            start, end = slot

            reply = (
                f"You have a free slot from "
                f"{start} to {end}."
            )

        return {
            "reply": reply,
            "events": prioritized,
            "actions": [],
            "conflicts": []
        }

    # =====================================================
    # RESCHEDULE EVENT
    # =====================================================

    elif intent == "RESCHEDULE_EVENT":

        event_title = entities.get("event_title")
        new_time = entities.get("time")

        if not event_title:

            return {
                "reply": "Which event would you like to reschedule?",
                "events": prioritized,
                "actions": [],
                "conflicts": []
            }

        matched_event = None

        for e in prioritized:

            title = e.get("title", "").lower()

            if event_title.lower() in title:

                matched_event = e
                break

        if not matched_event:

            return {
                "reply": f"I couldn't find '{event_title}' in your calendar.",
                "events": prioritized,
                "actions": [],
                "conflicts": []
            }

        # ---------------------------------------------
        # create pending action
        # ---------------------------------------------

        action = {
            "id": f"reschedule_{matched_event['id']}",
            "action": "reschedule",
            "event_id": matched_event["id"],
            "title": matched_event["title"],
            "requested_time": new_time
        }

        session["pending_actions"] = [action]

        save_session(session)

        return {
            "reply": (
                f"I can move '{matched_event['title']}' "
                f"to {new_time}. Approve?"
            ),
            "events": prioritized,
            "actions": [action],
            "conflicts": []
        }

    # =====================================================
    # DELETE EVENT
    # =====================================================

    elif intent == "DELETE_EVENT":

        event_title = entities.get("event_title")

        if not event_title:

            return {
                "reply": "Which event would you like me to delete?",
                "events": prioritized,
                "actions": [],
                "conflicts": []
            }

        matched_event = None

        for e in prioritized:

            title = e.get("title", "").lower()

            if event_title.lower() in title:

                matched_event = e
                break

        if not matched_event:

            return {
                "reply": f"I couldn't find '{event_title}' in your calendar.",
                "events": prioritized,
                "actions": [],
                "conflicts": []
            }

        action = {
            "id": f"delete_{matched_event['id']}",
            "action": "cancel",
            "event_id": matched_event["id"],
            "title": matched_event["title"]
        }

        session["pending_actions"] = [action]

        save_session(session)

        return {
            "reply": (
                f"I can delete '{matched_event['title']}'. "
                f"Approve?"
            ),
            "events": prioritized,
            "actions": [action],
            "conflicts": []
        }

    # =====================================================
    # APPROVE ACTIONS
    # =====================================================

    elif intent == "APPROVE_ACTIONS":

        pending = session.get("pending_actions", [])

        if not pending:

            return {
                "reply": "There are no pending actions to approve.",
                "events": prioritized,
                "actions": [],
                "conflicts": []
            }

        results = execute_actions(pending)

        session["pending_actions"] = []

        save_session(session)

        return {
            "reply": "Approved. The actions were executed successfully.",
            "events": prioritized,
            "actions": [],
            "conflicts": [],
            "results": results
        }

    # =====================================================
    # REJECT ACTIONS
    # =====================================================

    elif intent == "REJECT_ACTIONS":

        session["pending_actions"] = []

        save_session(session)

        return {
            "reply": "Okay, I discarded the pending actions.",
            "events": prioritized,
            "actions": [],
            "conflicts": []
        }

    # =====================================================
    # UNKNOWN
    # =====================================================

    return {
        "reply": (
            "I understood your message, "
            "but I don't know how to handle it yet."
        ),
        "events": prioritized,
        "actions": [],
        "conflicts": []
    }