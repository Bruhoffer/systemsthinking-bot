"""OpenAI SDK orchestration with Structured Outputs."""

import os

from openai import OpenAI
from pydantic import BaseModel
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


# ── BOT (Behaviour Over Time) evaluator ──────────────────────────────────────

class BotEvaluation(BaseModel):
    """Structured output for BOT answer evaluation."""
    is_correct: bool
    feedback: str  # Socratic hint if wrong, confirmation + explanation if correct


_BOT_SYSTEM_PROMPT = """\
You are a Socratic evaluator for a Systems Thinking course on the Borneo DDT case study.

The student is answering a Behaviour Over Time (BOT) question about how variables change \
over time after DDT spraying in Borneo.

You have:
- The question the student was asked
- The reference answer (the correct explanation)
- The conversation so far (the student may have already attempted and received feedback)

Your job:
1. Judge whether the student's latest message demonstrates sufficient understanding \
   of the key concept in the reference answer. They do NOT need to use the exact words — \
   they just need to show they understand the core dynamics (direction of change, why, \
   and any relevant delays or causal chains).
2. If CORRECT: set is_correct=true. Give a brief confirmation that reinforces the key insight. \
   Do not just say "correct" — explain WHY their reasoning is right in 1-2 sentences.
3. If INCORRECT or INCOMPLETE: set is_correct=false. Do NOT reveal the answer. Instead, \
   give a Socratic hint — point to a gap in their reasoning or ask a guiding question. \
   Keep it short (1-2 sentences).

Be encouraging but rigorous. Accept informal language and imprecise wording as long as the \
core causal reasoning is sound."""


def evaluate_bot_answer(
    question: str,
    reference_answer: str,
    chat_history: list[dict],
    model: str = "gpt-4o-mini",
) -> BotEvaluation:
    """Evaluate a student's BOT answer using an LLM.

    Args:
        question: The BOT question text.
        reference_answer: The expected correct answer for the evaluator.
        chat_history: List of {"role": ..., "content": ...} for this BOT question.
        model: Which model to use (gpt-4o-mini is fast + cheap enough).
    """
    client = _get_client()
    messages = [
        {"role": "system", "content": _BOT_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                f"## BOT Question\n{question}\n\n"
                f"## Reference Answer (DO NOT reveal to student)\n{reference_answer}"
            ),
        },
        *chat_history,
    ]

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=BotEvaluation,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("BOT evaluation returned unparseable response.")
    return parsed
