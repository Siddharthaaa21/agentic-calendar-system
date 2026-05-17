conversation_state = {
    "pending_intent": None,
    "pending_action": None,
    "awaiting_confirmation": False
}


def set_pending_action(data):
    global conversation_state

    conversation_state["pending_intent"] = data.get("intent")
    conversation_state["pending_action"] = data
    conversation_state["awaiting_confirmation"] = True


def get_pending_action():
    return conversation_state


def clear_pending_action():
    global conversation_state

    conversation_state = {
        "pending_intent": None,
        "pending_action": None,
        "awaiting_confirmation": False
    }