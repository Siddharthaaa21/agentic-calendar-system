import json
import os

BASE_DIR = os.path.dirname(__file__)
PREFERENCES_FILE = os.path.join(BASE_DIR, "preferences.json")


def _read_json(path, fallback=None):
    fallback = fallback if fallback is not None else {}
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as file_obj:
            content = file_obj.read().strip()
            if not content:
                return fallback
            return json.loads(content)
    except Exception:
        return fallback


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, indent=2)


def save_preferences(preferences):
    _write_json(PREFERENCES_FILE, preferences)


def load_preferences():
    default_preferences = {
        "preferred_focus_time": "morning",
        "avoid_evening_meetings": False,
    }

    preferences = _read_json(PREFERENCES_FILE, fallback=default_preferences)
    if preferences == default_preferences and not os.path.exists(PREFERENCES_FILE):
        save_preferences(default_preferences)
    return preferences