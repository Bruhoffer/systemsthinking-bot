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
if "log_error" not in st.session_state:
    st.session_state.log_error = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "student_id" not in st.session_state:
    st.session_state.student_id = None

# ── Student ID gate — must enter before chatting ─────────────────────────────
if not st.session_state.student_id:
    st.title("Socratic ST/SD Tutor")
    st.markdown("Enter your student ID to begin.")
    with st.form("student_id_form"):
        sid = st.text_input("Student ID (e.g. A0123456X)")
        submitted = st.form_submit_button("Start Session")
    if submitted and sid.strip():
        st.session_state.student_id = sid.strip()
        try:
            st.session_state.session_id = init_session(sid.strip())
        except Exception as e:
            st.error(f"Could not connect to database: {e}")
            st.stop()
        st.rerun()
    st.stop()

# ── Layout ───────────────────────────────────────────────────────────────────
st.title("Socratic ST/SD Tutor")

left_col, right_col = st.columns([1, 1])

# ── Right column: CLD visualisation ─────────────────────────────────────────
with right_col:
    st.subheader("Causal Loop Diagram")
    cld = render_cld(
        st.session_state.variables,
        st.session_state.links,
        st.session_state.loops,
    )
    st.graphviz_chart(cld, width="stretch")

    if st.session_state.variables:
        with st.expander("Current variables"):
            for v in st.session_state.variables:
                st.markdown(f"- {v}")

    if st.session_state.loops:
        with st.expander("Feedback loops"):
            for lp in st.session_state.loops:
                loop_type = lp["loop_type"].capitalize()
                st.markdown(
                    f"- **{lp['name']}** ({loop_type}): "
                    f"{' → '.join(lp['variable_sequence'])} → ..."
                )

# ── Left column: case study + chat ──────────────────────────────────────────
with left_col:
    with st.expander("Case Study: Operation Cat Drop (Borneo)", expanded=False):
        st.markdown(CASE_STUDY)

    st.subheader("Chat")

    # Scrollable chat history in a fixed-height container
    chat_container = st.container(height=480)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

# ── Chat input ───────────────────────────────────────────────────────────────
if user_input := st.chat_input("Describe a variable or causal link..."):
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Thinking..."):
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
            st.error(f"LLM error: {e}")
            st.stop()

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
            student_input=user_input,
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
        # Store error in session state so it survives st.rerun()
        st.session_state.log_error = str(e)

    st.rerun()

# ── Sidebar: controls ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**Student:** {st.session_state.student_id}")
    st.markdown(f"**Session:** `{st.session_state.session_id}`")
    if st.session_state.log_error:
        st.error(f"Logging error: {st.session_state.log_error}")
    st.divider()
    if st.button("Reset session"):
        st.session_state.messages = []
        st.session_state.variables = []
        st.session_state.links = []
        st.session_state.loops = []
        st.session_state.guardrail_errors = []
        st.session_state.session_id = None
        st.session_state.student_id = None
        st.rerun()
