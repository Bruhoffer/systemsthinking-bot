"""Application-level guardrails for graph state validation."""

from models import CausalLink, FeedbackLoop, TutorResponse


def is_duplicate_variable(new_var: str, existing_vars: list[str]) -> bool:
    """Check if a variable already exists (case-insensitive)."""
    return new_var.strip().lower() in {v.lower() for v in existing_vars}


def validate_link(
    link: CausalLink, existing_vars: list[str]
) -> tuple[bool, str | None]:
    """Validate that both source and target exist in approved variables."""
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

    # Process links (source/target must exist in variables)
    for link in response.extracted_links:
        is_valid, error_msg = validate_link(link, variables)
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
            loops.append(loop.model_dump())

    return errors
