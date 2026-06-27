from app.orchestrator.workflow import run_agentic_workflow

tests = [
    "what's for today",
    "show conflicts",
    "free slots",
    "move gym to 8pm",
    "delete lunch",
    "yes",
    "no",
]

for t in tests:
    print("\n====================================")
    print("MESSAGE:", t)
    result = run_agentic_workflow(t)
    print("\nREPLY:")
    print(result["reply"])
    print("\nACTIONS:")
    print(result.get("actions"))
