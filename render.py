"""Graphviz CLD renderer for the Socratic ST/SD Tutor."""

from typing import Sequence

import graphviz

from models import CausalLink, FeedbackLoop


def render_cld(
    variables: Sequence[str],
    links: Sequence[CausalLink | dict],
    loops: Sequence[FeedbackLoop | dict] | None = None,
) -> graphviz.Digraph:
    """Build a Causal Loop Diagram from approved variables, links, and loops.

    Args:
        variables: List of approved system variable names (nodes).
        links: List of CausalLink objects or dicts.
        loops: List of FeedbackLoop objects or dicts.

    Returns:
        A graphviz.Digraph ready for rendering.
    """
    dot = graphviz.Digraph(
        "CLD",
        format="svg",
        graph_attr={
            "rankdir": "LR",
            "bgcolor": "transparent",
            "fontname": "Helvetica",
            "pad": "0.5",
            "nodesep": "0.8",
            "ranksep": "1.0",
        },
        node_attr={
            "shape": "box",
            "style": "rounded,filled",
            "fillcolor": "#f0f4ff",
            "fontname": "Helvetica",
            "fontsize": "11",
            "color": "#4a6fa5",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "10",
        },
    )

    if not variables:
        dot.node(
            "empty",
            "No variables yet \u2014 start chatting!",
            shape="plaintext",
            fontcolor="#888888",
            fontsize="13",
        )
        return dot

    for var in variables:
        dot.node(var, var)

    for link in links:
        if isinstance(link, dict):
            link = CausalLink(**link)

        polarity = link.polarity

        # Build the headlabel: polarity sign placed at the arrowhead
        headlabel = f" {polarity} "
        if link.has_delay:
            headlabel += "// "

        if polarity == "+":
            color = "#16a34a"  # green
            style = "solid"
        else:
            color = "#dc2626"  # red
            style = "dashed"

        dot.edge(
            link.source,
            link.target,
            headlabel=headlabel,
            labeldistance="2.5",
            color=color,
            style=style,
            fontcolor=color,
            penwidth="1.5",
            arrowsize="0.9",
        )

    return dot
