import os
import json
import datetime
import logging
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv

load_dotenv()

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.core.session_context import current_session
from app.services import mock_calendar_service

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# In-memory per-session tokens: session_id -> {"creds": Credentials, "email": str, "token_data": dict}
_session_tokens: Dict[str, Dict[str, Any]] = {}
_session_demo_overrides: Dict[str, bool] = {}


def _find_token_file() -> Optional[str]:
    """Find a valid, non-empty Google token.json file on disk."""
    env_path = os.getenv("GOOGLE_TOKEN_FILE")
    if env_path and os.path.exists(env_path) and os.path.getsize(env_path) > 0:
        return env_path

    candidates = [
        os.path.abspath(os.path.join(_BASE_DIR, "..", "..", "token.json")),  # backend/token.json
        os.path.abspath(os.path.join(_BASE_DIR, "..", "..", "..", "token.json")),  # root token.json
        os.path.abspath(os.path.join(_BASE_DIR, "token.json")),  # backend/app/services/token.json
        os.path.abspath("backend/token.json"),
        os.path.abspath("token.json"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 0:
            return c
    return None


def _write_token(creds: Credentials, target_file: Optional[str] = None) -> None:
    path = target_file or _find_token_file() or os.path.join(_BASE_DIR, "token.json")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as token:
            token.write(creds.to_json())
    except Exception as e:
        logger.warning("Could not persist refreshed token to %s: %s", path, e)


def get_credentials(session_id: Optional[str] = None) -> Optional[Credentials]:
    """Resolve valid, refreshed Google OAuth credentials for the active session or server."""
    sess = session_id or current_session()

    # 1. Per-session token
    if sess and sess in _session_tokens:
        info = _session_tokens[sess]
        creds = info.get("creds")
        if creds:
            if not creds.valid and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning("Failed refreshing session creds: %s", e)
            if creds.valid:
                return creds

    # 2. Environment variable GOOGLE_TOKEN_JSON
    raw_env_json = os.getenv("GOOGLE_TOKEN_JSON") or os.getenv("GOOGLE_TOKEN")
    if raw_env_json:
        try:
            token_dict = json.loads(raw_env_json) if isinstance(raw_env_json, str) else raw_env_json
            creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
            if not creds.valid and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            if creds.valid:
                return creds
        except Exception as e:
            logger.warning("Failed loading creds from GOOGLE_TOKEN_JSON: %s", e)

    # 3. File on disk (if DEMO_MODE is not strictly forced to true without a token)
    token_file = _find_token_file()
    if token_file:
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            if not creds.valid and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                _write_token(creds, token_file)
            if creds.valid:
                return creds
        except Exception as e:
            logger.warning("Failed loading token from %s: %s", token_file, e)

    return None


def is_google_calendar_connected(session_id: Optional[str] = None) -> bool:
    sess = session_id or current_session()
    if _session_demo_overrides.get(sess) is True:
        return False
    # If DEMO_MODE was explicitly passed as true in env AND there is no session token or token file
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        # Allow connecting if a real token exists
        creds = get_credentials(sess)
        return creds is not None
    return get_credentials(sess) is not None


def get_connected_account(session_id: Optional[str] = None) -> Optional[str]:
    sess = session_id or current_session()
    if _session_demo_overrides.get(sess) is True:
        return None
    if sess and sess in _session_tokens and _session_tokens[sess].get("email"):
        return _session_tokens[sess]["email"]

    creds = get_credentials(sess)
    if not creds:
        return None
    try:
        service = build("calendar", "v3", credentials=creds)
        cal = service.calendarList().get(calendarId="primary").execute()
        email = cal.get("id") or cal.get("summary")
        if sess and sess in _session_tokens:
            _session_tokens[sess]["email"] = email
        return email
    except Exception as e:
        logger.warning("Could not fetch calendar account identity: %s", e)
        return "Connected Google Account"


def set_session_token(session_id: str, token_data: Union[dict, str]) -> Dict[str, Any]:
    """Bind a user's Google OAuth token to their specific browser session."""
    if isinstance(token_data, str):
        token_data = json.loads(token_data)

    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    service = build("calendar", "v3", credentials=creds)
    cal = service.calendarList().get(calendarId="primary").execute()
    email = cal.get("id") or cal.get("summary") or "Primary Calendar"

    _session_tokens[session_id] = {
        "creds": creds,
        "email": email,
        "token_data": token_data,
    }
    _session_demo_overrides[session_id] = False
    return {"status": "ok", "email": email}


def disconnect_session(session_id: str) -> None:
    _session_tokens.pop(session_id, None)
    _session_demo_overrides[session_id] = True


def get_service(session_id: Optional[str] = None):
    creds = get_credentials(session_id)
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds)


def normalize_event(event: dict) -> dict:
    return {
        "id": event.get("id"),
        "title": event.get("summary", event.get("title", "No Title")),
        "start": event.get("start", {}).get("dateTime", event.get("start", {}).get("date", event.get("start"))),
        "end": event.get("end", {}).get("dateTime", event.get("end", {}).get("date", event.get("end"))),
        "description": event.get("description", ""),
        "status": event.get("status"),
    }


def get_today_events(session_id: Optional[str] = None) -> List[dict]:
    sess = session_id or current_session()
    if not is_google_calendar_connected(sess):
        return mock_calendar_service.get_today_events()

    service = get_service(sess)
    if not service:
        return mock_calendar_service.get_today_events()

    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_day = datetime.datetime(now.year, now.month, now.day, 0, 0, 0).isoformat() + "Z"
    end_of_day = datetime.datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + "Z"

    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = events_result.get("items", [])
        return [normalize_event(e) for e in events]
    except Exception as e:
        logger.exception("Google Calendar API list failed: %s", e)
        return []


def get_upcoming_events(limit: int = 5, session_id: Optional[str] = None) -> List[dict]:
    sess = session_id or current_session()
    if not is_google_calendar_connected(sess):
        return mock_calendar_service.get_today_events()[:limit]

    service = get_service(sess)
    if not service:
        return []

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        res = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=limit,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return [normalize_event(e) for e in res.get("items", [])]
    except Exception as e:
        logger.exception("Google Calendar API upcoming failed: %s", e)
        return []


def cancel_event(event_id: str, session_id: Optional[str] = None) -> dict:
    sess = session_id or current_session()
    if not is_google_calendar_connected(sess):
        return mock_calendar_service.cancel_event(event_id)

    service = get_service(sess)
    if not service:
        return {"status": "FAILED", "event_id": event_id, "error": "Calendar not connected"}

    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return {"status": "cancelled", "event_id": event_id}
    except Exception as e:
        logger.exception("Cancel failed on Google Calendar for %s: %s", event_id, e)
        return {"status": "FAILED", "event_id": event_id, "error": "Couldn't cancel this event."}


def reschedule_event(event_id: str, new_start: str, new_end: str, session_id: Optional[str] = None) -> dict:
    sess = session_id or current_session()
    if not is_google_calendar_connected(sess):
        return mock_calendar_service.reschedule_event(event_id, new_start, new_end)

    service = get_service(sess)
    if not service:
        return {"status": "FAILED", "event_id": event_id, "error": "Calendar not connected"}

    try:
        updated = service.events().patch(
            calendarId="primary",
            eventId=event_id,
            body={
                "start": {"dateTime": new_start, "timeZone": "UTC"},
                "end": {"dateTime": new_end, "timeZone": "UTC"},
            },
        ).execute()
        return normalize_event(updated)
    except Exception as e:
        logger.exception("Reschedule failed on Google Calendar for %s: %s", event_id, e)
        return {"status": "FAILED", "event_id": event_id, "error": "Couldn't reschedule this event."}


def create_event(title: str, start_time: str, end_time: str, description: str = "", session_id: Optional[str] = None) -> dict:
    sess = session_id or current_session()
    if not is_google_calendar_connected(sess):
        return mock_calendar_service.create_event(title, start_time, end_time, description)

    service = get_service(sess)
    if not service:
        return {"status": "FAILED", "title": title, "error": "Calendar not connected"}

    try:
        created = service.events().insert(
            calendarId="primary",
            body={
                "summary": title,
                "description": description,
                "start": {"dateTime": start_time, "timeZone": "UTC"},
                "end": {"dateTime": end_time, "timeZone": "UTC"},
            },
        ).execute()
        return normalize_event(created)
    except Exception as e:
        logger.exception("Create failed on Google Calendar for %s: %s", title, e)
        return {"status": "FAILED", "title": title, "error": "Couldn't create this event."}