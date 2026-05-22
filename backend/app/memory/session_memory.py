memory_store = {
    "last_focus_slot": None,
    "last_suggested_action": None,
    "last_intent": None,
    "turns": []
}


def save_memory(key, value):
    memory_store[key] = value


def get_memory(key):
    return memory_store.get(key)


def append_turn(role, content):
    turns = memory_store.get("turns", [])
    turns.append({
        "role": role,
        "content": content
    })
    memory_store["turns"] = turns[-20:]


def get_recent_turns(limit=8):
    turns = memory_store.get("turns", [])
    return turns[-limit:]