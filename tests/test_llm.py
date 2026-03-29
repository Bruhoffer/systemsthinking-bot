"""Tests for LLM orchestration (mocked — no real API calls)."""

from unittest.mock import MagicMock, patch

from models import TutorResponse
from llm import _build_messages


class TestBuildMessages:
    def test_includes_system_prompt(self):
        msgs = _build_messages([], [], [])
        system_msgs = [m for m in msgs if m["role"] == "system"]
        assert len(system_msgs) >= 1
        assert "ST/SD tutor" in system_msgs[0]["content"]

    def test_includes_case_study(self):
        msgs = _build_messages([], [], [])
        combined = " ".join(m["content"] for m in msgs)
        assert "Borneo" in combined

    def test_includes_graph_state(self):
        msgs = _build_messages([], ["Cat Population"], [])
        combined = " ".join(m["content"] for m in msgs)
        assert "Cat Population" in combined

    def test_includes_guardrail_error(self):
        msgs = _build_messages([], [], [], guardrail_error="Error: test error")
        combined = " ".join(m["content"] for m in msgs)
        assert "Error: test error" in combined

    def test_trims_long_history(self):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(100)]
        msgs = _build_messages(history, [], [])
        user_msgs = [m for m in msgs if m["role"] == "user"]
        assert len(user_msgs) <= 40

    def test_chat_history_appended_after_system(self):
        history = [{"role": "user", "content": "hello"}]
        msgs = _build_messages(history, [], [])
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "hello"
