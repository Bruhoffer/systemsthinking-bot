"""Tests for the Graphviz CLD renderer."""

from models import CausalLink, FeedbackLoop
from render import render_cld


class TestRenderCLD:
    def test_empty_graph_shows_placeholder(self):
        dot = render_cld([], [])
        source = dot.source
        assert "No variables yet" in source

    def test_nodes_rendered(self, sample_variables):
        dot = render_cld(sample_variables, [])
        source = dot.source
        for var in sample_variables:
            assert var in source

    def test_positive_edge_blue_solid(self):
        variables = ["A", "B"]
        links = [CausalLink(source="A", target="B", polarity="+", has_delay=False)]
        dot = render_cld(variables, links)
        source = dot.source
        assert "#2563eb" in source  # blue
        assert "solid" in source

    def test_negative_edge_red_dashed(self):
        variables = ["A", "B"]
        links = [CausalLink(source="A", target="B", polarity="-", has_delay=False)]
        dot = render_cld(variables, links)
        source = dot.source
        assert "#dc2626" in source  # red
        assert "dashed" in source

    def test_delay_marker_appended(self):
        variables = ["A", "B"]
        links = [CausalLink(source="A", target="B", polarity="+", has_delay=True)]
        dot = render_cld(variables, links)
        source = dot.source
        assert "//" in source

    def test_no_delay_marker_when_false(self):
        variables = ["A", "B"]
        links = [CausalLink(source="A", target="B", polarity="+", has_delay=False)]
        dot = render_cld(variables, links)
        source = dot.source
        assert "//" not in source

    def test_accepts_dict_links(self, sample_links):
        variables = ["DDT Spraying Level", "Mosquito Population"]
        dot = render_cld(variables, sample_links)
        source = dot.source
        assert "DDT Spraying Level" in source
        assert "Mosquito Population" in source

    def test_polarity_at_arrowhead_via_headlabel(self):
        variables = ["A", "B"]
        links = [CausalLink(source="A", target="B", polarity="+", has_delay=False)]
        dot = render_cld(variables, links)
        source = dot.source
        assert "headlabel" in source

    def test_reinforcing_loop_rendered(self):
        variables = ["A", "B"]
        links = [
            {"source": "A", "target": "B", "polarity": "+", "has_delay": False},
            {"source": "B", "target": "A", "polarity": "+", "has_delay": False},
        ]
        loops = [
            FeedbackLoop(
                name="R1", loop_type="reinforcing", variable_sequence=["A", "B"]
            )
        ]
        dot = render_cld(variables, links, loops)
        source = dot.source
        assert "R1" in source
        assert "#2563eb" in source  # reinforcing uses blue

    def test_balancing_loop_rendered(self):
        variables = ["A", "B"]
        links = [
            {"source": "A", "target": "B", "polarity": "+", "has_delay": False},
            {"source": "B", "target": "A", "polarity": "-", "has_delay": False},
        ]
        loops = [
            FeedbackLoop(
                name="B1", loop_type="balancing", variable_sequence=["A", "B"]
            )
        ]
        dot = render_cld(variables, links, loops)
        source = dot.source
        assert "B1" in source
        assert "#dc2626" in source  # balancing uses red
