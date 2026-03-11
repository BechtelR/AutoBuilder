"""Tests for state helpers, callback composition, and NullSkillLibrary."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agents.protocols import (
    NullSkillLibrary,
    SkillEntry,
    SkillMatchContext,
)
from app.agents.state_helpers import (
    compose_callbacks,
    context_from_state,
)


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
