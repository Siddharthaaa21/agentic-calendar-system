# app/testing/testing_conversation.py

from app.agents.conversation_agent import process_message


tests = [

    "what's for today",

    "show conflicts",

    "free slots",

    "move gym to 8pm",

    "delete lunch",

    "yes",

    "no"
]


for t in tests:

    print("\n====================================")
    print("MESSAGE:", t)

    result = process_message(t)

    print("\nREPLY:")
    print(result["reply"])

    print("\nACTIONS:")
    print(result.get("actions"))