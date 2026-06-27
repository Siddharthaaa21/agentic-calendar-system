"""Per-request session identity.

A single backend process serves many concurrent users. To keep each user's
conversation memory and pending actions isolated, every request sets a session
id at its entry point (the API endpoint) and all the state stores read it via
`current_session()`. A `ContextVar` carries the value safely across both the
async event loop and FastAPI's sync threadpool for the duration of one request.
"""

from contextvars import ContextVar

_current_session: ContextVar[str] = ContextVar("session_id", default="default")


def set_session(session_id: str) -> None:
    """Bind the session id for the current request context."""
    _current_session.set((session_id or "default").strip() or "default")


def current_session() -> str:
    return _current_session.get()
