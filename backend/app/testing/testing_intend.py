from app.agents.intend_agent import detect_intent


tests = [

    "what's today like",
    "show conflicts",
    "move gym to 8pm",
    "delete lunch",
    "optimize my day",
    "yes",
    "no",
    "yesterday",
    "my evening looks packed",
    "can you shift dinner later"
]

for t in tests:

    result = detect_intent(t)

    print("\n---------------------------")
    print("MESSAGE :", t)
    print("RESULT  :", result)