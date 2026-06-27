from app.services.formatter_service import pretty_time


def format_schedule_summary(context):

    events = context["events"]

    if not events:
        return "Your calendar is completely free today."

    lines = []

    lines.append(
        f"Your day contains {len(events)} scheduled events."
    )

    if context["conflicts"]:
        n = len(context["conflicts"])
        noun = "conflict" if n == 1 else "conflicts"
        lines.append(
            f"You currently have {n} scheduling {noun}."
        )

    lines.append("")

    lines.append("Today's priorities:")

    for e in events[:4]:

        lines.append(
            f"- **{e['title']}** — {pretty_time(e['start'])}"
        )

    if context["free_slot"]:

        start, end = context["free_slot"]

        lines.append("")
        lines.append(
            f"Best available focus slot: {pretty_time(start)} to {pretty_time(end)}"
        )

    return "\n".join(lines)


def style_reply(reply, context, intent="UNKNOWN"):
    prefs = context.get("conversation_prefs", {})
    history = context.get("conversation_history", [])
    turn_index = len(history)
    last_user = ""
    for turn in reversed(history):
        if turn.get("role") == "user":
            last_user = (turn.get("content") or "").strip().lower()
            break

    openings_map = {
        "GET_TODAY": [
            "Here’s a quick read of your day.",
            "Got it — here’s what today looks like.",
            "Sure — here’s your schedule snapshot.",
        ],
        "GET_FREE_SLOTS": [
            "I checked your timeline.",
            "Great question — I scanned your day.",
            "I found the best opening in your calendar.",
        ],
        "RESCHEDULE_EVENT": [
            "I can help with that.",
            "Makes sense — here’s what I’d move.",
            "Good call — here are the best reschedule options.",
        ],
        "SHOW_CONFLICTS": [
            "I reviewed your overlaps.",
            "Here’s what’s colliding in your schedule.",
            "I spotted these conflicts.",
        ],
        "WHY_EXPLAIN": [
            "Great question.",
            "Totally fair to ask.",
            "Here’s the reasoning behind it.",
        ],
        "UNKNOWN": [
            "I’m with you.",
            "Got it.",
            "Understood.",
        ],
    }

    openings = openings_map.get(intent, openings_map["UNKNOWN"])
    opening = openings[turn_index % len(openings)]

    if prefs.get("prefers_brief"):
        body = reply.split("\n\n")[0]
    else:
        body = reply

    if body.strip().lower().startswith(("hey", "hi", "hello")):
        return body

    follow_up_cues = (
        "why",
        "how",
        "can we",
        "could we",
        "what if",
        "then",
        "ok",
        "okay",
    )
    if last_user and any(last_user.startswith(cue) for cue in follow_up_cues):
        opening = "Got you."

    if body.lower().startswith(opening.lower()):
        return body

    return f"{opening}\n\n{body}"