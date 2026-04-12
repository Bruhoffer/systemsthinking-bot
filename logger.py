"""Supabase logging via direct PostgreSQL connection (psycopg2)."""

import json
import os
from uuid import uuid4

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def _get_conn():
    """Open a fresh connection for each operation.

    Supabase's session pooler drops idle TCP connections, so a persistent
    singleton goes silently dead between Streamlit reruns. A fresh connection
    per call is safer and the pooler handles the overhead.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set in .env")
    return psycopg2.connect(url, connect_timeout=5)


def init_session(student_id: str) -> str:
    """Insert a new session row and return the generated session_id (UUID)."""
    session_id = str(uuid4())
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (id, student_id) VALUES (%s, %s)",
                (session_id, student_id),
            )
        conn.commit()
    finally:
        conn.close()
    return session_id


def get_latest_session(student_id: str) -> dict | None:
    """Return the most recent session row for a student, or None."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, last_active
                FROM sessions
                WHERE student_id = %s
                ORDER BY last_active DESC NULLS LAST
                LIMIT 1
                """,
                (student_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def load_session_state(session_id: str) -> dict:
    """Reconstruct graph state and chat history from a previous session.

    Returns a dict with keys: variables, links, loops, messages.
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Latest snapshot for graph state
            cur.execute(
                """
                SELECT snapshot_variables, snapshot_links, snapshot_loops
                FROM turns
                WHERE session_id = %s
                ORDER BY turn_number DESC
                LIMIT 1
                """,
                (session_id,),
            )
            snapshot_row = cur.fetchone()

            # All turns ordered for chat history reconstruction
            cur.execute(
                """
                SELECT student_input, tutor_response
                FROM turns
                WHERE session_id = %s
                ORDER BY turn_number ASC
                """,
                (session_id,),
            )
            turn_rows = cur.fetchall()
    finally:
        conn.close()

    messages: list[dict] = []
    for row in turn_rows:
        messages.append({"role": "user", "content": row["student_input"]})
        messages.append({"role": "assistant", "content": row["tutor_response"]})

    if snapshot_row:
        def _parse(v):
            return json.loads(v) if isinstance(v, str) else (v or [])
        variables = _parse(snapshot_row["snapshot_variables"])
        links = _parse(snapshot_row["snapshot_links"])
        loops = _parse(snapshot_row["snapshot_loops"])
    else:
        variables, links, loops = [], [], []

    return {"variables": variables, "links": links, "loops": loops, "messages": messages}


def save_pre_assessment(session_id: str, score: dict, raw_text: str = "") -> None:
    """Persist pre-assessment raw response and score.

    Requires these columns to exist:
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS pre_assessment jsonb;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS pre_assessment_raw text;
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET pre_assessment = %s, pre_assessment_raw = %s WHERE id = %s",
                (json.dumps(score), raw_text, session_id),
            )
        conn.commit()
    finally:
        conn.close()


def save_quiz_results(session_id: str, results: dict) -> None:
    """Persist post-assessment quiz results to sessions.quiz_results (jsonb).

    results should include:
        score: int
        total: int
        answers: list of {question, selected, correct_answer, is_correct}

    Requires the column to exist:
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS quiz_results jsonb;
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET quiz_results = %s WHERE id = %s",
                (json.dumps(results), session_id),
            )
        conn.commit()
    finally:
        conn.close()


def save_session_transcript(session_id: str, transcript: str, cld_dot: str) -> None:
    """Persist full chat transcript and CLD DOT source when a session ends.

    Requires these columns to exist:
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS transcript text;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS cld_dot text;
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET transcript = %s, cld_dot = %s WHERE id = %s",
                (transcript, cld_dot, session_id),
            )
        conn.commit()
    finally:
        conn.close()


def save_session_outcome(session_id: str, outcome: dict) -> None:
    """Persist final tutoring outcome to sessions.session_outcome (jsonb).

    Called when the student clicks Finish. Stores variables/loops found
    scored against the reference model, mirroring pre_assessment structure.

    Requires the column to exist:
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS session_outcome jsonb;
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET session_outcome = %s WHERE id = %s",
                (json.dumps(outcome), session_id),
            )
        conn.commit()
    finally:
        conn.close()


def save_pre_assessment_raw(session_id: str, raw_text: str) -> None:
    """Persist only the raw pre-assessment text immediately (before scoring completes).

    Requires the column to exist:
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS pre_assessment_raw text;
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET pre_assessment_raw = %s WHERE id = %s",
                (raw_text, session_id),
            )
        conn.commit()
    finally:
        conn.close()


def log_turn(
    session_id: str,
    turn_number: int,
    student_input: str,
    llm_scratchpad: str,
    tutor_response: str,
    extracted_variables: list,
    extracted_links: list,
    extracted_loops: list,
    guardrail_errors: list,
    snapshot_variables: list,
    snapshot_links: list,
    snapshot_loops: list,
) -> None:
    """Insert one turn row and update the session's last_active timestamp."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO turns (
                    session_id, turn_number,
                    student_input, llm_scratchpad, tutor_response,
                    extracted_variables, extracted_links, extracted_loops,
                    guardrail_errors,
                    snapshot_variables, snapshot_links, snapshot_loops
                ) VALUES (
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s,
                    %s, %s, %s
                )
                """,
                (
                    session_id,
                    turn_number,
                    student_input,
                    llm_scratchpad,
                    tutor_response,
                    json.dumps(extracted_variables),
                    json.dumps(extracted_links),
                    json.dumps(extracted_loops),
                    json.dumps(guardrail_errors),
                    json.dumps(snapshot_variables),
                    json.dumps(snapshot_links),
                    json.dumps(snapshot_loops),
                ),
            )
            cur.execute(
                "UPDATE sessions SET last_active = now() WHERE id = %s",
                (session_id,),
            )
        conn.commit()
    finally:
        conn.close()
