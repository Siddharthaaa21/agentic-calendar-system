import streamlit as st
import requests
from datetime import datetime
API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Axon",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg:       #0a0d12;
    --surface:  #111520;
    --border:   #1e2a3a;
    --accent:   #2563eb;
    --accent-2: #1d4ed8;
    --muted:    #3d5166;
    --text:     #e2e8f0;
    --text-2:   #64748b;
    --red:      #ef4444;
    --green:    #10b981;
    --amber:    #f59e0b;
}

html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text) !important;
}

.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stSidebar"] { display: none; }
#MainMenu, footer, header, [data-testid="stToolbar"], .stDeployButton { display: none !important; }

/* ── HEADER ── */
.hdr {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
}
.hdr-dot {
    width: 8px; height: 8px; border-radius: 50%; background: var(--green);
    animation: pulse 2.5s ease infinite; flex-shrink: 0;
}
.hdr-dot.offline { background: var(--muted); animation: none; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .4; } }
.hdr-title { font-size: 14px; font-weight: 600; letter-spacing: -.2px; }
.hdr-sub   { font-size: 11px; color: var(--text-2); }
.hdr-right { margin-left: auto; font-size: 11px; color: var(--muted);
             font-family: 'JetBrains Mono', monospace; }

/* ── COLUMNS ── */
[data-testid="stHorizontalBlock"] > div:first-child {
    border-right: 1px solid var(--border);
}

/* ── CHAT ── */
[data-testid="stChatMessage"] { background: transparent !important; }
[data-testid="stChatMessageContent"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px 10px 10px 10px !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
    padding: 10px 14px !important;
    box-shadow: none !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
    background: rgba(37,99,235,.1) !important;
    border-color: rgba(37,99,235,.25) !important;
    border-radius: 10px 2px 10px 10px !important;
}
[data-testid="stChatInput"] > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
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
    border-radius: 7px !important;
    transition: all .15s !important;
    padding: 5px 14px !important;
}
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
    background: var(--accent) !important; color: #fff !important;
    border: none !important; width: 100% !important;
}
.btn-all button:hover { background: var(--accent-2) !important; }

/* ── CARDS ── */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    box-shadow:
        rgba(0,0,0,.55) 0px 0px,
        rgba(0,0,0,.54) 0px 9px 20px,
        rgba(0,0,0,.45) 0px 37px 37px,
        rgba(0,0,0,.28) 0px 84px 50px;
}
.card-label {
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 1px; color: var(--muted); margin-bottom: 10px;
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
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 10px; }
.stat  { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; }
.stat-n { font-size: 20px; font-weight: 600; font-family: 'JetBrains Mono', monospace; line-height: 1; }
.stat-l { font-size: 10px; color: var(--text-2); margin-top: 3px; text-transform: uppercase; letter-spacing: .5px; }

/* ── TIMELINE ── */
.tl { display: flex; flex-direction: column; }
.tl-row {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 7px 0; border-bottom: 1px solid var(--border); font-size: 12px;
}
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
    padding: 11px 12px; border-radius: 8px; margin-bottom: 8px;
    border: 1px solid var(--border);
    background: rgba(37,99,235,.03); font-size: 12px;
}
.act-type { font-size: 10px; font-weight: 600; text-transform: uppercase;
            letter-spacing: .8px; color: var(--accent); margin-bottom: 3px; }
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
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def fetch_schedule():
    """Returns (data_dict, error_string). One of them will be None."""
    try:
        r = requests.get(f"{API_URL}/today", timeout=6)
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
        return requests.post(f"{API_URL}/execute", json={"actions": actions}, timeout=6).json()
    except Exception as e:
        st.warning(f"Execute failed: {e}")
        return {}
    

def call_approve():
    try:
        return requests.post(f"{API_URL}/approve", json={"approval": "yes"}, timeout=6).json()
    except Exception as e:
        st.warning(f"Approve failed: {e}")
        return {}
def ask_agent(prompt):
    try:
        r = requests.post(
            f"{API_URL}/chat",
            json={"message": prompt},
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
# ─────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────
defaults = {
    "messages": [{
        "role": "assistant",
        "content": (
            "Hi — I'm **Axon**, your AI calendar agent.\n\n"
            "I can analyze your schedule, detect conflicts, "
            "suggest optimizations, and help reschedule meetings intelligently.\n\n"
            "Try asking:\n"
            "- 'How busy is my day?'\n"
            "- 'What should I move?'\n"
            "- 'Suggest better focus slots'\n"
            "- 'Reschedule my low priority meetings'"
        ),
    }],
    "data": None,
    "error": None,
    "approved": set(),
    "rejected": set(),
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Auto-load calendar once
if st.session_state.data is None:
    with st.spinner("Connecting to Google Calendar..."):
        result, err = fetch_schedule()

    if err:
        st.session_state.error = err
    else:
        st.session_state.data = result

connected   = st.session_state.data is not None
dot_cls     = "hdr-dot" if connected else "hdr-dot offline"
status_text = "Connected to Google Calendar" if connected else "Not connected"

st.markdown(f"""
<div class="hdr">
    <div class="{dot_cls}"></div>
    <div>
        <div class="hdr-title">Axon</div>
        <div class="hdr-sub">{status_text}</div>
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
    st.markdown('<div style="padding:16px 20px 0;">', unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    # if prompt := st.chat_input("Message Axon…"):
        # 
    if prompt := st.chat_input("Message Axon…"):
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        with st.spinner("Axon is reasoning..."):
            response = ask_agent(prompt)

        reply = response.get("reply", "No response from agent.")

        if "data" in response:
            st.session_state.data = response["data"]

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply
        })
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

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
    else:
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
            rows = ""
            for e in events:
                p   = e.get("priority", "MED")
                dot = {"HIGH": "h", "MED": "m", "LOW": "l"}.get(p, "m")
                is_conflict = e.get("conflict") or "conflict" in e["title"].lower()
                cls  = "tl-row conflict" if is_conflict else "tl-row"
                name = (f'<span class="tl-name err">⚠ {e["title"]}</span>'
                        if is_conflict else f'<span class="tl-name">{e["title"]}</span>')
                rows += f"""
                <div class="{cls}">
                    <span class="tl-time">{e['start']}</span>
                    <div class="dot {dot}"></div>
                    <div>
                        {name}
                        <div class="tl-sub">{e['start']} – {e['end']} · {p}</div>
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
                <div style="height:2px;border-radius:2px;background:var(--border);margin-top:4px;overflow:hidden;">
                    <div style="height:100%;width:{load_pct}%;background:{load_c};border-radius:2px;"></div>
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
            {cfl_html}
        </div>
        """, unsafe_allow_html=True)



    # Actions
    icon_map = {"RESCHEDULE": "↗", "REBALANCE": "⇄", "CANCEL": "×", "CREATE": "+"}

    if pending:
        for a in pending:
            aid  = a["id"]
            icon = icon_map.get(a["action"], "→")
            st.markdown(f"""
            <div class="act">
                <div class="act-type">{icon} {a['action']}</div>
                <div class="act-desc"><strong>{a['title']}</strong> — {a.get('detail', '')}</div>
            </div>
            """, unsafe_allow_html=True)

            needs_edit = a["action"] in ("RESCHEDULE", "REBALANCE")
            cols = st.columns([1, 1, 1] if needs_edit else [1, 1, 2])

            with cols[0]:
                st.markdown('<div class="btn-approve">', unsafe_allow_html=True)
                if st.button("Approve", key=f"ap_{aid}"):
                    call_execute([a])
                    st.session_state.approved.add(aid)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"✓ **{a['title']}** pushed to Google Calendar.",
                    })
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
                call_approve()
                for a in pending:
                    st.session_state.approved.add(a["id"])
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"✓ All {len(pending)} actions applied to Google Calendar.",
                })
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    elif actions:
        st.success("All actions resolved")

st.markdown('</div>', unsafe_allow_html=True)