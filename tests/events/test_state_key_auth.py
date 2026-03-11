"""Tests for state key authorization (Phase 5b)."""

from app.events.publisher import determine_agent_tier, validate_state_delta
from app.models.enums import AgentTier


class TestDetermineAgentTier:
    def test_director(self) -> None:
        assert determine_agent_tier("director") == AgentTier.DIRECTOR
        assert determine_agent_tier("Director") == AgentTier.DIRECTOR
        assert determine_agent_tier("DIRECTOR") == AgentTier.DIRECTOR

    def test_pm(self) -> None:
        assert determine_agent_tier("pm_project1") == AgentTier.PM
        assert determine_agent_tier("PM_test") == AgentTier.PM
        assert determine_agent_tier("pm") == AgentTier.PM

    def test_worker(self) -> None:
        assert determine_agent_tier("coder") == AgentTier.WORKER
        assert determine_agent_tier("planner") == AgentTier.WORKER
        assert determine_agent_tier("reviewer") == AgentTier.WORKER


class TestValidateStateDelta:
    def test_director_writes_all(self) -> None:
        delta: dict[str, object] = {
            "director:governance_override": True,
            "pm:batch_position": 1,
            "worker:progress": 50,
            "user:prefs": "dark",
            "app:config": "val",
            "no_prefix_key": "value",
        }
        result = validate_state_delta(delta, AgentTier.DIRECTOR)
        assert result == []

    def test_pm_blocked_from_director(self) -> None:
        delta: dict[str, object] = {
            "director:governance_override": True,
            "pm:batch_position": 1,
        }
        result = validate_state_delta(delta, AgentTier.PM)
        assert result == ["director:governance_override"]

    def test_worker_blocked_from_director_and_pm(self) -> None:
        delta: dict[str, object] = {
            "director:governance_override": True,
            "pm:batch_position": 1,
            "app:config": "val",
            "worker:progress": 50,
        }
        result = validate_state_delta(delta, AgentTier.WORKER)
        assert "director:governance_override" in result
        assert "pm:batch_position" in result
        assert "app:config" in result
        assert "worker:progress" not in result

    def test_nonprefixed_allowed_for_all(self) -> None:
        delta: dict[str, object] = {"some_key": "value", "batch_result": "done"}
        assert validate_state_delta(delta, AgentTier.DIRECTOR) == []
        assert validate_state_delta(delta, AgentTier.PM) == []
        assert validate_state_delta(delta, AgentTier.WORKER) == []

    def test_user_and_temp_allowed_for_all(self) -> None:
        delta: dict[str, object] = {
            "user:formation_status": "COMPLETE",
            "temp:scratch": "data",
        }
        assert validate_state_delta(delta, AgentTier.DIRECTOR) == []
        assert validate_state_delta(delta, AgentTier.PM) == []
        assert validate_state_delta(delta, AgentTier.WORKER) == []

    def test_returns_all_unauthorized(self) -> None:
        delta: dict[str, object] = {
            "director:key1": "a",
            "director:key2": "b",
            "pm:key3": "c",
        }
        result = validate_state_delta(delta, AgentTier.WORKER)
        assert len(result) == 3
        assert "director:key1" in result
        assert "director:key2" in result
        assert "pm:key3" in result

    def test_empty_returns_empty(self) -> None:
        assert validate_state_delta({}, AgentTier.DIRECTOR) == []
        assert validate_state_delta({}, AgentTier.PM) == []
        assert validate_state_delta({}, AgentTier.WORKER) == []
