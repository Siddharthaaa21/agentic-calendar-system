from app.orchestrator import workflow as wf
from app.memory import session_memory


FAKE_EVENTS = [
    {
        "id": "evt_finish",
        "title": "finish project",
        "start": "2026-05-19T08:00:00Z",
        "end": "2026-05-19T09:00:00Z",
        "priority": "medium",
    },
    {
        "id": "evt_interview",
        "title": "interview",
        "start": "2026-05-19T09:30:00Z",
        "end": "2026-05-19T10:30:00Z",
        "priority": "medium",
    },
    {
        "id": "evt_prep",
        "title": "interview prep",
        "start": "2026-05-19T12:00:00Z",
        "end": "2026-05-19T13:00:00Z",
        "priority": "medium",
    },
    {
        "id": "evt_checking",
        "title": "checking",
        "start": "2026-05-19T13:30:00Z",
        "end": "2026-05-19T14:30:00Z",
        "priority": "medium",
    },
]


def reset_state():
    # Clear every session bucket so each regression run starts clean.
    session_memory._sessions.clear()


def patch_workflow_dependencies():
    fake_session = {
        "pending_actions": [],
        "last_events": FAKE_EVENTS,
        "last_suggestions": "",
    }

    def fake_get_session():
        return fake_session

    def fake_save_session(payload):
        # Snapshot first: callers sometimes pass the live session dict back in
        # (save_session(get_session())), so clearing before copying would wipe
        # it. The real file-backed save_session round-trips through JSON and
        # never aliases like this.
        snapshot = dict(payload)
        fake_session.clear()
        fake_session.update(snapshot)

    def fake_execute_actions(actions):
        return [{"status": "EXECUTED", "action": action.get("action")} for action in actions]

    def fake_build_context(conversation_history=None):
        return {
            "events": FAKE_EVENTS,
            "conflicts": [],
            "free_slot": ("2026-05-19T15:45:00Z", "2026-05-19T16:45:00Z"),
            "load_pct": 75,
            "preferences": {},
            "conversation_history": conversation_history or [],
            "conversation_prefs": {},
        }

    wf.get_session = fake_get_session
    wf.save_session = fake_save_session
    wf.execute_actions = fake_execute_actions
    wf.build_context = fake_build_context


def check(condition, label, details=None):
    if condition:
        print(f"✅ {label}")
        return True
    print(f"❌ {label}")
    if details:
        print(f"   {details}")
    return False


def run_regression_suite():
    reset_state()
    patch_workflow_dependencies()

    passes = []

    r1 = wf.run_agentic_workflow("remove checking", conversation_history=[])
    passes.append(
        check(
            r1.get("intent") == "DELETE_EVENT" and len(r1.get("actions", [])) == 1,
            "remove checking -> DELETE_EVENT with one action",
            r1,
        )
    )

    r2 = wf.run_agentic_workflow("todays tasks", conversation_history=[])
    passes.append(
        check(
            r2.get("intent") == "GET_TODAY" and not r2.get("actions"),
            "todays tasks -> GET_TODAY and no create/delete action",
            r2,
        )
    )

    r3 = wf.run_agentic_workflow("all tasks?", conversation_history=[])
    passes.append(
        check(
            r3.get("intent") == "GET_TODAY" and not r3.get("actions"),
            "all tasks? -> GET_TODAY and not hijacked by stale draft",
            r3,
        )
    )

    r4 = wf.run_agentic_workflow("add a new task named paper prep", conversation_history=[])
    passes.append(
        check(
            r4.get("intent") == "CREATE_EVENT" and not r4.get("actions"),
            "create with title only -> asks for time (no executable action yet)",
            r4,
        )
    )

    r5 = wf.run_agentic_workflow("then 9 pm", conversation_history=[])
    actions5 = r5.get("actions", [])
    passes.append(
        check(
            r5.get("intent") == "CREATE_EVENT"
            and len(actions5) == 1
            and actions5[0].get("action") == "create"
            and "paper prep" in actions5[0].get("title", "").lower(),
            "then 9 pm -> creates pending CREATE action for draft title",
            r5,
        )
    )

    r6 = wf.run_agentic_workflow("no", conversation_history=[])
    passes.append(
        check(
            r6.get("intent") == "REJECT_ACTIONS" and "discarded" in r6.get("reply", "").lower(),
            "no -> rejects pending actions",
            r6,
        )
    )

    # Multi-turn create must survive all the way through approval. The chat
    # fast-path builds the CREATE action and says "Approve when you're ready";
    # if that action isn't persisted to pending_actions, the follow-up "yes"
    # finds nothing pending. Regression guard for that exact bug.
    reset_state()
    wf.run_agentic_workflow("add yoga", conversation_history=[])
    r7 = wf.run_agentic_workflow("8am", conversation_history=[])
    passes.append(
        check(
            r7.get("intent") == "CREATE_EVENT" and len(r7.get("actions", [])) == 1,
            "add yoga -> 8am -> pending CREATE action",
            r7,
        )
    )
    r8 = wf.run_agentic_workflow("yes", conversation_history=[])
    passes.append(
        check(
            r8.get("intent") == "APPROVE_ACTIONS"
            and "applied" in r8.get("reply", "").lower(),
            "yes -> applies the pending multi-turn CREATE (not 'nothing pending')",
            r8,
        )
    )

    total = len(passes)
    passed = sum(1 for item in passes if item)
    print("\n---------------------------------")
    print(f"Regression result: {passed}/{total} passed")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_regression_suite()
