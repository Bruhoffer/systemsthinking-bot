"""Application-level guardrails for graph state validation."""

from models import CausalLink, FeedbackLoop, TutorResponse

# Canonical loop names keyed by the minimum set of variables that uniquely
# identify each loop (case-insensitive). First match wins.
_CANONICAL_LOOPS: list[tuple[str, str, set[str]]] = [
    ("B1", "balancing", {
        "malaria incidence", "ddt spraying level", "mosquito population",
    }),
    ("B2", "balancing", {
        "parasitic wasp population", "thatch-eating caterpillar population",
    }),
    ("B3", "balancing", {
        "ddt accumulated insects", "ddt accumulated geckos",
    }),
    # B5 must come before B4 — it is a superset of B4's vars plus grain shortages
    ("B5", "balancing", {
        "cat population", "rat population", "grain shortages", "cat parachute drops",
    }),
    ("B4", "balancing", {
        "cat population", "rat population",
    }),
    ("R1", "reinforcing", {
        "ddt accumulated geckos", "cat population",
    }),
]


def _canonical_loop_name(loop: FeedbackLoop, existing_loops: list[dict]) -> str:
    """Return the canonical label (B1–B5, R1) for a loop, or next available Bx/Rx."""
    used_names = {l.get("name", "").upper() for l in existing_loops}
    seq_set = {v.lower() for v in loop.variable_sequence}

    for name, _, key_vars in _CANONICAL_LOOPS:
        if name in used_names:
            continue
        if key_vars.issubset(seq_set):
            return name

    # Fallback: next available label
    prefix = "R" if loop.loop_type == "reinforcing" else "B"
    n = 1
    while f"{prefix}{n}" in used_names:
        n += 1
    return f"{prefix}{n}"


def is_duplicate_variable(new_var: str, existing_vars: list[str]) -> bool:
    """Check if a variable already exists (case-insensitive)."""
    return new_var.strip().lower() in {v.lower() for v in existing_vars}


def is_duplicate_link(link: CausalLink, existing_links: list[dict]) -> bool:
    """Check if an identical (source, target) pair already exists (case-insensitive)."""
    src = link.source.strip().lower()
    tgt = link.target.strip().lower()
    return any(
        l.get("source", "").lower() == src and l.get("target", "").lower() == tgt
        for l in existing_links
    )


def validate_link(
    link: CausalLink, existing_vars: list[str], existing_links: list[dict]
) -> tuple[bool, str | None]:
    """Validate that both source and target exist and the link is not a duplicate."""
    var_set = {v.lower() for v in existing_vars}
    missing = []

    if link.source.lower() not in var_set:
        missing.append(link.source)
    if link.target.lower() not in var_set:
        missing.append(link.target)

    if missing:
        return False, (
            f"Error: Attempted to link undefined variable(s): "
            f"{', '.join(missing)}. Prompt the student to define them first."
        )

    if is_duplicate_link(link, existing_links):
        return False, (
            f"Error: Link from '{link.source}' to '{link.target}' already exists. "
            "Do not re-draw it. Acknowledge it and continue."
        )

    return True, None


def validate_loop(
    loop: FeedbackLoop,
    existing_vars: list[str],
    existing_links: list[dict],
    existing_loops: list[dict],
) -> tuple[bool, str | None]:
    """Validate that a feedback loop references only approved variables and links."""
    if any(l.get("name", "").lower() == loop.name.lower() for l in existing_loops):
        return False, f"Error: Loop '{loop.name}' already exists."

    var_set = {v.lower() for v in existing_vars}
    missing = [v for v in loop.variable_sequence if v.lower() not in var_set]
    if missing:
        return False, (
            f"Error: Loop references undefined variable(s): "
            f"{', '.join(missing)}. They must be approved first."
        )

    link_set = {(l["source"].lower(), l["target"].lower()) for l in existing_links}
    seq = loop.variable_sequence
    for i in range(len(seq)):
        src = seq[i].lower()
        tgt = seq[(i + 1) % len(seq)].lower()
        if (src, tgt) not in link_set:
            return False, (
                f"Error: No approved link from '{seq[i]}' to "
                f"'{seq[(i + 1) % len(seq)]}'. All links in the loop must "
                "be approved first."
            )

    return True, None


def apply_tutor_response(
    response: TutorResponse,
    variables: list[str],
    links: list[dict],
    loops: list[dict] | None = None,
) -> list[str]:
    """Apply a validated TutorResponse to the graph state.

    Processes extracted_variables, extracted_links, and extracted_loops
    from the list-based schema. Mutates state in-place.

    Returns:
        A list of error messages (empty if all extractions succeeded).
    """
    if loops is None:
        loops = []
    errors: list[str] = []

    # Process variables first (links may depend on them)
    for var in response.extracted_variables:
        if is_duplicate_variable(var, variables):
            errors.append(
                f"Error: Variable '{var}' already exists. "
                "Acknowledge the duplicate and move on."
            )
        else:
            variables.append(var.strip())

    # Process links (source/target must exist in variables; no duplicates)
    for link in response.extracted_links:
        is_valid, error_msg = validate_link(link, variables, links)
        if not is_valid:
            errors.append(error_msg)
        else:
            links.append(link.model_dump())

    # Process loops
    for loop in response.extracted_loops:
        # Normalise loop_type to lowercase (LLM sometimes returns "Balancing")
        loop = loop.model_copy(update={"loop_type": loop.loop_type.lower()})

        # Strip closing duplicate: LLM often ends the sequence with the first
        # variable again (e.g. [A, B, C, A]). Remove it before validating.
        seq = loop.variable_sequence
        if len(seq) > 1 and seq[-1].lower() == seq[0].lower():
            loop = loop.model_copy(update={"variable_sequence": seq[:-1]})

        is_valid, error_msg = validate_loop(loop, variables, links, loops)
        if not is_valid:
            errors.append(error_msg)
        else:
            canonical_name = _canonical_loop_name(loop, loops)
            loop = loop.model_copy(update={"name": canonical_name})
            loops.append(loop.model_dump())

    return errors
