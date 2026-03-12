"""Tests for state helpers, callback composition, and NullSkillLibrary."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agents.protocols import NullSkillLibrary, SkillMatchContext
from app.agents.state_helpers import (
    compose_callbacks,
    context_from_state,
    create_system_reminder_callback,
)
from app.skills.library import SkillEntry


class TestContextFromState:
    def test_context_from_state_required_present(self) -> None:
        state: dict[str, object] = {"name": "alice", "count": 42}
        result = context_from_state(state, "name", str)
        assert result == "alice"

    def test_context_from_state_required_missing_raises(self) -> None:
        state: dict[str, object] = {"other": "value"}
        with pytest.raises(ValueError, match="Required state key 'missing'"):
            context_from_state(state, "missing", str)

    def test_context_from_state_optional_missing_returns_default(self) -> None:
        state: dict[str, object] = {}
        result = context_from_state(state, "key", str, required=False, default="fallback")
        assert result == "fallback"

    def test_context_from_state_type_mismatch_raises(self) -> None:
        state: dict[str, object] = {"key": 123}
        with pytest.raises(ValueError, match="expected type str, got int"):
            context_from_state(state, "key", str)


class TestComposeCallbacks:
    def test_compose_callbacks_first_non_none_wins(self) -> None:
        sentinel = MagicMock()
        cb1 = MagicMock(return_value=None)
        cb2 = MagicMock(return_value=sentinel)
        cb3 = MagicMock(return_value=MagicMock())

        composed = compose_callbacks(cb1, cb2, cb3)

        ctx = MagicMock()
        req = MagicMock()
        result = composed(ctx, req)

        assert result is sentinel
        cb1.assert_called_once_with(ctx, req)
        cb2.assert_called_once_with(ctx, req)
        cb3.assert_not_called()

    def test_compose_callbacks_all_none_returns_none(self) -> None:
        cb1 = MagicMock(return_value=None)
        cb2 = MagicMock(return_value=None)

        composed = compose_callbacks(cb1, cb2)

        ctx = MagicMock()
        req = MagicMock()
        result = composed(ctx, req)

        assert result is None
        cb1.assert_called_once()
        cb2.assert_called_once()


class TestNullSkillLibrary:
    def test_null_skill_library_returns_empty(self) -> None:
        lib = NullSkillLibrary()
        ctx = SkillMatchContext(deliverable_type="api", tags=["python"])
        entries = lib.match(ctx)
        assert entries == []

        entry = SkillEntry(name="test_skill", description="A skill")
        content = lib.load(entry)
        assert content.entry is entry
        assert content.content == ""


class TestSystemReminderCallback:
    def _make_ctx(self, state: dict[str, object]) -> MagicMock:
        ctx = MagicMock()
        ctx.state = state
        return ctx

    def test_no_budget_returns_none(self) -> None:
        cb = create_system_reminder_callback()
        ctx = self._make_ctx({})
        req = MagicMock()
        result = cb(ctx, req)
        assert result is None
        # No budget data -> empty reminders
        assert ctx.state["_system_reminders"] == ""

    def test_low_budget_no_warning(self) -> None:
        cb = create_system_reminder_callback()
        ctx = self._make_ctx({"context_budget_used_pct": 30.0})
        req = MagicMock()
        result = cb(ctx, req)
        assert result is None
        assert ctx.state["_system_reminders"] == ""

    def test_high_budget_injects(self) -> None:
        cb = create_system_reminder_callback()
        ctx = self._make_ctx({"context_budget_used_pct": 73.0})
        req = MagicMock()
        result = cb(ctx, req)
        assert result is None
        assert "73%" in ctx.state["_system_reminders"]

    def test_clears_when_no_reminders(self) -> None:
        cb = create_system_reminder_callback()
        # First call with high budget
        ctx1 = self._make_ctx({"context_budget_used_pct": 80.0})
        cb(ctx1, MagicMock())
        assert ctx1.state["_system_reminders"] != ""

        # Second call with no budget
        ctx2 = self._make_ctx({})
        cb(ctx2, MagicMock())
        assert ctx2.state["_system_reminders"] == ""


class TestSkillMatchContext:
    def test_skill_match_context_creation(self) -> None:
        ctx = SkillMatchContext(
            deliverable_type="api",
            file_patterns=["*.py"],
            tags=["python", "fastapi"],
            agent_role="coder",
        )
        assert ctx.deliverable_type == "api"
        assert ctx.file_patterns == ["*.py"]
        assert ctx.tags == ["python", "fastapi"]
        assert ctx.agent_role == "coder"

    def test_skill_match_context_defaults(self) -> None:
        ctx = SkillMatchContext()
        assert ctx.deliverable_type is None
        assert ctx.file_patterns == []
        assert ctx.tags == []
        assert ctx.agent_role is None
