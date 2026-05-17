# app/testing/testing_entity.py

from app.agents.entity_agent import extract_entities


tests = [

    "move gym to 8pm",

    "reschedule team meeting to 7 pm",

    "delete lunch",

    "cancel dentist appointment",

    "shift dinner to 9:30 pm",

    "move project discussion to 11 am"
]


for t in tests:

    print("\n-----------------------------")
    print("MESSAGE :", t)

    result = extract_entities(t)

    print("ENTITIES:", result)