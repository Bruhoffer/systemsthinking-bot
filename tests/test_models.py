"""Tests for Pydantic schemas."""

from models import CausalLink, FeedbackLoop, TutorResponse


class TestCausalLink:
    def test_valid_link(self):
        link = CausalLink(
            source="DDT Spraying Level",
            target="Mosquito Population",
            polarity="-",
            has_delay=False,
        )
        assert link.source == "DDT Spraying Level"
        assert link.polarity == "-"
        assert link.has_delay is False

    def test_link_with_delay(self):
        link = CausalLink(
            source="A", target="B", polarity="+", has_delay=True
        )
        assert link.has_delay is True


class TestFeedbackLoop:
    def test_valid_loop(self):
        loop = FeedbackLoop(
            name="R1",
            loop_type="reinforcing",
            variable_sequence=["A", "B"],
        )
        assert loop.name == "R1"
        assert loop.loop_type == "reinforcing"
        assert loop.variable_sequence == ["A", "B"]


class TestTutorResponse:
    def test_minimal_response_defaults_to_empty_lists(self):
        resp = TutorResponse(
            student_state_analysis="Student is exploring events.",
            message_to_student="What happened first?",
        )
        assert resp.extracted_variables == []
        assert resp.extracted_links == []
        assert resp.extracted_loops == []

    def test_multi_extraction_variables(self):
        resp = TutorResponse(
            student_state_analysis="Two valid variables.",
            message_to_student="Great, both added!",
            extracted_variables=["Mosquito Population", "DDT Spraying Level"],
        )
        assert len(resp.extracted_variables) == 2

    def test_multi_extraction_variable_and_link(self):
        resp = TutorResponse(
            student_state_analysis="Variable + link in one turn.",
            message_to_student="Added variable and link!",
            extracted_variables=["Cat Population"],
            extracted_links=[
                CausalLink(
                    source="Rat Population",
                    target="Cat Population",
                    polarity="-",
                    has_delay=False,
                )
            ],
        )
        assert len(resp.extracted_variables) == 1
        assert len(resp.extracted_links) == 1
        assert resp.extracted_links[0].polarity == "-"

    def test_multi_extraction_with_loop(self):
        resp = TutorResponse(
            student_state_analysis="Loop identified.",
            message_to_student="Loop added!",
            extracted_loops=[
                FeedbackLoop(
                    name="B1",
                    loop_type="balancing",
                    variable_sequence=["A", "B"],
                )
            ],
        )
        assert len(resp.extracted_loops) == 1
        assert resp.extracted_loops[0].loop_type == "balancing"
