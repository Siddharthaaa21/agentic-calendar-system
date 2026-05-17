# import requests

# API_URL = "http://127.0.0.1:8000"


# def fetch_schedule():
#     try:
#         res = requests.get(f"{API_URL}/today", timeout=10)
#         res.raise_for_status()
#         return res.json()
#     except Exception:
#         return {
#             "events": [],
#             "conflicts": [],
#             "actions": [],
#             "memory": {},
#             "load_pct": 0
#         }


# def approve_action(action):
#     try:
#         res = requests.post(
#             f"{API_URL}/execute",
#             json={"actions": [action]},
#             timeout=10
#         )
#         return res.json()
#     except Exception:
#         return {"status": "offline mode"}


# def suggest_times(event_title):

#     return [
#         "11:30 AM",
#         "2:00 PM",
#         "4:30 PM"
#     ]


# def build_schedule_text(events):

#     if not events:
#         return "You have no events today."

#     text = "### Today's Schedule\n\n"

#     for e in events:
#         text += (
#             f"• **{e['title']}** "
#             f"({e['start']} → {e['end']})\n"
#         )

#     return text


# def build_conflict_text(conflicts):

#     if not conflicts:
#         return "No conflicts detected."

#     text = "### Conflicts Found\n\n"

#     for c in conflicts:
#         text += f"• {c['title']}\n"

#     return text