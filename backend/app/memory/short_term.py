import json

SESSION_FILE = "session.json"


def save_session(session_data):
    with open(SESSION_FILE, "w") as f:
        json.dump(session_data, f)


def get_session():
    try:
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "last_events": [],
            "pending_actions": [],
            "last_suggestions": ""
        }