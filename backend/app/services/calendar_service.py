import os
import datetime
import logging
from dotenv import load_dotenv

load_dotenv()

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


# ---------------------------
# AUTH
# ---------------------------
def get_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and not creds.valid and creds.expired and creds.refresh_token:
        # Silently refresh — no browser needed.
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    if not creds or not creds.valid:
        # Interactive OAuth opens a browser and blocks — only safe to run
        # locally during first-time setup, never on a headless server.
        if os.getenv("ALLOW_INTERACTIVE_AUTH", "false").lower() != "true":
            raise RuntimeError(
                "No valid Google Calendar credentials. Run locally with "
                "ALLOW_INTERACTIVE_AUTH=true to authorize, or set DEMO_MODE=true."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE, SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


# ---------------------------
# READ EVENTS
# ---------------------------
def get_today_events():
    service = get_service()

    now = datetime.datetime.now(datetime.timezone.utc)

    start_of_day = datetime.datetime(
        now.year, now.month, now.day, 0, 0, 0
    ).isoformat() + "Z"

    end_of_day = datetime.datetime(
        now.year, now.month, now.day, 23, 59, 59
    ).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day,
        timeMax=end_of_day,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])

    return [normalize_event(e) for e in events]


# ---------------------------
# NORMALIZATION
# ---------------------------
def normalize_event(event):
    return {
        "id": event.get("id"),
        "title": event.get("summary", "No Title"),
        "start": event["start"].get("dateTime", event["start"].get("date")),
        "end": event["end"].get("dateTime", event["end"].get("date")),
        "description": event.get("description", ""),
        "status": event.get("status"),
    }


# ---------------------------
# ACTIONS
# ---------------------------

# ✅ CANCEL EVENT
def cancel_event(event_id: str):
    try:
        service = get_service()

        logger.info("Deleting event: %s", event_id)

        service.events().delete(
            calendarId="primary",
            eventId=event_id
        ).execute()

        return {
            "status": "cancelled",
            "event_id": event_id
        }

    except Exception as e:
        logger.exception("Cancel failed for event %s", event_id)
        return {
            "status": "FAILED",
            "event_id": event_id,
            "error": str(e)
        }


# ✅ RESCHEDULE EVENT
def reschedule_event(event_id: str, new_start: str, new_end: str):
    try:
        service = get_service()

        logger.info("Rescheduling event: %s", event_id)

        updated_event = service.events().patch(
            calendarId="primary",
            eventId=event_id,
            body={
    "start": {
        "dateTime": new_start,
        "timeZone": "UTC"
    },
    "end": {
        "dateTime": new_end,
        "timeZone": "UTC"
    }
}
        ).execute()

        return normalize_event(updated_event)

    except Exception as e:
        logger.exception("Reschedule failed for event %s", event_id)
        return {
            "status": "FAILED",
            "event_id": event_id,
            "error": str(e)
        }


def create_event(title: str, start_time: str, end_time: str, description: str = ""):
    try:
        service = get_service()

        created = service.events().insert(
            calendarId="primary",
            body={
                "summary": title,
                "description": description,
                "start": {
                    "dateTime": start_time,
                    "timeZone": "UTC",
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": "UTC",
                },
            },
        ).execute()

        return normalize_event(created)
    except Exception as e:
        logger.exception("Create failed for event %s", title)
        return {
            "status": "FAILED",
            "error": str(e),
            "title": title,
        }


# ---------------------------
# DEMO MODE
# ---------------------------
# When DEMO_MODE=true, swap in an in-memory mock backend so the app can run
# on a public deployment without Google OAuth credentials. Must be last in
# this file so it overrides the real implementations above.
if os.getenv("DEMO_MODE", "false").lower() == "true":
    from app.services.mock_calendar_service import (  # noqa: F401,E402
        get_service,
        get_today_events,
        normalize_event,
        cancel_event,
        reschedule_event,
        create_event,
    )