"""Tests for application-level guardrails."""

from models import CausalLink, FeedbackLoop, TutorResponse
from guardrails import (
    is_duplicate_variable,
    validate_link,
    validate_loop,
    apply_tutor_response,
)


class TestIsDuplicateVariable:
    def test_exact_match(self):
        assert is_duplicate_variable("Cat Population", ["Cat Population"]) is True

    def test_case_insensitive(self):
        assert is_duplicate_variable("cat population", ["Cat Population"]) is True

    def test_no_match(self):
        assert is_duplicate_variable("Rat Population", ["Cat Population"]) is False

    def test_whitespace_stripped(self):
        assert is_duplicate_variable("  Cat Population  ", ["Cat Population"]) is True

    def test_empty_list(self):
        assert is_duplicate_variable("Anything", []) is False


class TestValidateLink:
    def test_valid_link(self, sample_variables):
        link = CausalLink(
            source="DDT Spraying Level",
            target="Mosquito Population",
            polarity="-",
            has_delay=False,
        )
        is_valid, error = validate_link(link, sample_variables)
        assert is_valid is True
        assert error is None

    def test_missing_source(self, sample_variables):
        link = CausalLink(
            source="Nonexistent",
            target="Mosquito Population",
            polarity="+",
            has_delay=False,
        )
        is_valid, error = validate_link(link, sample_variables)
        assert is_valid is False
        assert "Nonexistent" in error

    def test_missing_target(self, sample_variables):
        link = CausalLink(
            source="Cat Population",
            target="Nonexistent",
            polarity="-",
            has_delay=False,
        )
        is_valid, error = validate_link(link, sample_variables)
        assert is_valid is False
        assert "Nonexistent" in error

    def test_both_missing(self):
        link = CausalLink(source="A", target="B", polarity="+", has_delay=False)
        is_valid, error = validate_link(link, [])
        assert is_valid is False
        assert "A" in error
        assert "B" in error


class TestValidateLoop:
    def test_valid_loop(self):
        variables = ["A", "B"]
        links = [
            {"source": "A", "target": "B", "polarity": "+", "has_delay": False},
            {"source": "B", "target": "A", "polarity": "+", "has_delay": False},
        ]
        loop = FeedbackLoop(
            name="R1", loop_type="reinforcing", variable_sequence=["A", "B"]
        )
        is_valid, error = validate_loop(loop, variables, links, [])
        assert is_valid is True
        assert error is None

    def test_duplicate_loop_name(self):
        loop = FeedbackLoop(
            name="R1", loop_type="reinforcing", variable_sequence=["A", "B"]
        )
        existing_loops = [{"name": "R1", "loop_type": "reinforcing", "variable_sequence": ["A", "B"]}]
        is_valid, error = validate_loop(loop, ["A", "B"], [], existing_loops)
        assert is_valid is False
        assert "already exists" in error

    def test_undefined_variable_in_loop(self):
        loop = FeedbackLoop(
            name="R1", loop_type="reinforcing", variable_sequence=["A", "Z"]
        )
        is_valid, error = validate_loop(loop, ["A"], [], [])
        assert is_valid is False
        assert "Z" in error

    def test_missing_link_in_loop(self):
        variables = ["A", "B"]
        links = [
            {"source": "A", "target": "B", "polarity": "+", "has_delay": False},
        ]
        loop = FeedbackLoop(
            name="R1", loop_type="reinforcing", variable_sequence=["A", "B"]
        )
        is_valid, error = validate_loop(loop, variables, links, [])
        assert is_valid is False
        assert "No approved link" in error


class TestApplyTutorResponse:
    def test_single_variable_extracted(self):
        variables = []
        links = []
        resp = TutorResponse(
            student_state_analysis="ok",
            message_to_student="Added!",
            extracted_variables=["Mosquito Population"],
        )
        errors = apply_tutor_response(resp, variables, links)
        assert errors == []
        assert variables == ["Mosquito Population"]

    def test_multiple_variables_extracted(self):
        variables = []
        links = []
        resp = TutorResponse(
            student_state_analysis="ok",
            message_to_student="Both added!",
            extracted_variables=["Mosquito Population", "DDT Spraying Level"],
        )
        errors = apply_tutor_response(resp, variables, links)
        assert errors == []
        assert len(variables) == 2

    def test_duplicate_variable_rejected(self):
        variables = ["Mosquito Population"]
        links = []
        resp = TutorResponse(
            student_state_analysis="ok",
            message_to_student="Added!",
            extracted_variables=["mosquito population"],
        )
        errors = apply_tutor_response(resp, variables, links)
        assert len(errors) == 1
        assert "already exists" in errors[0]
        assert len(variables) == 1

    def test_variable_and_link_in_same_turn(self):
        variables = ["A"]
        links = []
        resp = TutorResponse(
            student_state_analysis="ok",
            message_to_student="Variable and link added!",
            extracted_variables=["B"],
            extracted_links=[
                CausalLink(source="A", target="B", polarity="+", has_delay=False)
            ],
        )
        # Variables are processed first, so B exists before the link is validated
        errors = apply_tutor_response(resp, variables, links)
        assert errors == []
        assert "B" in variables
        assert len(links) == 1

    def test_link_rejected_when_target_undefined(self):
        variables = ["A"]
        links = []
        resp = TutorResponse(
            student_state_analysis="ok",
            message_to_student="Linked!",
            extracted_links=[
                CausalLink(source="A", target="Z", polarity="-", has_delay=False)
            ],
        )
        errors = apply_tutor_response(resp, variables, links)
        assert len(errors) == 1
        assert "Z" in errors[0]
        assert len(links) == 0

    def test_loop_extracted(self):
        variables = ["A", "B"]
        links = [
            {"source": "A", "target": "B", "polarity": "+", "has_delay": False},
            {"source": "B", "target": "A", "polarity": "+", "has_delay": False},
        ]
        loops = []
        resp = TutorResponse(
            student_state_analysis="ok",
            message_to_student="Loop identified!",
            extracted_loops=[
                FeedbackLoop(
                    name="R1", loop_type="reinforcing", variable_sequence=["A", "B"]
                )
            ],
        )
        errors = apply_tutor_response(resp, variables, links, loops)
        assert errors == []
        assert len(loops) == 1

    def test_empty_extraction_returns_no_errors(self):
        resp = TutorResponse(
            student_state_analysis="ok",
            message_to_student="Tell me more.",
        )
        errors = apply_tutor_response(resp, [], [])
        assert errors == []
