"""Tests for Director formation logic."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.agents.formation import (
    EVOLUTION_INSTRUCTION,
    FORMATION_INSTRUCTION,
    ensure_formation_state,
    reset_formation,
    write_artifact,
)
from app.models.constants import (
    APP_NAME,
    CEO_PROFILE_KEY,
    DIRECTOR_IDENTITY_KEY,
    FORMATION_STATUS_KEY,
    OPERATING_CONTRACT_KEY,
)
from app.models.enums import FormationStatus


@dataclass
class FakeSession:
    """Minimal session-like object with mutable state dict."""

    state: dict[str, object] = field(default_factory=lambda: dict[str, object]())


class FakeSessionService:
    """Dict-backed session service for testing."""

    def __init__(self) -> None:
        self._sessions: dict[str, FakeSession] = {}

    def _key(self, app_name: str, user_id: str, session_id: str) -> str:
        return f"{app_name}:{user_id}:{session_id}"

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> FakeSession | None:
        return self._sessions.get(self._key(app_name, user_id, session_id))

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        state: dict[str, object] | None = None,
    ) -> FakeSession:
        session = FakeSession(state=dict(state) if state else {})
        self._sessions[self._key(app_name, user_id, session_id)] = session
        return session

    async def delete_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> None:
        self._sessions.pop(self._key(app_name, user_id, session_id), None)


# --- Constant tests ---


class TestFormationConstants:
    def test_formation_instruction_not_empty(self) -> None:
        assert isinstance(FORMATION_INSTRUCTION, str)
        assert len(FORMATION_INSTRUCTION) > 0

    def test_evolution_instruction_not_empty(self) -> None:
        assert isinstance(EVOLUTION_INSTRUCTION, str)
        assert len(EVOLUTION_INSTRUCTION) > 0

    def test_formation_status_enum_values(self) -> None:
        assert FormationStatus.PENDING == "PENDING"
        assert FormationStatus.IN_PROGRESS == "IN_PROGRESS"
        assert FormationStatus.COMPLETE == "COMPLETE"


# --- ensure_formation_state ---


class TestEnsureFormationState:
    @pytest.mark.asyncio
    async def test_creates_pending_when_missing(self) -> None:
        svc = FakeSessionService()
        status = await ensure_formation_state(svc, "user1", APP_NAME)
        assert status == FormationStatus.PENDING

    @pytest.mark.asyncio
    async def test_returns_existing_status(self) -> None:
        svc = FakeSessionService()
        await svc.create_session(
            app_name=APP_NAME,
            user_id="user1",
            session_id="settings_user1",
            state={FORMATION_STATUS_KEY: FormationStatus.COMPLETE},
        )
        status = await ensure_formation_state(svc, "user1", APP_NAME)
        assert status == FormationStatus.COMPLETE


# --- write_artifact ---


class TestWriteArtifact:
    @pytest.mark.asyncio
    async def test_single_artifact_does_not_complete(self) -> None:
        svc = FakeSessionService()
        # Pre-create session
        await svc.create_session(
            app_name=APP_NAME,
            user_id="user1",
            session_id="settings_user1",
            state={FORMATION_STATUS_KEY: FormationStatus.IN_PROGRESS},
        )
        await write_artifact(svc, "user1", APP_NAME, DIRECTOR_IDENTITY_KEY, "friendly")
        session = await svc.get_session(
            app_name=APP_NAME,
            user_id="user1",
            session_id="settings_user1",
        )
        assert session is not None
        assert session.state.get(FORMATION_STATUS_KEY) != FormationStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_all_three_artifacts_completes(self) -> None:
        svc = FakeSessionService()
        await svc.create_session(
            app_name=APP_NAME,
            user_id="user1",
            session_id="settings_user1",
            state={FORMATION_STATUS_KEY: FormationStatus.IN_PROGRESS},
        )
        await write_artifact(svc, "user1", APP_NAME, DIRECTOR_IDENTITY_KEY, "friendly AI")
        await write_artifact(svc, "user1", APP_NAME, CEO_PROFILE_KEY, "hands-off leader")
        await write_artifact(svc, "user1", APP_NAME, OPERATING_CONTRACT_KEY, "high autonomy")
        session = await svc.get_session(
            app_name=APP_NAME,
            user_id="user1",
            session_id="settings_user1",
        )
        assert session is not None
        assert session.state[FORMATION_STATUS_KEY] == FormationStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_invalid_key_raises(self) -> None:
        svc = FakeSessionService()
        with pytest.raises(ValueError, match="Invalid artifact key"):
            await write_artifact(svc, "user1", APP_NAME, "bad:key", "value")


# --- reset_formation ---


class TestResetFormation:
    @pytest.mark.asyncio
    async def test_clears_all(self) -> None:
        svc = FakeSessionService()
        await svc.create_session(
            app_name=APP_NAME,
            user_id="user1",
            session_id="settings_user1",
            state={
                FORMATION_STATUS_KEY: FormationStatus.COMPLETE,
                DIRECTOR_IDENTITY_KEY: "friendly AI",
                CEO_PROFILE_KEY: "hands-off leader",
                OPERATING_CONTRACT_KEY: "high autonomy",
            },
        )
        await reset_formation(svc, "user1", APP_NAME)
        session = await svc.get_session(
            app_name=APP_NAME,
            user_id="user1",
            session_id="settings_user1",
        )
        assert session is not None
        assert session.state[FORMATION_STATUS_KEY] == FormationStatus.PENDING
        assert session.state[DIRECTOR_IDENTITY_KEY] == ""
        assert session.state[CEO_PROFILE_KEY] == ""
        assert session.state[OPERATING_CONTRACT_KEY] == ""
