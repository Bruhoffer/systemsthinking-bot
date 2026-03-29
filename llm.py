"""OpenAI SDK orchestration with Structured Outputs."""

import os

from openai import OpenAI
from dotenv import load_dotenv

from models import CASE_STUDY, SYSTEM_PROMPT, TutorResponse

load_dotenv()

_client: OpenAI | None = None

MAX_HISTORY_MESSAGES = 40  # keep last N messages to stay within token limits


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Add it to your .env file."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def _build_messages(
    chat_history: list[dict],
    variables: list[str],
    links: list[dict],
    loops: list[dict] | None = None,
    guardrail_error: str | None = None,
) -> list[dict]:
    """Assemble the full message payload for the LLM."""
    loops = loops or []
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                f"## Case Study\n{CASE_STUDY}\n\n"
                f"## Current Graph State\n"
                f"Approved variables: {variables if variables else '(none yet)'}\n"
                f"Approved links: {links if links else '(none yet)'}\n"
                f"Identified loops: {loops if loops else '(none yet)'}"
            ),
        },
    ]

    if guardrail_error:
        messages.append({"role": "system", "content": guardrail_error})

    trimmed = chat_history[-MAX_HISTORY_MESSAGES:]
    messages.extend(trimmed)

    return messages


def get_tutor_response(
    chat_history: list[dict],
    variables: list[str],
    links: list[dict],
    loops: list[dict] | None = None,
    guardrail_error: str | None = None,
    model: str = "gpt-4o",
) -> TutorResponse:
    """Call OpenAI with Structured Outputs and return a parsed TutorResponse."""
    client = _get_client()
    messages = _build_messages(
        chat_history, variables, links, loops, guardrail_error
    )

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=TutorResponse,
    )

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("LLM returned unparseable response.")

    return parsed
