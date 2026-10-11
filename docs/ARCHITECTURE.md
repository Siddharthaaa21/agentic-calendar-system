# Axon — End-to-End Architecture & Working

> **Axon** is a conversational agent that manages your Google Calendar in plain English.
> You talk to it ("move gym to 8pm", "what's free this afternoon?"), it reasons over your
> day with a multi-agent pipeline, proposes concrete actions, and **never touches your
> calendar without explicit approval** (human-in-the-loop).

This document explains how the whole system fits together — from a keystroke in the UI to
a mutation on Google Calendar — grounded in the actual code.

---

## 1. The 10,000-foot view

```
┌──────────────┐        HTTP/JSON         ┌────────────────────────────────────┐
│  Streamlit   │ ───────────────────────► │            FastAPI backend          │
│  frontend    │   /today /chat           │  app/main.py                        │
│ (app.py)     │   /execute /approve      │                                     │
│              │ ◄─────────────────────── │  ┌──────────────────────────────┐   │
└──────────────┘     JSON responses       │  │   Orchestrator (workflow.py) │   │
       ▲                                   │  │  intent → entity → route →   │   │
       │ renders chat + dashboard          │  │  workflow → format           │   │
       │                                   │  └──────────────────────────────┘   │
       │                                   │     │            │           │       │
       │                                   │   agents/      memory/   services/   │
       │                                   │  intent        session   calendar    │
       │                                   │  entity        short     (real/mock) │
       │                                   │  planner       long      ↕           │
       │                                   │  prioritizer   state   Google Cal API │
       │                                   │  execution                            │
       └───────────────────────────────────┴───── core/llm.py → Anthropic | Groq ─┘
```

- **Frontend** — Streamlit (`frontend/app.py`). Pure HTTP client; holds no business logic.
- **Backend** — FastAPI (`backend/app/main.py`). Five endpoints, optional API-key auth.
- **Orchestrator** — turns a message into a structured response via a fixed pipeline.
- **Agents** — focused units (intent, entity, planner, prioritizer, execution).
- **Memory** — session conversation state, persisted pending actions, long-term patterns.
- **Services** — Google Calendar API, or an in-memory mock for `DEMO_MODE`.
- **Core** — the LLM provider abstraction, guardrails, personas, per-request session context.

Both Anthropic (Claude, default) and Groq (Llama) are supported behind one `call_llm()`
abstraction, selected by the `LLM_PROVIDER` env var.

---

## 2. The HTTP surface (`backend/app/main.py`)

| Method | Path       | Auth | Purpose |
|--------|------------|------|---------|
| `GET`  | `/`        | open | Health check → `{"status":"ok","service":"axon-calendar"}` |
| `GET`  | `/today`   | gated | Build today's structured, prioritized schedule |
| `POST` | `/chat`    | gated | Run a user message through the agent pipeline |
| `POST` | `/execute` | gated | Queue proposed actions for approval (HITL step 1) |
| `POST` | `/approve` | gated | Commit or discard queued actions (HITL step 2) |

**Auth model.** `require_api_key()` reads the `X-API-Key` header and compares it to the
`API_KEY` env var with `secrets.compare_digest` (constant-time). If `API_KEY` is unset,
auth is **disabled** and a loud warning is logged at startup — convenient for demos, but
every mutating endpoint is then open.

**CORS.** Restricted to `ALLOWED_ORIGINS` (comma-separated; defaults to localhost:8501).

**Safety rails.**
- `MAX_ACTIONS_PER_REQUEST = 25` — rejects oversized action batches (quota protection).
- `/chat` caps the message at 800 chars; replies are sanitized (`core/guardrails.py`,
  capped at 1500 chars, de-duplicated lines).

Every request carries a `session_id` (defaults to `"default"`), bound for the duration of
the request via `set_session()` so memory layers stay isolated per user/browser.

---

## 3. The orchestrator pipeline (`/chat`)

When `POST /chat` arrives, `run_agentic_workflow(message, conversation_history)` runs three
phases:

### Phase 1 — Fast paths
Greetings / thanks / "how are you" are matched by regex and answered with canned replies,
skipping the expensive context build. The turn is still recorded in conversation history.

### Phase 2 — Multi-turn drafts
The hard part of a chat assistant is state across turns. Axon keeps per-session drafts:
- `awaiting_event_title` / `draft_create_event` — "create an event" → (next msg) "Yoga" → "8am".
- `draft_reschedule_event` — remembers which event is mid-reschedule.
- **Slot-fill** — after "find me a free slot", "add deep work in that window" creates an
  event in the previously recommended slot.

`_persist_pending()` guarantees any actions produced on a fast path reach
`session["pending_actions"]` even when the handler returns early — this was a real
regression (test case 6) where fast-path actions were dropped before persistence.

### Phase 3 — Main pipeline
```
build_context()  →  detect_intent()  →  extract_entities()  →  route_intent()  →  style_reply()
```

1. **`build_context()`** (`orchestrator/context_builder.py`)
   Fetches today's events (5-minute TTL cache), structures + prioritizes them, computes
   `load_pct` (share of a 600-min workday booked), detects overlap conflicts, and finds a
   free slot. Returns one `context` dict consumed by everything downstream.

2. **`detect_intent()`** (`agents/intent_agent.py`) — **hybrid, rules first**
   - Rule layer: anchored affirm/reject regex, verb prefixes ("reschedule…", "add…",
     "delete…"), and a keyword map for 11 intents (`GET_TODAY`, `GET_FREE_SLOTS`,
     `CREATE_EVENT`, `RESCHEDULE_EVENT`, `DELETE_EVENT`, `SHOW_CONFLICTS`, `OPTIMIZE_DAY`,
     `APPROVE_ACTIONS`, `REJECT_ACTIONS`, `WHY_EXPLAIN`).
   - LLM fallback: only when no rule matches. The prompt includes the last intent and the
     last 3 turns, and is constrained to the valid intent set.

3. **`extract_entities()`** (`agents/entity_agent.py`) — **hybrid**
   Regex extracts an event title and a time ("3pm", "at 9", "tomorrow 8"); an LLM pass
   fills gaps. Both are validated (titles ≤ 8 words, no question words; times must look
   like times) and merged with rules taking precedence.

4. **`route_intent()`** (`orchestrator/router.py`)
   Dispatches the intent to either a workflow or an inline handler:
   - `GET_TODAY` → `today_workflow`
   - `GET_FREE_SLOTS`, `OPTIMIZE_DAY` → `focus_workflow`
   - `RESCHEDULE_EVENT` / `DELETE_EVENT` / `CREATE_EVENT` → inline handlers that resolve the
     target event, fill missing slots via drafts, and emit **proposed actions** (not
     executed yet). Reschedules of `priority == "high"` events are refused by guard.
   - `SHOW_CONFLICTS`, `WHY_EXPLAIN` → explanatory replies, no actions.

5. **`style_reply()`** (`orchestrator/response_formatter.py`)
   Adds a contextual opening and respects a "prefers brief" preference.

The response dict returned to the frontend always carries:
`reply, intent, events, conflicts, actions, load_pct, requires_confirmation, suggestions`.

---

## 4. The agents

| Agent | File | In → Out | Uses LLM? |
|-------|------|----------|-----------|
| **Intent** | `agents/intent_agent.py` | message+context → intent label | Fallback only |
| **Entity** | `agents/entity_agent.py` | message+context → `{event_title, time}` | Gap-fill only |
| **Planner** | `agents/planner_agent.py` | raw events → typed/enriched events | Yes (1 batch call) |
| **Prioritizer** | `agents/prioritizer_agent.py` | events → events + `priority`/`duration` | Yes (1 batch call) |
| **Execution** | `agents/execution_agent.py` | approved actions → results | No |

Two design choices worth noting:

- **Batch LLM calls.** Planner and prioritizer classify the *entire* event list in a single
  LLM call (`_batch_enrich`, `_batch_llm_priorities`), not one call per event — fewer
  round-trips, lower latency and cost.
- **Rules before the model.** Prioritizer applies hard keyword rules ("interview", "client",
  "deadline" → high; very short events → low) and consults **long-term patterns** (an event
  seen >5 times → high; cancelled >70% of the time → low) before asking the LLM to refine.

The **Execution agent** is deterministic: it resolves each action's target event, converts
spoken times to ISO-8601 in `APP_TIMEZONE` (then UTC for the API), preserves the original
duration on reschedules, calls the calendar service, updates long-term patterns, and returns
`{status: "EXECUTED" | "FAILED", ...}`. It re-checks the high-priority guard before moving.

---

## 5. Memory layers (`backend/app/memory/`)

| Layer | File | Backing | Holds |
|-------|------|---------|-------|
| Session (volatile) | `session_memory.py` | in-process dict | conversation turns (last 20), drafts, last focus slot, last intent |
| Short-term (durable) | `short_term.py` | `session_store.json` | `last_events`, `pending_actions` per session |
| Long-term | `long_term.py` | `store.json` | per-title `{count, cancelled, rescheduled}` patterns |
| Preferences | `state_manager.py` | `preferences.json` | focus-time preference, evening-meeting avoidance |

Session isolation is enforced by a `ContextVar` set per request (`core/session_context.py`),
so concurrent users never read each other's drafts or pending actions.

> **Scaling note:** session/pending state is file-backed, so a multi-replica deployment needs
> shared storage (e.g. Redis) instead of `session_store.json`. Single-instance is fine as-is.

---

## 6. Calendar services & DEMO_MODE

`services/calendar_service.py` wraps the Google Calendar API: OAuth via `credentials.json`
→ `token.json` (auto-refresh), then `get_today_events`, `create_event`, `reschedule_event`,
`cancel_event` against the `primary` calendar.

When `DEMO_MODE=true`, those calls are transparently swapped for
`services/mock_calendar_service.py` — an in-memory list seeded with 5 realistic events
(including a deliberate lunch/sync overlap so conflict detection has something to find). This
lets anyone run the full product with **no Google account and no OAuth**, which is also what
CI uses.

---

## 7. The human-in-the-loop (HITL) approval flow

Axon proposes; the user disposes. Mutations are a two-step commit:

```
1. /chat or /execute   →  actions land in session["pending_actions"]   (nothing changed yet)
2. user reviews them in the dashboard
3. /approve {"yes"}    →  execute_actions(pending) runs  →  calendar mutated
   /approve (not yes)  →  pending_actions cleared, drafts reset, nothing happens
```

After a successful approval the event cache is invalidated, so the next `/today` reflects the
change. The same gate is reachable conversationally: "yes / do it" → `APPROVE_ACTIONS`,
"no / cancel" → `REJECT_ACTIONS`.

**Worked example — "add yoga at 8am":**
1. `/chat` → intent `CREATE_EVENT`, entities `{yoga, 8am}` → proposed `create` action,
   persisted to pending. Reply: *"I can add yoga at 8am — review and approve."*
2. Frontend shows the action card → user clicks **Approve**.
3. `/execute` queues it, `/approve {"yes"}` runs `create_event(...)` (real or mock).
4. Cache invalidated → `/today` now shows Yoga at 08:00.

---

## 8. The frontend (`frontend/app.py`)

A single Streamlit app, two columns:
- **Left** — chat. Generates a per-browser `session_id` (`uuid4().hex`), sends every message
  to `/chat`, merges the structured response back into UI state.
- **Right** — a live dashboard: stats (events / conflicts / pending), a priority-coloured
  timeline with a load bar, detected conflicts, and **pending-action cards** with
  Approve / Reject / Edit-time controls (and "Approve all").

It talks to the backend at `API_URL` (defaults to `http://127.0.0.1:8000`; set to
`http://backend:8000` under Docker Compose). If the backend has `API_KEY` set, the frontend
must send the matching `X-API-Key`.

---

## 9. Running it

### Local (two terminals)
```bash
# backend
cd backend
python -m uvicorn app.main:app --reload --app-dir .       # → http://127.0.0.1:8000

# frontend
cd frontend
python -m streamlit run app.py                            # → http://localhost:8501
```
Set `DEMO_MODE=true` to skip Google OAuth entirely.

### Docker Compose (recommended)
```bash
cp .env.example .env        # fill in ANTHROPIC_API_KEY or GROQ_API_KEY (or leave demo)
docker compose up --build
# backend  → http://localhost:8000
# frontend → http://localhost:8501
```
The backend image is multi-stage (wheels built once, runtime is slim), runs as a non-root
user, and ships a `HEALTHCHECK` against `/`. Compose gates the frontend on the backend
becoming healthy.

---

## 10. Quality gates (CI — `.github/workflows/ci.yml`)

Three jobs run on every push/PR to `main`:

1. **Lint & compile** — byte-compiles all sources (fast syntax fail), runs `ruff` (advisory).
2. **Chat regression** — `python -m app.testing.testing_chat_regression` in `DEMO_MODE`.
   Six deterministic end-to-end cases (calendar + LLM mocked) covering: delete-intent,
   `GET_TODAY` not emitting actions, draft state not leaking between calls, multi-turn
   create (title → time), and the full add → time → "yes" approval persistence path.
3. **Docker build & smoke** — builds both images with layer caching, boots the backend
   container in demo mode, and polls `/` until it returns healthy.

`lint` gates the other two; `regression` and `docker` run in parallel after it.

---

## 11. Configuration reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `groq` |
| `ANTHROPIC_API_KEY` | — | required when provider is anthropic |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | Claude model id |
| `GROQ_API_KEY` | — | required when provider is groq |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model id |
| `DEMO_MODE` | `false` | `true` → in-memory mock calendar, no OAuth |
| `ALLOW_INTERACTIVE_AUTH` | `false` | allow browser OAuth flow (local only) |
| `API_KEY` | — | if set, all non-health endpoints require `X-API-Key` |
| `ALLOWED_ORIGINS` | `localhost:8501,127.0.0.1:8501` | CORS allow-list |
| `APP_TIMEZONE` | `UTC` | timezone for parsing spoken times |
| `API_URL` | `http://127.0.0.1:8000` | backend URL used by the frontend |

---

## 12. Request lifecycle (one diagram)

```
"move gym to 8pm"
      │  POST /chat {message, history, session_id}
      ▼
main.chat() ── set_session() ──► run_agentic_workflow()
      │                                │
      │            build_context() ────┤  events(cached) + load + conflicts + free_slot
      │            detect_intent() ────┤  rules → RESCHEDULE_EVENT
      │            extract_entities() ─┤  {title:"gym", time:"8pm"}
      │            route_intent() ─────┤  resolve event, guard high-prio,
      │                                │  emit proposed reschedule action
      │            _persist_pending() ─┘  → session["pending_actions"]
      ▼
reply + actions ──► frontend renders action card
      │
   user Approve
      │  POST /execute → queue   then   POST /approve {"yes"}
      ▼
execute_actions() ─► reschedule_event() (real|mock) ─► invalidate cache
      ▼
GET /today reflects gym @ 8pm
```

---

*Generated as living documentation of the Axon codebase. Not part of the deployable app.*
