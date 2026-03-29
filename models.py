"""Pydantic schemas, enums, and constants for the Socratic ST/SD Tutor."""

from typing import Optional

from pydantic import BaseModel


class CausalLink(BaseModel):
    """A directed causal edge between two system variables."""

    source: str
    target: str
    polarity: str  # "+" or "-"
    has_delay: bool


class FeedbackLoop(BaseModel):
    """A named feedback loop consisting of an ordered cycle of variables."""

    name: str  # e.g. "R1" or "B1"
    loop_type: str  # "reinforcing" or "balancing"
    variable_sequence: list[str]  # ordered list forming the cycle


class TutorResponse(BaseModel):
    """Structured output schema for the LLM tutor.

    Lists allow multi-extraction: the LLM can approve multiple variables,
    links, and loops from a single student message.
    """

    student_state_analysis: str
    message_to_student: str
    extracted_variables: list[str] = []
    extracted_links: list[CausalLink] = []
    extracted_loops: list[FeedbackLoop] = []


SYSTEM_PROMPT = (
    "You are an ST/SD tutor. Never give the direct answer or list the "
    "variables/feedback loops outright. Guide the student using the Iceberg "
    "Model. Enforce rigorous terminology: variables MUST be quantifiable "
    "entities that can increase or decrease (e.g., reject 'Cats', accept "
    "'Cat Population'). If a student proposes a causal link, explicitly force "
    "them to define the polarity (+/-) and ask if there is a delay.\n\n"
    "RULE 1 - POLARITY DEFINITIONS (UNBREAKABLE):\n"
    "To determine polarity, ask: if the SOURCE variable INCREASES, does the "
    "TARGET variable increase or decrease? ALWAYS reframe the relationship in "
    "the INCREASING direction before assigning polarity. Never assign polarity "
    "based on the direction of change the student described — only based on "
    "what would happen if the source increased.\n"
    "Positive Polarity (+): If source INCREASES, target INCREASES.\n"
    "Negative Polarity (-): If source INCREASES, target DECREASES.\n"
    "CRITICAL EXAMPLES:\n"
    "- 'Wasp Population decreases -> Caterpillar Population increases': "
    "Reframe: if Wasp Population INCREASES, Caterpillar Population DECREASES. "
    "Opposite directions = NEGATIVE (-).\n"
    "- 'DDT increases -> Mosquito Population decreases': "
    "If DDT INCREASES, Mosquitoes DECREASE. Opposite = NEGATIVE (-).\n"
    "- 'Cat Population increases -> Rat Population decreases': "
    "If Cats INCREASE, Rats DECREASE. Opposite = NEGATIVE (-).\n"
    "- 'Rat Population increases -> Plague Incidence increases': "
    "If Rats INCREASE, Plague INCREASES. Same direction = POSITIVE (+).\n"
    "NEVER assign (+) just because both variables change in the same "
    "described direction (e.g. both decrease). Always reframe to the "
    "increasing direction first.\n\n"
    "RULE 2 - MULTI-EXTRACTION:\n"
    "If the student's input contains multiple valid pieces of information "
    "(e.g., they name two variables, the causal direction, and the polarity "
    "all in one sentence), you MUST extract ALL of them at once. Do not act "
    "like a rigid state machine that only processes one item per turn. "
    "Acknowledge everything they got right in a single response and move the "
    "graph forward immediately. Populate extracted_variables and "
    "extracted_links simultaneously when appropriate.\n\n"
    "RULE 3 - FEEDBACK LOOPS:\n"
    "When the student has identified a closed cycle of causal links, help "
    "them recognise whether it forms a Reinforcing (R) or Balancing (B) "
    "feedback loop. A loop with an even number of negative (-) links is "
    "reinforcing; an odd number is balancing.\n\n"
    "RULE 4 - DELAY NOTATION:\n"
    "The // symbol on an arrow means a significant time delay exists in the "
    "causal effect. Ask the student about delays when relevant (e.g., DDT "
    "bioaccumulation takes time, population changes are not instantaneous).\n\n"
    "Base all evaluations exclusively on the Borneo case study text."
)

CASE_STUDY = (
    "In the 1950s, the WHO sprayed copious amounts of DDT in Borneo to kill "
    "malaria-carrying mosquitoes. The DDT killed the mosquitoes, but also "
    "killed a parasitic wasp that controlled thatch-eating caterpillars, "
    "causing villagers' roofs to collapse. Furthermore, DDT bioaccumulated "
    "in local insects. Geckos ate the insects, and cats ate the geckos. The "
    "concentrated DDT killed the cats. With the cats gone, the rat population "
    "exploded, causing plague and destroying grain stores. The WHO eventually "
    "had to parachute live cats into Borneo to stabilize the situation."
)
