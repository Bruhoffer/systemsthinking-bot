"""Socratic ST/SD Tutor — Streamlit entry point."""

import streamlit as st

from models import CASE_STUDY
from render import render_cld
from guardrails import apply_tutor_response
from llm import get_tutor_response
from logger import init_session, log_turn

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Socratic ST/SD Tutor",
    layout="wide",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Shrink default block padding so more content fits */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        max-width: 100% !important;
    }

    /* Top info bar: student + session + reset */
    .top-bar {
        display: flex;
        align-items: center;
        gap: 18px;
        background: #1e293b;
        color: #e2e8f0;
        border-radius: 8px;
        padding: 7px 16px;
        font-size: 0.8rem;
        margin-bottom: 10px;
        flex-wrap: wrap;
    }
    .top-bar .label { color: #94a3b8; margin-right: 3px; }
    .top-bar .value { font-weight: 600; color: #f1f5f9; }
    .top-bar .tag {
        background: #334155;
        border-radius: 4px;
        padding: 1px 7px;
        font-family: monospace;
        font-size: 0.75rem;
        color: #7dd3fc;
    }
    .top-bar form { margin: 0; }
    .top-bar .reset-btn {
        margin-left: auto;
        background: #dc2626;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 4px 12px;
        cursor: pointer;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .top-bar .reset-btn:hover { background: #b91c1c; }

    /* Case study scrollable banner */
    .case-study-bar {
        background: #0f172a;
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 10px 16px;
        font-size: 0.81rem;
        line-height: 1.6;
        color: #cbd5e1;
        max-height: 100px;
        overflow-y: auto;
        margin-bottom: 10px;
    }
    .case-study-bar .cs-title {
        font-size: 0.7rem;
        letter-spacing: 0.07em;
        color: #60a5fa;
        text-transform: uppercase;
        font-weight: 700;
        display: block;
        margin-bottom: 5px;
    }

    /* Hide the default Streamlit sidebar toggle when sidebar is empty */
    [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }

    /* Scrollable info panel for variables and loops */
    .info-scroll {
        max-height: 420px;
        overflow-y: auto;
        padding-right: 4px;
    }
    .info-scroll::-webkit-scrollbar { width: 4px; }
    .info-scroll::-webkit-scrollbar-track { background: transparent; }
    .info-scroll::-webkit-scrollbar-thumb {
        background: #334155;
        border-radius: 4px;
    }

    /* Fix CLD column height so it doesn't grow with content */
    [data-testid="stGraphVizChart"] svg {
        max-width: 100% !important;
        height: auto !important;
    }

    /* Thinking indicator inline with Chat header */
    .chat-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 0.4rem;
    }
    .chat-header h3 {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 700;
    }
    .thinking-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #1e3a5f;
        color: #7dd3fc;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        animation: pulse 1.2s ease-in-out infinite;
    }
    .thinking-pill .dot {
        width: 6px; height: 6px;
        background: #38bdf8;
        border-radius: 50%;
        display: inline-block;
        animation: bounce 1.2s ease-in-out infinite;
    }
    .thinking-pill .dot:nth-child(2) { animation-delay: 0.2s; }
    .thinking-pill .dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce {
        0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
        40% { transform: translateY(-4px); opacity: 1; }
    }
    @keyframes pulse {
        0%, 100% { opacity: 0.85; }
        50% { opacity: 1; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state initialisation ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "variables" not in st.session_state:
    st.session_state.variables = []
if "links" not in st.session_state:
    st.session_state.links = []
if "loops" not in st.session_state:
    st.session_state.loops = []
if "guardrail_errors" not in st.session_state:
    st.session_state.guardrail_errors = []
if "is_thinking" not in st.session_state:
    st.session_state.is_thinking = False
if "pending_input" not in st.session_state:
    st.session_state.pending_input = None
if "last_response_debug" not in st.session_state:
    st.session_state.last_response_debug = None
if "log_error" not in st.session_state:
    st.session_state.log_error = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "student_id" not in st.session_state:
    st.session_state.student_id = None

# ── Student ID gate — must enter before chatting ─────────────────────────────
if not st.session_state.student_id or not st.session_state.session_id:
    st.title("Socratic ST/SD Tutor")
    st.markdown("Enter your student ID to begin.")
    with st.form("student_id_form"):
        sid = st.text_input("Student ID (e.g. A0123456X)")
        submitted = st.form_submit_button("Start Session")
    if submitted and sid.strip():
        try:
            session_id = init_session(sid.strip())
            st.session_state.student_id = sid.strip()
            st.session_state.session_id = session_id
            st.rerun()
        except Exception as e:
            st.error(f"Could not connect to database: {e}")
    st.stop()

# ── Top bar: student info + reset ────────────────────────────────────────────
info_left, info_right = st.columns([5, 1])
with info_left:
    short_session = str(st.session_state.session_id)[:8] + "..."
    st.markdown(
        f'<div class="top-bar">'
        f'<span><span class="label">Student</span>'
        f'<span class="value">{st.session_state.student_id}</span></span>'
        f'<span><span class="label">Session</span>'
        f'<span class="tag">{short_session}</span></span>'
        + (f'<span style="color:#f87171;font-size:0.75rem">⚠ Logging error: {st.session_state.log_error}</span>'
           if st.session_state.log_error else '')
        + '</div>',
        unsafe_allow_html=True,
    )
with info_right:
    if st.button("Reset session", type="primary"):
        for key in ["messages", "variables", "links", "loops", "guardrail_errors"]:
            st.session_state[key] = []
        st.session_state.session_id = None
        st.session_state.student_id = None
        st.rerun()

# ── Case study banner ─────────────────────────────────────────────────────────
st.markdown(
    f'<div class="case-study-bar">'
    f'<span class="cs-title">Case Study — Operation Cat Drop (Borneo)</span>'
    f'{CASE_STUDY}</div>',
    unsafe_allow_html=True,
)

chat_col, cld_col, info_col = st.columns([1, 1.4, 0.6])

# ── Middle column: CLD ───────────────────────────────────────────────────────
with cld_col:
    st.subheader("Causal Loop Diagram")
    cld = render_cld(
        st.session_state.variables,
        st.session_state.links,
        st.session_state.loops,
    )
    st.graphviz_chart(cld, width="stretch")

# ── Right column: variables + loops (fixed width, scrollable) ───────────────
with info_col:
    # Build the full HTML block and render it in one scrollable div
    vars_html = ""
    if st.session_state.variables:
        for v in st.session_state.variables:
            vars_html += (
                f'<div style="font-size:0.8rem;padding:3px 0;'
                f'border-bottom:1px solid #e2e8f020;color:#e2e8f0">'
                f'· {v}</div>'
            )
    else:
        vars_html = '<div style="font-size:0.78rem;color:#64748b">No variables approved yet.</div>'

    loops_html = ""
    if st.session_state.loops:
        for lp in st.session_state.loops:
            name = lp["name"]
            loop_type = lp["loop_type"].capitalize()
            seq = lp["variable_sequence"]
            path = " → ".join(seq) + (f" → {seq[0]}" if seq else "")
            color = "#16a34a" if lp["loop_type"] == "reinforcing" else "#dc2626"
            loops_html += (
                f'<div style="margin-bottom:8px;padding:7px 9px;'
                f'border-left:3px solid {color};border-radius:4px;'
                f'background:rgba(255,255,255,0.04)">'
                f'<span style="font-weight:700;color:{color};font-size:0.82rem">{name}</span> '
                f'<span style="font-size:0.74rem;color:#64748b">({loop_type})</span><br>'
                f'<span style="font-size:0.74rem;line-height:1.6;color:#cbd5e1">{path}</span>'
                f'</div>'
            )
    else:
        loops_html = '<div style="font-size:0.78rem;color:#64748b">No loops identified yet.</div>'

    st.markdown(
        f'<div class="info-scroll">'
        f'<div style="font-size:0.7rem;font-weight:700;letter-spacing:0.06em;'
        f'color:#60a5fa;text-transform:uppercase;margin-bottom:6px">Variables</div>'
        f'{vars_html}'
        f'<div style="margin:12px 0 6px;font-size:0.7rem;font-weight:700;'
        f'letter-spacing:0.06em;color:#60a5fa;text-transform:uppercase">Feedback Loops</div>'
        f'{loops_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.divider()
    with st.expander("Debug: last LLM extraction", expanded=False):
        if st.session_state.last_response_debug:
            d = st.session_state.last_response_debug
            st.markdown("**Scratchpad:**")
            st.caption(d["scratchpad"])
            st.markdown(f"**extracted_variables:** `{d['extracted_variables']}`")
            st.markdown(f"**extracted_links:** `{d['extracted_links']}`")
            st.markdown(f"**extracted_loops:** `{d['extracted_loops']}`")
        else:
            st.caption("No response yet.")

# ── Left column: chat ────────────────────────────────────────────────────────
with chat_col:
    # Header row: "Chat" title + animated thinking pill side by side
    if st.session_state.is_thinking:
        st.markdown(
            '<div class="chat-header">'
            '<h3>Chat</h3>'
            '<span class="thinking-pill">'
            '<span class="dot"></span><span class="dot"></span><span class="dot"></span>'
            '&nbsp;Thinking…'
            '</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="chat-header"><h3>Chat</h3></div>', unsafe_allow_html=True)

    chat_container = st.container(height=520)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

# ── Chat input (pinned to bottom by Streamlit default) ───────────────────────
if user_input := st.chat_input("Describe a variable or causal link..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.pending_input = user_input
    st.session_state.is_thinking = True
    st.rerun()

if st.session_state.is_thinking:
    try:
        guardrail_ctx = (
            "\n".join(st.session_state.guardrail_errors)
            if st.session_state.guardrail_errors
            else None
        )
        response = get_tutor_response(
            chat_history=st.session_state.messages,
            variables=st.session_state.variables,
            links=st.session_state.links,
            loops=st.session_state.loops,
            guardrail_error=guardrail_ctx,
        )
    except Exception as e:
        st.session_state.is_thinking = False
        st.error(f"LLM error: {e}")
        st.stop()

    st.session_state.is_thinking = False
    st.session_state.last_response_debug = {
        "scratchpad": response.student_state_analysis,
        "extracted_variables": response.extracted_variables,
        "extracted_links": [lnk.model_dump() for lnk in response.extracted_links],
        "extracted_loops": [lp.model_dump() for lp in response.extracted_loops],
    }

    # Reset guardrail errors after they have been sent
    st.session_state.guardrail_errors = []

    # Apply guardrails and update graph state
    errors = apply_tutor_response(
        response,
        st.session_state.variables,
        st.session_state.links,
        st.session_state.loops,
    )
    if errors:
        st.session_state.guardrail_errors = errors

    # Append assistant message
    st.session_state.messages.append(
        {"role": "assistant", "content": response.message_to_student}
    )

    # Log this turn to Supabase
    turn_number = len([m for m in st.session_state.messages if m["role"] == "user"])
    try:
        log_turn(
            session_id=st.session_state.session_id,
            turn_number=turn_number,
            student_input=st.session_state.pending_input or "",
            llm_scratchpad=response.student_state_analysis,
            tutor_response=response.message_to_student,
            extracted_variables=response.extracted_variables,
            extracted_links=[lnk.model_dump() for lnk in response.extracted_links],
            extracted_loops=[lp.model_dump() for lp in response.extracted_loops],
            guardrail_errors=errors,
            snapshot_variables=list(st.session_state.variables),
            snapshot_links=list(st.session_state.links),
            snapshot_loops=list(st.session_state.loops),
        )
        st.session_state.log_error = None
    except Exception as e:
        st.session_state.log_error = str(e)

    st.session_state.pending_input = None

    st.rerun()

