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
    return psycopg2.connect(url)


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
