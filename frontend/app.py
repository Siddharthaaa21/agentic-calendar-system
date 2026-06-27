import os
import uuid
import streamlit as st
import requests
from datetime import datetime

def _get_api_url():
    if os.getenv("API_URL"):
        return os.getenv("API_URL")
    try:
        return st.secrets["API_URL"]
    except Exception:
        return "http://127.0.0.1:8000"


API_URL = _get_api_url()
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"


def _fmt_time(value):
    """Format an ISO-8601 timestamp as a short human-readable time, e.g. '9:00 AM'."""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%I:%M %p").lstrip("0")
    except (ValueError, TypeError):
        return str(value)

st.set_page_config(
    page_title="Axon",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg:       #070a0f;
    --surface:  #111520;
    --surface-2:#161b2a;
    --border:   #1e2a3a;
    --accent:   #3b82f6;
    --accent-2: #2563eb;
    --muted:    #3d5166;
    --text:     #e8eef6;
    --text-2:   #64748b;
    --red:      #ef4444;
    --green:    #10b981;
    --amber:    #f59e0b;
    --glass:    rgba(255,255,255,.03);
    --grad:     linear-gradient(135deg, #3b82f6 0%, #6366f1 50%, #8b5cf6 100%);
}

html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1200px 600px at 12% -10%, rgba(59,130,246,.10), transparent 55%),
        radial-gradient(1000px 500px at 100% 0%, rgba(139,92,246,.08), transparent 50%),
        var(--bg) !important;
    background-attachment: fixed !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text) !important;
    -webkit-font-smoothing: antialiased;
}

@keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }

.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stSidebar"] { display: none; }
#MainMenu, footer, header, [data-testid="stToolbar"], .stDeployButton { display: none !important; }

/* ── HEADER ── */
.hdr {
    display: flex; align-items: center; gap: 13px;
    padding: 14px 26px;
    border-bottom: 1px solid var(--border);
    background: rgba(17,21,32,.55);
    backdrop-filter: blur(18px) saturate(140%);
    -webkit-backdrop-filter: blur(18px) saturate(140%);
    position: sticky; top: 0; z-index: 50;
    animation: fadeUp .4s ease both;
}
.hdr-logo {
    width: 30px; height: 30px; border-radius: 9px; flex-shrink: 0;
    background: var(--grad);
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; font-weight: 700; color: #fff;
    box-shadow: 0 4px 16px rgba(59,130,246,.4);
}
.hdr-dot {
    width: 8px; height: 8px; border-radius: 50%; background: var(--green);
    box-shadow: 0 0 0 0 rgba(16,185,129,.5);
    animation: pulse 2.5s ease infinite; flex-shrink: 0;
}
.hdr-dot.offline { background: var(--muted); animation: none; box-shadow: none; }
@keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(16,185,129,.45); }
    70%  { box-shadow: 0 0 0 7px rgba(16,185,129,0); }
    100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); }
}
.hdr-title {
    font-size: 15px; font-weight: 700; letter-spacing: -.3px;
    background: var(--grad); -webkit-background-clip: text;
    background-clip: text; -webkit-text-fill-color: transparent;
}
.hdr-sub   { font-size: 11px; color: var(--text-2); display: flex; align-items: center; gap: 6px; }
.hdr-right { margin-left: auto; font-size: 11px; color: var(--muted);
             font-family: 'JetBrains Mono', monospace; }

/* ── COLUMNS ── */
[data-testid="stHorizontalBlock"] > div:first-child {
    border-right: 1px solid var(--border);
}

/* ── CHAT ── */
[data-testid="stChatMessage"] { background: transparent !important; }
[data-testid="stChatMessage"] { animation: fadeUp .35s ease both; }
[data-testid="stChatMessageContent"] {
    background: linear-gradient(180deg, var(--surface-2), var(--surface)) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px 14px 14px 14px !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
    padding: 11px 15px !important;
    box-shadow: 0 8px 20px -14px rgba(0,0,0,.8) !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
    background: linear-gradient(135deg, rgba(59,130,246,.18), rgba(139,92,246,.12)) !important;
    border-color: rgba(99,102,241,.3) !important;
    border-radius: 14px 4px 14px 14px !important;
}

/* ── CHAT MESSAGE LISTS (e.g. task/priority bullets) ── */
[data-testid="stChatMessageContent"] ul {
    margin: 6px 0 !important;
    padding-left: 0 !important;
    list-style: none !important;
}
[data-testid="stChatMessageContent"] ul li {
    position: relative;
    padding: 4px 0 4px 18px !important;
    margin: 0 !important;
    border-bottom: 1px solid rgba(255,255,255,.04);
}
[data-testid="stChatMessageContent"] ul li:last-child { border-bottom: none; }
[data-testid="stChatMessageContent"] ul li::before {
    content: "";
    position: absolute;
    left: 2px; top: 13px;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--accent);
}
[data-testid="stChatMessageContent"] ul ul {
    margin: 2px 0 0 0 !important;
}
[data-testid="stChatMessageContent"] ul ul li {
    border-bottom: none !important;
    padding: 2px 0 2px 18px !important;
}
[data-testid="stChatMessageContent"] ul ul li::before {
    width: 4px; height: 4px; top: 11px;
    background: var(--text-2);
}
[data-testid="stChatMessageContent"] p { margin: 4px 0 !important; }
[data-testid="stChatInput"] > div {
    background: rgba(17,21,32,.6) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    transition: border-color .2s ease, box-shadow .2s ease !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: rgba(59,130,246,.5) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,.12) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--muted) !important; }

/* ── BUTTONS ── */
button[kind="secondary"], [data-testid="stButton"] button {
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important; font-weight: 500 !important;
    border-radius: 9px !important;
    transition: all .18s ease !important;
    padding: 6px 15px !important;
}
[data-testid="stButton"] button:active { transform: scale(.97) !important; }
.btn-approve button {
    background: transparent !important; color: var(--green) !important;
    border: 1px solid rgba(16,185,129,.3) !important;
}
.btn-approve button:hover { background: rgba(16,185,129,.08) !important; }
.btn-reject button {
    background: transparent !important; color: var(--red) !important;
    border: 1px solid rgba(239,68,68,.3) !important;
}
.btn-reject button:hover { background: rgba(239,68,68,.08) !important; }
.btn-edit button {
    background: transparent !important; color: var(--amber) !important;
    border: 1px solid rgba(245,158,11,.3) !important;
}
.btn-edit button:hover { background: rgba(245,158,11,.08) !important; }
.btn-refresh button {
    background: transparent !important; color: var(--text-2) !important;
    border: 1px solid var(--border) !important;
    width: 100% !important;
}
.btn-refresh button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }
.btn-all button {
    background: var(--grad) !important; color: #fff !important;
    border: none !important; width: 100% !important; font-weight: 600 !important;
    box-shadow: 0 6px 18px -6px rgba(59,130,246,.6) !important;
}
.btn-all button:hover { filter: brightness(1.08) !important; box-shadow: 0 8px 22px -6px rgba(59,130,246,.75) !important; }

/* ── CARDS ── */
.card {
    background: linear-gradient(180deg, var(--surface-2), var(--surface));
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px 18px;
    margin-bottom: 12px;
    box-shadow: 0 1px 0 rgba(255,255,255,.03) inset, 0 18px 40px -20px rgba(0,0,0,.8);
    transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
    animation: fadeUp .4s ease both;
}
.card:hover {
    border-color: rgba(59,130,246,.35);
    transform: translateY(-2px);
    box-shadow: 0 1px 0 rgba(255,255,255,.04) inset, 0 24px 50px -22px rgba(0,0,0,.9);
}
.card-label {
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 1.2px; color: var(--text-2); margin-bottom: 12px;
    display: flex; align-items: center; gap: 7px;
}
.card-label::before {
    content: ""; width: 3px; height: 12px; border-radius: 2px; background: var(--grad);
}

/* ── EMPTY STATE ── */
.empty {
    padding: 28px 16px; text-align: center;
    border: 1px dashed var(--border);
    border-radius: 10px; margin-bottom: 10px;
}
.empty-title { font-size: 13px; color: var(--text-2); font-weight: 500; margin-bottom: 4px; }
.empty-sub   { font-size: 11px; color: var(--muted); }

/* ── STATS ── */
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 12px; }
.stat  {
    background: linear-gradient(180deg, var(--surface-2), var(--surface));
    border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px;
    transition: transform .18s ease, border-color .18s ease;
    animation: fadeUp .4s ease both;
}
.stat:hover { transform: translateY(-2px); border-color: rgba(59,130,246,.3); }
.stat-n { font-size: 23px; font-weight: 600; font-family: 'JetBrains Mono', monospace; line-height: 1; }
.stat-l { font-size: 10px; color: var(--text-2); margin-top: 5px; text-transform: uppercase; letter-spacing: .6px; }

/* ── TIMELINE ── */
.tl { display: flex; flex-direction: column; }
.tl-row {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 8px 6px; border-bottom: 1px solid var(--border); font-size: 12px;
    border-radius: 7px; transition: background .15s ease;
}
.tl-row:hover { background: var(--glass); }
.tl-row:last-child { border-bottom: none; }
.tl-row.conflict {
    background: rgba(239,68,68,.04); border-radius: 6px;
    padding: 7px 6px; border-bottom: none; margin: 2px 0;
}
.tl-time { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); min-width: 38px; padding-top: 2px; }
.tl-name { color: var(--text); font-weight: 500; }
.tl-name.err { color: var(--red); }
.tl-sub  { font-size: 10px; color: var(--text-2); margin-top: 1px; }
.dot { width: 6px; height: 6px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
.dot.h { background: var(--red); }
.dot.m { background: var(--amber); }
.dot.l { background: var(--green); }

/* ── CONFLICT ── */
.cfl {
    display: flex; gap: 10px; align-items: flex-start;
    padding: 9px 10px; border-radius: 8px; margin-bottom: 7px;
    border: 1px solid rgba(239,68,68,.15);
    background: rgba(239,68,68,.04); font-size: 12px;
}
.cfl.warn { border-color: rgba(245,158,11,.15); background: rgba(245,158,11,.04); }
.cfl-body { color: var(--text); }
.cfl-sub  { color: var(--text-2); font-size: 10px; margin-top: 2px; }

/* ── ACTION ── */
.act {
    padding: 12px 14px; border-radius: 11px; margin-bottom: 8px;
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    background: linear-gradient(90deg, rgba(59,130,246,.07), rgba(59,130,246,.02));
    font-size: 12px;
    transition: border-color .18s ease, transform .18s ease;
    animation: fadeUp .35s ease both;
}
.act:hover { transform: translateX(2px); border-left-color: #8b5cf6; }
.act-type { font-size: 10px; font-weight: 600; text-transform: uppercase;
            letter-spacing: .8px; color: var(--accent); margin-bottom: 4px; }
.act-desc { color: var(--text); line-height: 1.5; }

/* ── MISC ── */
[data-testid="stSuccess"] {
    background: rgba(16,185,129,.08) !important; border: 1px solid rgba(16,185,129,.2) !important;
    border-radius: 8px !important; color: var(--green) !important; font-size: 12px !important;
}
[data-testid="stWarning"] {
    background: rgba(245,158,11,.08) !important; border: 1px solid rgba(245,158,11,.2) !important;
    border-radius: 8px !important; color: var(--amber) !important; font-size: 12px !important;
}
div[data-testid="stSpinner"] { color: var(--text-2) !important; }
hr { border-color: var(--border) !important; margin: 8px 0 !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
::-webkit-scrollbar-track { background: transparent; }

/* ── EMPTY STATE hover ── */
.empty { transition: border-color .2s ease; animation: fadeUp .4s ease both; }
.empty:hover { border-color: var(--accent); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def fetch_schedule():
    """Returns (data_dict, error_string). One of them will be None."""
    try:
        r = requests.get(
            f"{API_URL}/today",
            params={"session_id": st.session_state.session_id},
            timeout=6,
        )
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, f"Cannot reach API at {API_URL}. Is the server running?"
    except requests.exceptions.Timeout:
        return None, "Request timed out. The server took too long to respond."
    except requests.exceptions.HTTPError as e:
        return None, f"Server returned an error: {e.response.status_code}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def call_execute(actions):
    try:
        return requests.post(
            f"{API_URL}/execute",
            json={"actions": actions, "session_id": st.session_state.session_id},
            timeout=6,
        ).json()
    except Exception as e:
        st.warning(f"Execute failed: {e}")
        return {}
    

def call_approve():
    try:
        return requests.post(
            f"{API_URL}/approve",
            json={"approval": "yes", "session_id": st.session_state.session_id},
            timeout=6,
        ).json()
    except Exception as e:
        st.warning(f"Approve failed: {e}")
        return {}
def ask_agent(prompt, history=None):
    try:
        history = history or []
        r = requests.post(
            f"{API_URL}/chat",
            json={
                "message": prompt,
                "history": history,
                "session_id": st.session_state.session_id,
            },
            timeout=20
        )

        r.raise_for_status()

        return r.json()

    except Exception as e:
        return {
            "reply": f"Agent error: {str(e)}"
        }

# ─────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────
defaults = {
    "messages": [{
        "role": "assistant",
        "content": (
            "Hey — I’m **Axon**. I can help you plan your day like a real assistant, "
            "not just a command bot.\n\n"
            "I keep context across turns, so you can talk naturally.\n\n"
            "You can start with:\n"
            "- 'what’s my day looking like?'\n"
            "- 'anything I should shift?'\n"
            "- 'why do you suggest that slot?'\n"
            "- 'can we move checking to 10 pm?'"
        ),
    }],
    "data": None,
    "error": None,
    "approved": set(),
    "rejected": set(),
    # Stable per-browser-session id so this user's conversation memory and
    # pending actions stay isolated from other users on the same backend.
    "session_id": uuid.uuid4().hex,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Auto-load calendar once
_connect_label = "Loading demo calendar..." if DEMO_MODE else "Connecting to Google Calendar..."
if st.session_state.data is None:
    with st.spinner(_connect_label):
        result, err = fetch_schedule()

    if err:
        st.session_state.error = err
    else:
        st.session_state.data = result

connected = st.session_state.data is not None
dot_cls   = "hdr-dot" if connected else "hdr-dot offline"
if connected:
    status_text = "Demo mode — sample calendar" if DEMO_MODE else "Connected to Google Calendar"
else:
    status_text = "Not connected"

st.markdown(f"""
<div class="hdr">
    <div class="hdr-logo">A</div>
    <div>
        <div class="hdr-title">Axon</div>
        <div class="hdr-sub"><span class="{dot_cls}"></span>{status_text}</div>
    </div>
    <div class="hdr-right">{datetime.now().strftime('%a %d %b · %I:%M %p')}</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  LAYOUT
# ─────────────────────────────────────────
left, right = st.columns([1.1, 0.9], gap="small")

data = st.session_state.data  # may be None until user refreshes

# ══════════════════════════════
#  LEFT — CHAT
# ══════════════════════════════
with left:

    for msg in st.session_state.messages:
        with st.chat_message(
            msg["role"],
            avatar="🤖" if msg["role"] == "assistant" else "👤"
        ):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Message Axon…"):

        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        with st.spinner("Axon is reasoning..."):
            response = ask_agent(prompt, history=st.session_state.messages)

        reply = response.get(
            "reply",
            "No response from agent."
        )

        if response.get("requires_confirmation"):
            reply += "\n\nPlease review and approve from the action panel."

        suggestions = response.get("suggestions", [])
        if suggestions:
            reply += "\n\nTry next:\n" + "\n".join([f"- {item}" for item in suggestions[:3]])

        if "data" in response and response["data"]:
            st.session_state.data = response["data"]
        else:
            current_data = st.session_state.data or {}
            merged = {
                "events": response.get("events", current_data.get("events", [])),
                "conflicts": response.get("conflicts", current_data.get("conflicts", [])),
                "actions": response.get("actions", current_data.get("actions", [])),
                "load_pct": response.get("load_pct", current_data.get("load_pct", 0)),
                "suggestions": response.get("suggestions", current_data.get("suggestions", [])),
            }
            st.session_state.data = merged

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply
        })

        st.rerun()
# ══════════════════════════════
#  RIGHT — DASHBOARD
# ══════════════════════════════
with right:
    st.markdown('<div style="padding:16px 16px 24px;">', unsafe_allow_html=True)

    # ── Refresh button ──
    st.markdown('<div class="btn-refresh">', unsafe_allow_html=True)
    if st.button("⟳  Refresh Schedule", key="ref"):
        with st.spinner("Fetching…"):
            result, err = fetch_schedule()
        if err:
            st.session_state.error = err
        else:
            st.session_state.data     = result
            st.session_state.error    = None
            st.session_state.approved = set()
            st.session_state.rejected = set()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

    # ── Error state ──
    if st.session_state.error:
        st.markdown(f"""
        <div class="empty">
            <div class="empty-title">Unable to fetch schedule</div>
            <div class="empty-sub">{st.session_state.error}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── No data yet ──
    elif data is None:
        st.markdown("""
        <div class="empty">
            <div class="empty-title">No data loaded</div>
            <div class="empty-sub">Click Refresh Schedule to fetch from your calendar.</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Dashboard ──
    if data is not None and not st.session_state.error:
        events    = data.get("events", [])
        conflicts = data.get("conflicts", [])
        actions   = data.get("actions", [])
        load_pct  = data.get("load_pct", 0)

        pending = []
        for i, a in enumerate(actions):
            if "id" not in a:
                a["id"] = f"action_{i}"
            if (a["id"] not in st.session_state.approved and a["id"] not in st.session_state.rejected):
                pending.append(a)

        # Stats
        st.markdown(f"""
        <div class="stats">
            <div class="stat">
                <div class="stat-n" style="color:#2563eb;">{len(events)}</div>
                <div class="stat-l">Events</div>
            </div>
            <div class="stat">
                <div class="stat-n" style="color:#ef4444;">{len(conflicts)}</div>
                <div class="stat-l">Conflicts</div>
            </div>
            <div class="stat">
                <div class="stat-n" style="color:#10b981;">{len(pending)}</div>
                <div class="stat-l">Pending</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Schedule
        if events:
            conflict_titles = " | ".join(c.get("title", "") for c in conflicts).lower()
            rows = ""
            for e in events:
                p   = str(e.get("priority", "medium")).lower()
                dot = {"high": "h", "medium": "m", "low": "l"}.get(p, "m")
                is_conflict = e.get("conflict") or e["title"].lower() in conflict_titles
                cls  = "tl-row conflict" if is_conflict else "tl-row"
                name = (f'<span class="tl-name err">⚠ {e["title"]}</span>'
                        if is_conflict else f'<span class="tl-name">{e["title"]}</span>')
                start, end = _fmt_time(e["start"]), _fmt_time(e["end"])
                rows += f"""
                <div class="{cls}">
                    <span class="tl-time">{start}</span>
                    <div class="dot {dot}"></div>
                    <div>
                        {name}
                        <div class="tl-sub">{start} – {end} · {p.title()}</div>
                    </div>
                </div>"""

            load_c = "#ef4444" if load_pct >= 80 else "#f59e0b" if load_pct >= 60 else "#10b981"
            load_label = "Heavy" if load_pct >= 80 else "Moderate" if load_pct >= 60 else "Light"
            st.markdown(f"""
            <div class="card">
                <div class="card-label">Today's Schedule</div>
                <div class="tl">{rows}</div>
                <div style="margin-top:10px;display:flex;justify-content:space-between;font-size:10px;color:var(--text-2);">
                    <span>Load</span>
                    <span style="color:{load_c};">{load_pct}% · {load_label}</span>
                </div>
                <div style="height:6px;border-radius:4px;background:rgba(255,255,255,.05);margin-top:6px;overflow:hidden;">
                    <div style="height:100%;width:{load_pct}%;background:linear-gradient(90deg,{load_c},{load_c}cc);border-radius:4px;transition:width .6s ease;box-shadow:0 0 10px {load_c}66;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="empty">
                <div class="empty-title">No events today</div>
                <div class="empty-sub">Your calendar is clear.</div>
            </div>
            """, unsafe_allow_html=True)

        # Conflicts
        conflicts = data.get("conflicts", [])
        if conflicts:
            cfl_html = ""
            for c in conflicts:
                cls = "cfl warn" if c.get("warn") else "cfl"
                cfl_html += f"""
                <div class="{cls}">
                    <div>
                        <div class="cfl-body">{c['title']}</div>
                        <div class="cfl-sub">{c.get('detail', '')}</div>
                    </div>
                </div>"""
            st.markdown(f"""
            <div class="card">
                <div class="card-label">Conflicts</div>
                <div class="cfl-list">{cfl_html}</div>
            </div>
            """, unsafe_allow_html=True)

        # Actions
        icon_map = {"RESCHEDULE": "↗", "REBALANCE": "⇄", "DELETE": "×", "CANCEL": "×", "CREATE": "+"}
        target_label = "the demo calendar" if DEMO_MODE else "Google Calendar"

        if pending:
            for a in pending:
                aid  = a["id"]
                action_type = a["action"].upper()
                icon = icon_map.get(action_type, "→")
                st.markdown(f"""
                <div class="act">
                    <div class="act-type">{icon} {action_type}</div>
                    <div class="act-desc"><strong>{a['title']}</strong> — {a.get('detail', '')}</div>
                </div>
                """, unsafe_allow_html=True)

                needs_edit = action_type in ("RESCHEDULE", "REBALANCE")
                cols = st.columns([1, 1, 1] if needs_edit else [1, 1, 2])

                with cols[0]:
                    st.markdown('<div class="btn-approve">', unsafe_allow_html=True)
                    if st.button("Approve", key=f"ap_{aid}"):
                        call_execute([a])
                        approve_result = call_approve()
                        results = approve_result.get("results", [])
                        failed = [item for item in results if item.get("status") == "FAILED"]

                        if failed:
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"I couldn't apply **{a['title']}**: {failed[0].get('error', 'unknown error')}",
                            })
                        else:
                            st.session_state.approved.add(aid)
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"✓ **{a['title']}** pushed to {target_label}.",
                            })

                        refreshed, err = fetch_schedule()
                        if not err and refreshed:
                            st.session_state.data = refreshed
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                with cols[1]:
                    st.markdown('<div class="btn-reject">', unsafe_allow_html=True)
                    if st.button("Reject", key=f"rj_{aid}"):
                        st.session_state.rejected.add(aid)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Dismissed — **{a['title']}** left unchanged.",
                        })
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                if needs_edit:
                    with cols[2]:
                        st.markdown('<div class="btn-edit">', unsafe_allow_html=True)
                        if st.button("Edit time", key=f"ed_{aid}"):
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"What time should I move **{a['title']}** to?",
                            })
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div style="height:2px;"></div>', unsafe_allow_html=True)

            if len(pending) > 1:
                st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
                st.markdown('<div class="btn-all">', unsafe_allow_html=True)
                if st.button("Approve all", key="all"):
                    call_execute(pending)
                    approve_result = call_approve()
                    results = approve_result.get("results", [])
                    failed = [item for item in results if item.get("status") == "FAILED"]

                    if failed:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Applied some changes, but {len(failed)} action(s) failed."
                        })
                    else:
                        for a in pending:
                            st.session_state.approved.add(a["id"])
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"✓ All {len(pending)} actions applied to {target_label}.",
                        })

                    refreshed, err = fetch_schedule()
                    if not err and refreshed:
                        st.session_state.data = refreshed
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        elif actions:
            st.success("All actions resolved")

st.markdown('</div>', unsafe_allow_html=True)