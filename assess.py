"""Pre-assessment extraction and silent scoring for the ST/SD Tutor."""

import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from models import CASE_STUDY, CausalLink, FeedbackLoop

load_dotenv()

# ── Reference model ───────────────────────────────────────────────────────────
# Each tuple: (canonical_name, frozenset of accepted surface forms)
_REFERENCE_VARIABLE_GROUPS: list[tuple[str, frozenset]] = [
    ("Malaria Incidence", frozenset({
        "malaria incidence", "malaria", "malaria cases", "malaria rate",
        "incidence of malaria",
    })),
    ("DDT Spraying Level", frozenset({
        "ddt spraying level", "ddt spraying", "ddt application", "ddt level",
        "amount of ddt", "ddt use", "ddt usage", "ddt",
    })),
    ("Mosquito Population", frozenset({
        "mosquito population", "mosquitoes", "number of mosquitoes", "mosquito numbers",
    })),
    ("Parasitic Wasp Population", frozenset({
        "parasitic wasp population", "wasps", "wasp population", "parasitic wasps",
        "wasp numbers",
    })),
    ("Thatch-Eating Caterpillar Population", frozenset({
        "thatch-eating caterpillar population", "caterpillars", "caterpillar population",
        "thatch caterpillars", "number of caterpillars",
    })),
    ("Roof Integrity", frozenset({
        "roof integrity", "number of collapsed roofs", "roof damage level",
        "collapsed roofs", "roof collapse", "roof condition", "roofs", "roof damage",
    })),
    ("DDT Accumulated Insects", frozenset({
        "ddt accumulated insects", "ddt in insects", "insect ddt level",
        "ddt concentration in insects", "ddt bioaccumulation in insects",
    })),
    ("DDT Accumulated Geckos", frozenset({
        "ddt accumulated geckos", "ddt in geckos", "gecko ddt level",
        "ddt concentration in geckos", "ddt bioaccumulation in geckos", "geckos",
    })),
    ("Cat Population", frozenset({
        "cat population", "cats", "number of cats", "cat numbers",
    })),
    ("Rat Population", frozenset({
        "rat population", "rats", "number of rats", "rat numbers",
    })),
    ("Plague Incidence", frozenset({
        "plague incidence", "plague", "plague cases", "bubonic plague", "rat-borne plague",
    })),
    ("Grain Shortages", frozenset({
        "grain shortages", "grain supply", "food shortage", "grain stores",
        "grain", "food supply", "grain destruction",
    })),
    ("Cat Parachute Drops", frozenset({
        "cat parachute drops", "parachuting cats", "cat drops",
        "operation cat drop", "cats parachuted",
    })),
]

# Each tuple: (loop_name, frozenset of key variable forms that uniquely identify it)
# B5 listed before B4 (superset takes priority)
_REFERENCE_LOOP_KEYS: list[tuple[str, frozenset]] = [
    ("B1", frozenset({"malaria incidence", "ddt spraying level", "mosquito population"})),
    ("B2", frozenset({"parasitic wasp population", "thatch-eating caterpillar population"})),
    ("B3", frozenset({"ddt accumulated insects", "ddt accumulated geckos"})),
    ("B5", frozenset({"cat population", "rat population", "grain shortages", "cat parachute drops"})),
    ("B4", frozenset({"cat population", "rat population"})),
    ("R1", frozenset({"ddt accumulated geckos", "cat population"})),
]

TOTAL_REFERENCE_VARIABLES = len(_REFERENCE_VARIABLE_GROUPS)  # 13
TOTAL_REFERENCE_LOOPS = len(_REFERENCE_LOOP_KEYS)  # 6


# ── Extraction schema ─────────────────────────────────────────────────────────

class ExtractionResponse(BaseModel):
    """Minimal schema for pre-assessment — no Socratic output fields needed."""
    extracted_variables: list[str] = []
    extracted_links: list[CausalLink] = []
    extracted_loops: list[FeedbackLoop] = []


_EXTRACTION_PROMPT = (
    "You are a structured extraction system for a systems thinking case study.\n"
    "The user will write a free-text description of the Borneo DDT/malaria case.\n"
    "Extract every variable, causal link, and feedback loop they explicitly mention.\n"
    "Be lenient: accept informal names, synonyms, and partial descriptions.\n"
    "Do NOT invent anything not stated by the user.\n\n"
    f"Case study context:\n{CASE_STUDY}"
)


def get_pre_assessment_extraction(student_text: str) -> ExtractionResponse:
    """Call GPT-4o-mini to extract variables/links/loops from free-text response."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set.")
    client = OpenAI(api_key=api_key)
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _EXTRACTION_PROMPT},
            {"role": "user", "content": student_text},
        ],
        response_format=ExtractionResponse,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("Extraction returned unparseable response.")
    return parsed


# ── Scoring ───────────────────────────────────────────────────────────────────

def _match_reference_variable(student_var: str) -> str | None:
    """Return canonical variable name if student_var matches any reference group."""
    sv = student_var.strip().lower()
    stops = {"the", "a", "an", "of", "in", "and", "or", "level", "number", "amount"}

    for canonical, forms in _REFERENCE_VARIABLE_GROUPS:
        if sv in forms:
            return canonical
        for form in forms:
            if form in sv or sv in form:
                return canonical
        # Word-overlap fallback (≥60% of shorter side, after removing stop words)
        sv_words = set(sv.split()) - stops
        for form in forms:
            fw = set(form.split()) - stops
            if sv_words and fw:
                overlap = sv_words & fw
                if len(overlap) >= 0.6 * min(len(sv_words), len(fw)):
                    return canonical
    return None


def score_assessment(
    extracted_variables: list[str],
    extracted_loops: list[dict],
) -> dict:
    """Compare extracted items against the reference model (silent — not shown to student).

    Returns:
        variables_found: int
        loops_found: int
        total_variables: int  (13)
        total_loops: int      (6)
        matched_variables: list[str]  canonical names matched
        matched_loops: list[str]      loop names matched e.g. ["B1", "R1"]
    """
    matched_vars: set[str] = set()
    for var in extracted_variables:
        canonical = _match_reference_variable(var)
        if canonical:
            matched_vars.add(canonical)

    matched_loops: set[str] = set()
    for loop in extracted_loops:
        seq_set = {v.lower() for v in loop.get("variable_sequence", [])}
        for name, key_vars in _REFERENCE_LOOP_KEYS:
            if name not in matched_loops and key_vars.issubset(seq_set):
                matched_loops.add(name)

    return {
        "variables_found": len(matched_vars),
        "loops_found": len(matched_loops),
        "total_variables": TOTAL_REFERENCE_VARIABLES,
        "total_loops": TOTAL_REFERENCE_LOOPS,
        "matched_variables": sorted(matched_vars),
        "matched_loops": sorted(matched_loops),
    }
