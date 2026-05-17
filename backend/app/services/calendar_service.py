import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

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

    if not creds or not creds.valid:
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

    now = datetime.datetime.utcnow()

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

        print(f"🗑 Deleting event: {event_id}")

        service.events().delete(
            calendarId="primary",
            eventId=event_id
        ).execute()

        print("✅ Deleted successfully")

        return {
            "status": "cancelled",
            "event_id": event_id
        }

    except Exception as e:
        print(f"❌ Cancel failed: {e}")
        return {
            "status": "FAILED",
            "event_id": event_id,
            "error": str(e)
        }


# ✅ RESCHEDULE EVENT
def reschedule_event(event_id: str, new_start: str, new_end: str):
    try:
        service = get_service()

        print(f"🔁 Rescheduling event: {event_id}")

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

        print("✅ Rescheduled successfully")

        return normalize_event(updated_event)

    except Exception as e:
        print(f"❌ Reschedule failed: {e}")
        return {
            "status": "FAILED",
            "event_id": event_id,
            "error": str(e)
        }