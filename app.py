"""Socratic ST/SD Tutor — Streamlit entry point."""

import html as html_lib
import threading
from uuid import uuid4

import streamlit as st

from assess import get_pre_assessment_extraction, score_assessment
from guardrails import apply_tutor_response
from llm import evaluate_bot_answer, get_tutor_response
from logger import (
    init_session,
    log_turn,
    save_bot_results,
    save_feedback_partial,
    save_pre_assessment,
    save_pre_assessment_raw,
    save_quiz_results,
    save_session_outcome,
    save_session_transcript,
)
from models import CASE_STUDY
from quiz import BOT_QUESTIONS, MCQ_QUESTIONS, TOTAL_BOT, TOTAL_MCQ
from render import render_cld

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Socratic ST/SD Tutor",
    layout="wide",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        max-width: 100% !important;
    }
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
    [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }
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
    [data-testid="stGraphVizChart"] svg {
        max-width: 100% !important;
        height: auto !important;
    }
    .chat-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 0.4rem;
    }
    .chat-header h3 { margin: 0; font-size: 1.1rem; font-weight: 700; }
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

# ── Session state initialisation ──────────────────────────────────────────────
_defaults: dict = {
    "messages": [],
    "variables": [],
    "links": [],
    "loops": [],
    "guardrail_errors": [],
    "is_thinking": False,
    "pending_input": None,
    "last_response_debug": None,
    "log_error": None,
    "session_id": None,
    "student_id": None,
    # Phases: pre_assessment | tutoring | quiz_mcq | quiz_bot | feedback | done
    "phase": "pre_assessment",
    # MCQ state
    "quiz_question_idx": 0,
    "quiz_answers": {},
    "quiz_saved": False,
    # BOT state
    "bot_question_idx": 0,
    "bot_messages": [],       # chat history for current BOT question
    "bot_correct": False,     # whether current BOT question is answered correctly
    "bot_evaluating": False,  # whether we're waiting for LLM evaluation
    "bot_attempts": {},       # {question_idx: number_of_attempts}
    "bot_results": {},        # {question_idx: {question, attempts, correct}} — persisted per Q
    # Feedback state
    "feedback_saved": False,
    "feedback_data": {},      # accumulated per-step answers — persisted per step
    "feedback_step": 0,       # which feedback question we're on (0-5)
    # Finish confirmation
    "confirm_finish": False,
    "quiz_started": False,  # True once user has entered the quiz
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Auto-assign student ID (no login gate) ────────────────────────────────────
if not st.session_state.student_id or not st.session_state.session_id:
    random_id = f"STU-{uuid4().hex[:8]}"
    try:
        session_id = init_session(random_id)
        st.session_state.student_id = random_id
        st.session_state.session_id = session_id
    except Exception as e:
        st.error(f"Could not connect to database: {e}")
        st.stop()

# ── Pre-assessment phase ─────────────────────────────────────────────────────
if st.session_state.phase == "pre_assessment":
    st.title("Socratic ST/SD Tutor")
    st.markdown(
        f'<div class="case-study-bar">'
        f'<span class="cs-title">Case Study — Operation Cat Drop (Borneo)</span>'
        f'{CASE_STUDY}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("### Before we begin — map the system yourself")
    st.markdown(
        "Read the case study above. Before the tutor guides you, take a few minutes "
        "to describe what you think the **key variables** are and how they **connect**. "
        "What causes what? Are there any feedback loops?\n\n"
        "_There are no right or wrong answers — this is just your starting mental model._"
    )

    pre_text = st.text_area(
        "Your response",
        height=180,
        placeholder=(
            "e.g. DDT spraying reduces the mosquito population, which reduces malaria. "
            "But DDT also kills parasitic wasps, which allows caterpillars to grow..."
        ),
        key="pre_assessment_input",
    )

    btn_col1, btn_col2, _ = st.columns([1.8, 1.2, 3])
    with btn_col1:
        submit_pressed = st.button(
            "Submit & start guided session",
            type="primary",
            use_container_width=True,
        )
    with btn_col2:
        skip_pressed = st.button(
            "Skip →",
            use_container_width=True,
            help="Skip straight to the Socratic guided session.",
        )

    if submit_pressed:
        if not pre_text.strip():
            st.warning("Please write something before submitting, or click Skip.")
        else:
            session_id = st.session_state.session_id
            text = pre_text.strip()
            try:
                save_pre_assessment_raw(session_id, text)
            except Exception:
                pass

            def _score_and_save(sid: str, raw: str) -> None:
                try:
                    extraction = get_pre_assessment_extraction(raw)
                    score = score_assessment(
                        extraction.extracted_variables,
                        [lp.model_dump() for lp in extraction.extracted_loops],
                    )
                    save_pre_assessment(sid, score, raw)
                except Exception:
                    pass

            threading.Thread(target=_score_and_save, args=(session_id, text), daemon=True).start()
            st.session_state.phase = "tutoring"
            st.rerun()

    if skip_pressed:
        if pre_text.strip():
            try:
                save_pre_assessment_raw(st.session_state.session_id, pre_text.strip())
            except Exception:
                pass
        st.session_state.phase = "tutoring"
        st.rerun()

    st.stop()

# ── Quiz MCQ phase ────────────────────────────────────────────────────────────
if st.session_state.phase == "quiz_mcq":
    if st.button("← Back to Chat", key="back_mcq"):
        st.session_state.phase = "tutoring"
        st.rerun()
    st.title("Part 1 — The 'Fixes that Fail' Archetype")

    idx = st.session_state.quiz_question_idx

    if idx >= TOTAL_MCQ:
        # MCQ done → save and move to BOT
        correct = sum(
            1
            for q_idx, ans in st.session_state.quiz_answers.items()
            if ans == MCQ_QUESTIONS[q_idx]["answer"]
        )
        if correct == TOTAL_MCQ:
            st.success(f"Perfect score — {correct}/{TOTAL_MCQ}!")
        elif correct >= TOTAL_MCQ - 1:
            st.success(f"Great work — {correct}/{TOTAL_MCQ} correct.")
        else:
            st.info(f"Part 1 complete — {correct}/{TOTAL_MCQ} correct.")

        st.markdown(
            "### Key Takeaway\n"
            "The **'Fixes that Fail'** archetype warns us that interventions targeting "
            "*symptoms* rather than *root causes* often generate delayed side-effects "
            "that worsen the original problem.\n\n"
            "**Next:** Let's explore how the key variables actually *behave over time*."
        )
        if st.button("Continue to Part 2: Behaviour Over Time →", type="primary"):
            st.session_state.phase = "quiz_bot"
            st.rerun()
        st.stop()

    # MCQ question screen
    total_all = TOTAL_MCQ + TOTAL_BOT
    st.progress(idx / total_all, text=f"Question {idx + 1} of {total_all}")
    q = MCQ_QUESTIONS[idx]

    st.markdown(f"#### Question {idx + 1}")
    st.markdown(q["question"])

    already_answered = idx in st.session_state.quiz_answers

    selected = st.radio(
        "Choose your answer:",
        options=q["options"],
        key=f"quiz_radio_{idx}",
        index=None,
        disabled=already_answered,
    )

    if not already_answered:
        if st.button("Submit answer", type="primary", disabled=(selected is None)):
            ans_idx = q["options"].index(selected)
            st.session_state.quiz_answers[idx] = ans_idx
            # Persist the full answer set so far immediately
            try:
                answer_log = [
                    {
                        "question": MCQ_QUESTIONS[q_idx]["question"],
                        "selected": MCQ_QUESTIONS[q_idx]["options"][a],
                        "correct_answer": MCQ_QUESTIONS[q_idx]["options"][MCQ_QUESTIONS[q_idx]["answer"]],
                        "is_correct": a == MCQ_QUESTIONS[q_idx]["answer"],
                    }
                    for q_idx, a in st.session_state.quiz_answers.items()
                ]
                correct_so_far = sum(1 for q_idx, a in st.session_state.quiz_answers.items() if a == MCQ_QUESTIONS[q_idx]["answer"])
                save_quiz_results(
                    st.session_state.session_id,
                    {"score": correct_so_far, "total": TOTAL_MCQ, "answers": answer_log},
                )
            except Exception:
                pass
            st.rerun()
    else:
        student_ans = st.session_state.quiz_answers[idx]
        correct_ans = q["answer"]
        if student_ans == correct_ans:
            st.success("Correct! ✓")
        else:
            st.error(f"Not quite. The correct answer: **{q['options'][correct_ans]}**")
        st.info(f"**Why:** {q['explanation']}")

        label = "Next question →" if idx < TOTAL_MCQ - 1 else "See Part 1 results →"
        if st.button(label, type="primary"):
            st.session_state.quiz_question_idx += 1
            st.rerun()

    st.stop()

# ── Quiz BOT phase (chat-based) ──────────────────────────────────────────────
if st.session_state.phase == "quiz_bot":
    if st.button("← Back to Chat", key="back_bot"):
        st.session_state.phase = "tutoring"
        st.rerun()
    bot_idx = st.session_state.bot_question_idx

    if bot_idx >= TOTAL_BOT:
        # All BOT questions done → transition to feedback
        st.title("Reflection Complete")
        st.success(
            f"You answered all {TOTAL_BOT} Behaviour Over Time questions. "
            "Great systems thinking!"
        )
        st.markdown(
            "### Key Takeaway\n"
            "In 'Fixes that Fail', the **timing** of effects is everything. "
            "The fix (DDT) produces immediate benefits but its side-effects travel "
            "through long causal chains with built-in delays. Tracing how each variable "
            "behaves over time — not just its direction — reveals *why* the system "
            "surprises us.\n\n"
            "**The antidote:** map the full system before acting. Trace every balancing "
            "loop your intervention might activate — especially the ones with long delays."
        )
        if st.button("Continue to Feedback →", type="primary"):
            st.session_state.phase = "feedback"
            st.rerun()
        st.stop()

    total_all = TOTAL_MCQ + TOTAL_BOT
    global_idx = TOTAL_MCQ + bot_idx
    st.title("Part 2 — Behaviour Over Time")
    st.progress(global_idx / total_all, text=f"Question {global_idx + 1} of {total_all}")

    bot_q = BOT_QUESTIONS[bot_idx]
    st.markdown(f"#### Question {global_idx + 1}")
    st.markdown(bot_q["question"])

    # Chat display for this BOT question
    chat_container = st.container(height=320)
    with chat_container:
        for msg in st.session_state.bot_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if st.session_state.bot_correct:
        st.success("You've got it! ✓")
        label = "Next question →" if bot_idx < TOTAL_BOT - 1 else "See reflection →"
        if st.button(label, type="primary"):
            st.session_state.bot_question_idx += 1
            st.session_state.bot_messages = []
            st.session_state.bot_correct = False
            st.session_state.bot_evaluating = False
            st.rerun()
    else:
        # Chat input for student answer
        if user_input := st.chat_input(
            "Type your answer...",
            key="bot_chat_input",
        ):
            st.session_state.bot_messages.append(
                {"role": "user", "content": user_input}
            )
            st.session_state.bot_evaluating = True
            st.session_state.bot_attempts[bot_idx] = (
                st.session_state.bot_attempts.get(bot_idx, 0) + 1
            )
            st.rerun()

    # Evaluate pending answer
    if st.session_state.bot_evaluating:
        try:
            result = evaluate_bot_answer(
                question=bot_q["question"],
                reference_answer=bot_q["reference_answer"],
                chat_history=st.session_state.bot_messages,
            )
            st.session_state.bot_messages.append(
                {"role": "assistant", "content": result.feedback}
            )
            st.session_state.bot_correct = result.is_correct
            if result.is_correct:
                # Persist this BOT answer immediately
                st.session_state.bot_results[bot_idx] = {
                    "question": bot_q["question"],
                    "attempts": st.session_state.bot_attempts.get(bot_idx, 1),
                    "correct": True,
                }
                try:
                    save_bot_results(st.session_state.session_id, st.session_state.bot_results)
                except Exception:
                    pass
        except Exception as e:
            st.session_state.bot_messages.append(
                {"role": "assistant", "content": f"Sorry, evaluation failed: {e}. Please try again."}
            )
        st.session_state.bot_evaluating = False
        st.rerun()

    st.stop()

# ── Feedback survey phase (one question per step, each saved immediately) ────
if st.session_state.phase == "feedback":
    if st.button("← Back to Chat", key="back_feedback"):
        st.session_state.phase = "tutoring"
        st.rerun()

    step = st.session_state.feedback_step
    FEEDBACK_TOTAL = 6
    st.title("Session Feedback")
    st.progress(step / FEEDBACK_TOTAL, text=f"Question {step + 1} of {FEEDBACK_TOTAL}")

    def _save_feedback_now() -> None:
        """Write accumulated feedback_data to DB immediately."""
        data = dict(st.session_state.feedback_data)
        data["bot_attempts"] = dict(st.session_state.bot_attempts)
        try:
            save_feedback_partial(st.session_state.session_id, data)
        except Exception:
            pass

    _SCALE = ["1 — Not at all", "2 — A little", "3 — Moderately",
              "4 — Quite a lot", "5 — Very much"]

    if step == 0:
        st.markdown("#### What are your key learning points from this session?")
        val = st.text_area("Your answer", height=120,
                           placeholder="e.g. I learned about feedback loops, unintended consequences...",
                           key="fb_0")
        if st.button("Next →", type="primary", disabled=not val.strip()):
            st.session_state.feedback_data["learning_points"] = val.strip()
            _save_feedback_now()
            st.session_state.feedback_step += 1
            st.rerun()

    elif step == 1:
        st.markdown("#### How much did the LLM tutor help you learn?")
        val = st.radio("", options=_SCALE, index=None, horizontal=True, key="fb_1")
        if st.button("Next →", type="primary", disabled=val is None):
            st.session_state.feedback_data["llm_helpfulness"] = int(val[0])
            _save_feedback_now()
            st.session_state.feedback_step += 1
            st.rerun()

    elif step == 2:
        st.markdown("#### Did this help your understanding of Junior Seminar courses?")
        val = st.radio("", options=_SCALE, index=None, horizontal=True, key="fb_2")
        if st.button("Next →", type="primary", disabled=val is None):
            st.session_state.feedback_data["junior_seminar_understanding"] = int(val[0])
            _save_feedback_now()
            st.session_state.feedback_step += 1
            st.rerun()

    elif step == 3:
        st.markdown("#### Did it help you understand Systems Thinking / System Dynamics fundamentals?")
        val = st.radio("", options=_SCALE, index=None, horizontal=True, key="fb_3")
        if st.button("Next →", type="primary", disabled=val is None):
            st.session_state.feedback_data["sd_fundamentals_understanding"] = int(val[0])
            _save_feedback_now()
            st.session_state.feedback_step += 1
            st.rerun()

    elif step == 4:
        st.markdown("#### What do you think is the strength of this LLM tutor?")
        val = st.text_area("Your answer", height=100,
                           placeholder="e.g. It asked good follow-up questions...",
                           key="fb_4")
        if st.button("Next →", type="primary", disabled=not val.strip()):
            st.session_state.feedback_data["strength"] = val.strip()
            _save_feedback_now()
            st.session_state.feedback_step += 1
            st.rerun()

    elif step == 5:
        st.markdown("#### What is something that can be improved?")
        val = st.text_area("Your answer", height=100,
                           placeholder="e.g. Sometimes the hints were too vague...",
                           key="fb_5")
        if st.button("Submit Feedback", type="primary", disabled=not val.strip()):
            st.session_state.feedback_data["improvement"] = val.strip()
            _save_feedback_now()
            st.session_state.feedback_saved = True
            st.session_state.phase = "done"
            st.rerun()

    st.stop()

# ── Done phase ────────────────────────────────────────────────────────────────
if st.session_state.phase == "done":
    st.title("Thank you!")
    st.balloons()
    st.markdown(
        "Your session is complete. Thank you for participating!\n\n"
        "You may now close this tab."
    )
    if st.button("← Return to my diagram"):
        st.session_state.phase = "tutoring"
        st.rerun()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# TUTORING PHASE (main layout)
# ══════════════════════════════════════════════════════════════════════════════

# Build CLD once — used for display, export, and session-end logging
cld = render_cld(
    st.session_state.variables,
    st.session_state.links,
    st.session_state.loops,
)

# ── Top bar ───────────────────────────────────────────────────────────────────
short_session = str(st.session_state.session_id)[:8] + "..."
safe_log_error = html_lib.escape(str(st.session_state.log_error)) if st.session_state.log_error else ""

# Single row: session tag (auto-width) | buttons (fixed narrow)
info_left, info_right = st.columns([1, 2])
with info_left:
    safe_student_id = html_lib.escape(st.session_state.student_id)
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:8px;'
        f'background:#1e293b;border-radius:6px;padding:5px 12px;font-size:0.78rem;">'
        f'<span style="color:#94a3b8">Your ID</span>'
        f'<span style="background:#334155;border-radius:4px;padding:1px 7px;'
        f'font-family:monospace;font-size:0.73rem;color:#7dd3fc">{safe_student_id}</span>'
        + (f'<span style="color:#f87171;font-size:0.72rem">⚠ {safe_log_error}</span>'
           if safe_log_error else '')
        + '</div>',
        unsafe_allow_html=True,
    )
with info_right:
    if st.session_state.quiz_started:
        # Quiz already entered — just jump back, no confirmation needed
        btn_back, btn_reset = st.columns(2)
        with btn_back:
            if st.button(
                "Back to Quiz →",
                use_container_width=True,
                type="primary",
                help="Return to the quiz",
            ):
                st.session_state.phase = "quiz_mcq" if st.session_state.bot_question_idx == 0 and st.session_state.quiz_question_idx < TOTAL_MCQ else "quiz_bot"
                st.rerun()
        with btn_reset:
            if st.button("Reset", use_container_width=True):
                for key in ["messages", "variables", "links", "loops", "guardrail_errors"]:
                    st.session_state[key] = []
                for key in _defaults:
                    st.session_state[key] = _defaults[key]
                st.rerun()
    elif not st.session_state.confirm_finish:
        btn_finish, btn_reset = st.columns(2)
        with btn_finish:
            if st.button(
                "Finish →",
                use_container_width=True,
                type="primary",
                help="End tutoring session and proceed to the quiz",
            ):
                st.session_state.confirm_finish = True
                st.rerun()
        with btn_reset:
            if st.button("Reset", use_container_width=True):
                for key in ["messages", "variables", "links", "loops", "guardrail_errors"]:
                    st.session_state[key] = []
                for key in _defaults:
                    st.session_state[key] = _defaults[key]
                st.rerun()
    else:
        # Flat horizontal row: label | Yes | No — no vertical expansion
        c_lbl, c_yes, c_no = st.columns([1.4, 1, 1])
        with c_lbl:
            st.markdown(
                '<span style="font-size:0.75rem;color:#fbbf24;white-space:nowrap">'
                '⚠ End session?</span>',
                unsafe_allow_html=True,
            )
        with c_yes:
            if st.button("Yes", type="primary", use_container_width=True):
                try:
                    outcome = score_assessment(
                        st.session_state.variables,
                        st.session_state.loops,
                    )
                    save_session_outcome(st.session_state.session_id, outcome)
                except Exception:
                    pass
                try:
                    transcript_lines = []
                    for m in st.session_state.messages:
                        role = "You" if m["role"] == "user" else "Tutor"
                        transcript_lines.append(f"[{role}]\n{m['content']}\n")
                    save_session_transcript(
                        st.session_state.session_id,
                        "\n".join(transcript_lines),
                        cld.source,
                    )
                except Exception:
                    pass
                st.session_state.confirm_finish = False
                st.session_state.quiz_started = True
                st.session_state.phase = "quiz_mcq"
                st.rerun()
        with c_no:
            if st.button("No", use_container_width=True):
                st.session_state.confirm_finish = False
                st.rerun()

# ── Case study banner ─────────────────────────────────────────────────────────
st.markdown(
    f'<div class="case-study-bar">'
    f'<span class="cs-title">Case Study — Operation Cat Drop (Borneo)</span>'
    f'{CASE_STUDY}</div>',
    unsafe_allow_html=True,
)

chat_col, cld_col, info_col = st.columns([1, 1.4, 0.6])

# ── Middle column: CLD + export ──────────────────────────────────────────────
with cld_col:
    st.subheader("Causal Loop Diagram")
    st.graphviz_chart(cld, use_container_width=True)

    has_chat = bool(st.session_state.messages)
    has_cld = bool(st.session_state.variables)

    if has_chat or has_cld:
        st.markdown(
            '<p style="font-size:0.68rem;color:#64748b;margin:4px 0 4px;">Export:</p>',
            unsafe_allow_html=True,
        )
        exp_cols = st.columns(2)

        if has_chat:
            transcript_lines = []
            for m in st.session_state.messages:
                role = "You" if m["role"] == "user" else "Tutor"
                transcript_lines.append(f"[{role}]\n{m['content']}\n")
            with exp_cols[0]:
                st.download_button(
                    "📄 Transcript",
                    "\n".join(transcript_lines),
                    file_name=f"transcript_{st.session_state.student_id}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

        if has_cld:
            with exp_cols[1]:
                st.download_button(
                    "🔗 CLD (DOT)",
                    cld.source,
                    file_name=f"cld_{st.session_state.student_id}.gv",
                    mime="text/plain",
                    use_container_width=True,
                    help="Open the .gv file at graphviz.online to render it.",
                )

# ── Right column: variables + loops ──────────────────────────────────────────
with info_col:
    vars_html = ""
    if st.session_state.variables:
        for v in st.session_state.variables:
            vars_html += (
                f'<div style="font-size:0.8rem;padding:3px 0;'
                f'border-bottom:1px solid #e2e8f020;color:#e2e8f0">'
                f'· {html_lib.escape(v)}</div>'
            )
    else:
        vars_html = '<div style="font-size:0.78rem;color:#64748b">No variables approved yet.</div>'

    loops_html = ""
    if st.session_state.loops:
        for lp in st.session_state.loops:
            name = html_lib.escape(lp["name"])
            loop_type = html_lib.escape(lp["loop_type"].capitalize())
            seq = lp["variable_sequence"]
            path = html_lib.escape(" → ".join(seq) + (f" → {seq[0]}" if seq else ""))
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
    if st.session_state.is_thinking:
        st.markdown(
            '<div class="chat-header"><h3>Chat</h3>'
            '<span class="thinking-pill">'
            '<span class="dot"></span><span class="dot"></span><span class="dot"></span>'
            '&nbsp;Thinking…</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="chat-header"><h3>Chat</h3></div>', unsafe_allow_html=True)

    chat_container = st.container(height=520)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
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

    st.session_state.guardrail_errors = []

    errors = apply_tutor_response(
        response,
        st.session_state.variables,
        st.session_state.links,
        st.session_state.loops,
    )
    if errors:
        st.session_state.guardrail_errors = errors

    st.session_state.messages.append(
        {"role": "assistant", "content": response.message_to_student}
    )

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
