import json
import os

FILE_PATH = "app/memory/store.json"

def load_memory():
    if not os.path.exists(FILE_PATH):
        return {"patterns": {}}

    try:
        with open(FILE_PATH, "r") as f:
            content = f.read().strip()

            if not content:   # 🔥 empty file fix
                return {"patterns": {}}

            return json.loads(content)

    except Exception:
        return {"patterns": {}}

def save_memory(data):
    with open(FILE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def update_pattern(event_title, action=None):
    data = load_memory()
    patterns = data.get("patterns", {})

    if event_title not in patterns:
        patterns[event_title] = {
            "count": 0,
            "cancelled": 0,
            "rescheduled": 0
        }

    patterns[event_title]["count"] += 1

    if action == "cancel":
        patterns[event_title]["cancelled"] += 1
    elif action == "reschedule":
        patterns[event_title]["rescheduled"] += 1

    data["patterns"] = patterns
    save_memory(data)


def get_patterns():
    return load_memory().get("patterns", {})