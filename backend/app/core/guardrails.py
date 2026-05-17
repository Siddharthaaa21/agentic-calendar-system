import json

MAX_EVENTS = 10
MAX_OUTPUT_LENGTH = 200



# INPUT GUARDRAILS
def validate_events(events):
    """
    Ensures:
    - Correct type
    - Required fields exist
    - Limits number of events
    """
    if not isinstance(events, list):
        raise ValueError("Events must be a list")

    cleaned = []

    for e in events:
        if not isinstance(e, dict):
            continue

        if not e.get("start") or not e.get("end"):
            continue

        cleaned.append({
            "title": e.get("title", "No Title"),
            "start": e.get("start"),
            "end": e.get("end"),
            "priority": e.get("priority", "medium"),
        })

        if len(cleaned) >= MAX_EVENTS:
            break

    return cleaned



# PROMPT GUARDRAILS

def build_safe_prompt(persona: str, events):
    """
    Constructs a strict prompt with rules
    """
    return f"""
{persona}

STRICT RULES:
- Only use the provided events
- Do NOT assume missing information
- Keep response under 5 lines
- Be concise and actionable
- Do NOT hallucinate

TASK:
Analyze the schedule:
- Detect overload
- Identify low priority meetings
- Suggest rescheduling or cancellation

EVENTS:
{events}
"""


# output guardrails
def sanitize_output(output: str):
    """
    Cleans and constrains LLM output
    """
    if not output or not isinstance(output, str):
        return "No suggestions available."

    output = output.strip()

    # limit length
    if len(output) > MAX_OUTPUT_LENGTH:
        output = output[:MAX_OUTPUT_LENGTH]

    # basic safety (avoid weird repetition)
    lines = output.split("\n")
    unique_lines = []
    for line in lines:
        if line.strip() and line not in unique_lines:
            unique_lines.append(line)

    return "\n".join(unique_lines[:5])  # max 5 lines


# for making the output more structured in future iteration
def enforce_json_output(output: str):
    """
    Try to enforce structured output (optional future use)
    """
    try:
        return json.loads(output)
    except:
        return {"suggestions": output}