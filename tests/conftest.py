"""Shared fixtures for the Socratic ST/SD Tutor test suite."""

import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path so `import models` etc. work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import CausalLink


# ── Reference CLD (answer key — NOT shown to student or LLM) ────────────────

REFERENCE_VARIABLES = [
    "DDT Spraying Level",
    "Mosquito Population",
    "Malaria Incidence",
    "Parasitic Wasp Population",
    "Thatch-Eating Caterpillar Population",
    "Roof Structural Integrity",
    "DDT Concentration in Insects",
    "Gecko Population",
    "DDT Concentration in Geckos",
    "Cat Population",
    "DDT Concentration in Cats",
    "Rat Population",
    "Plague Incidence",
    "Grain Store Level",
    "Cat Parachute Drops",
]

REFERENCE_LINKS = [
    CausalLink(source="DDT Spraying Level", target="Mosquito Population", polarity="-", has_delay=False),
    CausalLink(source="DDT Spraying Level", target="Parasitic Wasp Population", polarity="-", has_delay=False),
    CausalLink(source="DDT Spraying Level", target="DDT Concentration in Insects", polarity="+", has_delay=True),
    CausalLink(source="Mosquito Population", target="Malaria Incidence", polarity="+", has_delay=True),
    CausalLink(source="Parasitic Wasp Population", target="Thatch-Eating Caterpillar Population", polarity="-", has_delay=False),
    CausalLink(source="Thatch-Eating Caterpillar Population", target="Roof Structural Integrity", polarity="-", has_delay=True),
    CausalLink(source="DDT Concentration in Insects", target="Gecko Population", polarity="-", has_delay=True),
    CausalLink(source="DDT Concentration in Insects", target="DDT Concentration in Geckos", polarity="+", has_delay=True),
    CausalLink(source="DDT Concentration in Geckos", target="Cat Population", polarity="-", has_delay=True),
    CausalLink(source="Cat Population", target="Rat Population", polarity="-", has_delay=False),
    CausalLink(source="Rat Population", target="Plague Incidence", polarity="+", has_delay=True),
    CausalLink(source="Rat Population", target="Grain Store Level", polarity="-", has_delay=False),
    CausalLink(source="Cat Parachute Drops", target="Cat Population", polarity="+", has_delay=False),
]


@pytest.fixture
def sample_variables():
    return ["Mosquito Population", "DDT Spraying Level", "Cat Population"]


@pytest.fixture
def sample_links():
    return [
        {"source": "DDT Spraying Level", "target": "Mosquito Population", "polarity": "-", "has_delay": False},
    ]
