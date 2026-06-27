# Axon — Agentic Calendar System

A conversational agent that manages your Google Calendar through natural language: it understands intent, plans and prioritizes your day, detects conflicts, finds free slots, and proposes create/reschedule/delete actions through a human-in-the-loop (HITL) approval gate before anything touches your real calendar.

Built with a FastAPI backend, a Streamlit frontend, and Groq (Llama 3.1) for LLM reasoning.

**Status:** Active development — deterministic regression tests passing locally and in CI.

**Contents**
- `backend/` — FastAPI backend: agents (intent, entity, planner, prioritizer, execution), orchestrator (router, workflow, context builder), memory, and tests.
- `frontend/` — Streamlit UI for interactive chat and approvals.
- `tools/` — helper scripts (README graph generation).

---

## Try it live (demo mode)

The hosted demo runs with `DEMO_MODE=true`, which swaps Google Calendar for an in-memory mock calendar pre-seeded with a sample day (including an intentional scheduling conflict). No Google account or API keys needed — just chat with it:

- "what's for today"
- "show conflicts"
- "free slots"
- "move gym to 8pm"
- "delete lunch"

Demo state is shared and resets when the server restarts — it's for trying out the chat → plan → approve → execute loop, not for real scheduling.

---

## Architecture

```
User ↔ Streamlit (frontend/app.py)
            │  HTTP (API_URL)
            ▼
       FastAPI (backend/app/main.py)
            │
   ┌────────┴─────────┐
   │   Orchestrator     │  intent/entity detection → router → workflow
   └────────┬─────────┘
            │
   ┌────────┴─────────┐
   │      Agents        │  planner, prioritizer, execution (Groq LLM)
   └────────┬─────────┘
            │
   ┌────────┴─────────┐
   │ Calendar Service   │  Google Calendar API  — or —  in-memory mock (DEMO_MODE)
   └────────────────────┘
```

A HITL approval gate (`/execute` queues actions, `/approve` applies them) means the LLM never mutates your calendar directly — every create/reschedule/delete is queued and shown to the user first.

---

## Local Setup

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
- `GROQ_API_KEY` — required, get one free at https://console.groq.com
- `DEMO_MODE=true` — run with the mock calendar (no Google setup needed)
- `DEMO_MODE=false` — use real Google Calendar (see below)

### 2. Real Google Calendar (DEMO_MODE=false)

1. Create an OAuth client ID (Desktop app) in Google Cloud Console with the Calendar API enabled.
2. Download it as `backend/credentials.json`.
3. On first run, a browser window opens for you to log in; a `token.json` is saved for future runs.

This OAuth flow is interactive/local-only and will not work on a headless cloud server — use `DEMO_MODE=true` for cloud deployments.

### 3. Run the backend

```bash
source venv39/bin/activate
cd backend
python -m uvicorn app.main:app --reload --app-dir .
```

### 4. Run the frontend

```bash
source venv39/bin/activate
cd frontend
python -m streamlit run app.py
```

By default the frontend talks to `http://127.0.0.1:8000`. To point it at a different backend, set `API_URL` (env var or Streamlit secret).

---

## Tests / Regression

```bash
source venv39/bin/activate
cd backend
python -m app.testing.testing_chat_regression
```

Expected output: `Regression result: 6/6 passed`. This also runs automatically on every push/PR via GitHub Actions (`.github/workflows/ci.yml`).

---

## Deployment

### Docker (local / any container host)

```bash
GROQ_API_KEY=your_key DEMO_MODE=true docker compose up --build
```

This starts the backend on `:8000` and frontend on `:8501`.

### Cloud (recommended split)

- **Backend** → Render / Railway / Fly.io: deploy `backend/` (or use `backend/Dockerfile`), set `GROQ_API_KEY`, `DEMO_MODE=true`, and `ALLOWED_ORIGINS=https://<your-frontend-domain>`.
- **Frontend** → Streamlit Community Cloud: deploy `frontend/app.py`, set the `API_URL` secret to your backend's public URL.

---

## Project Notes & Next Steps
- HITL approve/apply flow: `/execute` (queue) + `/approve` (apply).
- Short-term session memory is file-backed; consider migrating to Redis for multi-instance deployments.
- The repository targets Python 3.9 (`venv39`); Google libraries warn about 3.9 EOL — consider upgrading to 3.10+.
- Demo mode state is in-memory and shared across all visitors of a deployment by design — fine for a portfolio demo, not for multi-tenant production use.

## Generate README Graphs

```bash
source venv39/bin/activate
python tools/generate_graphs.py
```

Produces `docs/graphs/architecture.png` and `docs/graphs/regression_results.png`, referenced below.

---

![Architecture](docs/graphs/architecture.png)

![Regression results](docs/graphs/regression_results.png)
