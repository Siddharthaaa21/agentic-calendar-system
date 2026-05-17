import requests
import json
from app.core.llm import call_llm

BASE_URL = "http://127.0.0.1:8000"

# ---------------- STATE ----------------
state = {
    "history": [],
    "last_events": [],
    "pending_actions": [],
    "last_suggestions": ""
}

def interpret(user_input):
    text = user_input.lower().strip()

    # 🔥 HARD RULES FIRST (never trust LLM for control flow)
    if text in {"exit", "quit", "bye", "close"}:
        return "exit"

    if text in {"yes", "y", "do it", "go ahead"}:
        return "approve"

    if text in {"no", "n", "cancel that"}:
        return "reject"

    if "schedule" in text or "today" in text:
        return "show_schedule"

    if "cancel" in text or "reschedule" in text:
        return "modify_action"

    # 🤖 fallback to LLM
    prompt = f"""
Classify user intent into ONE of:
- show_schedule
- approve
- reject
- modify_action
- exit
- unknown

User: "{user_input}"

Return only one word.
"""
    return call_llm(prompt).strip().lower()
# ---------------- API ----------------
def get_today():
    res = requests.get(f"{BASE_URL}/today")
    return res.json()


def execute_actions(actions):
    res = requests.post(f"{BASE_URL}/execute", json={"actions": actions})
    return res.json()


def approve_action(value):
    res = requests.post(f"{BASE_URL}/approve", json={"approval": value})
    return res.json()


# ---------------- UTIL ----------------
def find_event_id(title):
    title = title.lower().strip()

    best_match = None
    best_score = 0

    for e in state.get("last_events", []):
        event_title = e["title"].lower().strip()

        score = sum(1 for w in title.split() if w in event_title)

        if score > best_score:
            best_score = score
            best_match = e

    return best_match["id"] if best_match else None


def pretty_print_schedule(data):
    print("\n📅 EVENTS:")
    for e in data.get("events", []):
        print(f"- {e['title']} ({e['priority']})")

    print("\n💡 SUGGESTIONS:")
    print(data.get("suggestions", "None"))

    print("\n⚙️ ACTIONS:")
    for a in data.get("actions", []):
        print(f"- {a['action']} → {a['title']}")


def pretty_print_results(results):
    print("\n📊 CHANGES APPLIED:\n")

    for r in results:
        eid = r.get("event_id")
        action = r.get("action")

        old = next((e for e in state["last_events"] if e["id"] == eid), None)

        if not old:
            continue

        if action == "cancel":
            print(f"❌ Cancelled: {old['title']}")

        elif action == "reschedule":
            print(f"🔁 Rescheduled: {old['title']}")
            print(f"   Old: {old['start']} → {old['end']}")
            print(f"   New: {r.get('new_start')} → {r.get('new_end')}")


# ---------------- LLM BRAIN ----------------
def planner_decide(user_input):
    context = {
        "history": state["history"][-5:],  # last 5 interactions
        "last_suggestions": state["last_suggestions"],
        "pending_actions": state["pending_actions"],
        "events": state["last_events"]
    }

    prompt = f"""
You are a smart scheduling assistant.

User said:
"{user_input}"

Context:
{json.dumps(context)}

Decide next action.

Available intents:
- fetch_schedule
- suggest_changes
- execute_actions
- modify_action
- ask_clarification
- exit
- do_nothing

Rules:
- If user asks about schedule → fetch_schedule
- If user says yes → execute_actions
- If user says cancel/reschedule → modify_action
- If unclear → ask_clarification
- If user says exit → exit

Return JSON ONLY:

{{
  "intent": "...",
  "reason": "...",
  "actions": [
    {{
      "action": "cancel",
      "event_title": "..."
    }}
  ]
}}
"""

    try:
        res = call_llm(prompt)

        start = res.find("{")
        end = res.rfind("}") + 1
        return json.loads(res[start:end])

    except:
        return {"intent": "ask_clarification", "reason": "Couldn't understand"}


# ---------------- MAIN LOOP ----------------
def run():
    print("🤖 Smart Planner Bot Started (type 'exit' to quit)\n")

    while True:
        user = input("You: ")

        decision = planner_decide(user)
        intent = decision.get("intent")

        # ---- EXIT ----
        if intent == "exit":
            print("👋 Goodbye")
            break

        # ---- FETCH SCHEDULE ----
        elif intent == "fetch_schedule":
            data = get_today()

            state["last_events"] = data.get("events", [])
            state["pending_actions"] = data.get("actions", [])
            state["last_suggestions"] = data.get("suggestions", "")

            pretty_print_schedule(data)

            if state["pending_actions"]:
                print("\n👉 Do you want me to apply these changes?")

        # ---- EXECUTE ACTIONS ----
        elif intent == "execute_actions":
            if not state["pending_actions"]:
                print("⚠️ No pending actions to execute")
                continue

            res = approve_action("yes")

            pretty_print_results(res.get("results", []))

            # refresh state
            data = get_today()
            state["last_events"] = data.get("events", [])
            state["pending_actions"] = []

        # ---- MODIFY ACTION ----
        elif intent == "modify_action":
            actions = decision.get("actions", [])

            final_actions = []

            for a in actions:
                title = a.get("event_title")
                action_type = a.get("action")

                event_id = find_event_id(title)

                if not event_id:
                    print(f"⚠️ Could not find event: {title}")
                    continue

                final_actions.append({
                    "action": action_type,
                    "event_id": event_id,
                    "title": title
                })

            if not final_actions:
                print("❌ No valid actions found")
                continue

            res = execute_actions(final_actions)

            state["pending_actions"] = res.get("pending_actions", [])

            print("\n👉 Action queued. Approve? (yes/no)")

        # ---- ASK CLARIFICATION ----
        elif intent == "ask_clarification":
            print("🤖", decision.get("reason"))

        # ---- FALLBACK ----
        else:
            print("🤔 I didn’t understand. Try:")
            print("- show my schedule")
            print("- yes, do it")
            print("- cancel interview")

        # ---- STORE HISTORY ----
        state["history"].append({
            "user": user,
            "intent": intent
        })


# ---------------- ENTRY ----------------
if __name__ == "__main__":
    run()