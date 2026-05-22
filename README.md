# agentic-calendar-system

Agentic Calendar System — a conversational agent that manages calendar events (create, reschedule, delete) with a FastAPI backend and Streamlit frontend.

**Status:** Active development — deterministic regression tests passing locally.

**Contents**
- `backend/` — FastAPI backend, agents, orchestrator, services, and tests.
- `frontend/` — Streamlit UI for interactive chat and approvals.

**Quick Start (using existing venv39)**

1. Activate the project's existing virtual environment (recommended):

```bash
source venv39/bin/activate
```

2. Run the backend (from repo root):

```bash
cd backend
python -m uvicorn app.main:app --reload --app-dir .
```

3. Run the frontend (in another terminal, from repo root):

```bash
source venv39/bin/activate
cd frontend
python -m streamlit run app.py
```

**Tests / Regression**

Run the deterministic chat regression located at `backend/app/testing/testing_chat_regression.py` to validate multi-turn flows and action execution.

```bash
source venv39/bin/activate
cd backend
python -m app.testing.testing_chat_regression
```


**Generate README Graphs**

A helper script `tools/generate_graphs.py` can produce two small illustrative PNGs under `docs/graphs/`: an architecture placeholder and a regression results chart.

```bash
source venv39/bin/activate
python tools/generate_graphs.py
```

The images will be saved to `docs/graphs/architecture.png` and `docs/graphs/regression_results.png` and are referenced below.

**Project Notes & Next Steps**
- The code includes a HITL approve/apply flow: `/execute` (queue) + `/approve` (apply).
- Short-term session memory is file-backed; consider migrating to Redis for multi-instance deployments.
- The repository currently targets Python 3.9 in `venv39`; Google libraries warn about 3.9 EOL — consider upgrading to 3.10+ and adjusting `requirements.txt`.



---

![Architecture](docs/graphs/architecture.png)

![Regression results](docs/graphs/regression_results.png)
# agentic-calendar-system
