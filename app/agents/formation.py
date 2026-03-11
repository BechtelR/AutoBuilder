"""Director formation logic — Settings conversation artifacts."""

from __future__ import annotations

from typing import Protocol

from app.models.constants import (
    APP_NAME,
    CEO_PROFILE_KEY,
    DIRECTOR_IDENTITY_KEY,
    FORMATION_STATUS_KEY,
    OPERATING_CONTRACT_KEY,
)
from app.models.enums import FormationStatus

_ARTIFACT_KEYS = frozenset(
    {
        DIRECTOR_IDENTITY_KEY,
        CEO_PROFILE_KEY,
        OPERATING_CONTRACT_KEY,
    }
)


class SessionServiceLike(Protocol):
    """Minimal protocol for ADK session service state access."""

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> object | None: ...

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        state: dict[str, object] | None = None,
    ) -> object: ...

    async def delete_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> None: ...


def _settings_session_id(user_id: str) -> str:
    return f"settings_{user_id}"


def _extract_state(session: object) -> dict[str, object]:
    """Extract state dict from a session object."""
    raw: object = getattr(session, "state", None)
    if isinstance(raw, dict):
        return dict(raw)  # type: ignore[arg-type]
    return {}


async def _get_or_create_state(
    session_service: SessionServiceLike,
    user_id: str,
    app_name: str,
) -> dict[str, object]:
    """Get state dict from session, creating session if needed."""
    session_id = _settings_session_id(user_id)
    session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session is not None:
        return _extract_state(session)
    # Create session with empty state
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={},
    )
    return _extract_state(session)


async def _write_state(
    session_service: SessionServiceLike,
    user_id: str,
    app_name: str,
    updates: dict[str, object],
) -> None:
    """Write state updates by deleting and recreating the session with merged state.

    ADK DatabaseSessionService does not persist in-memory dict mutations, and
    ``create_session`` raises ``AlreadyExistsError`` for duplicate IDs.
    We must delete-then-create to update state outside of agent execution.
    """
    session_id = _settings_session_id(user_id)
    existing_state: dict[str, object] = {}
    session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session is not None:
        existing_state = _extract_state(session)
        await session_service.delete_session(app_name, user_id, session_id)

    merged = {**existing_state, **updates}
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=merged,
    )


async def ensure_formation_state(
    session_service: SessionServiceLike,
    user_id: str,
    app_name: str = APP_NAME,
) -> FormationStatus:
    """Check formation status, initializing to PENDING if missing."""
    state = await _get_or_create_state(session_service, user_id, app_name)
    raw = state.get(FORMATION_STATUS_KEY)
    if isinstance(raw, str):
        try:
            return FormationStatus(raw)
        except ValueError:
            pass

    await _write_state(
        session_service,
        user_id,
        app_name,
        {FORMATION_STATUS_KEY: FormationStatus.PENDING},
    )
    return FormationStatus.PENDING


async def write_artifact(
    session_service: SessionServiceLike,
    user_id: str,
    app_name: str,
    key: str,
    value: str,
) -> None:
    """Write a formation artifact and auto-complete when all three present."""
    if key not in _ARTIFACT_KEYS:
        raise ValueError(
            f"Invalid artifact key '{key}'. Must be one of: {', '.join(sorted(_ARTIFACT_KEYS))}"
        )
    updates: dict[str, object] = {key: value}

    state = await _get_or_create_state(session_service, user_id, app_name)
    # Merge current state with the new write to check completeness
    merged = {**state, **updates}
    all_present = all(
        isinstance(merged.get(k), str) and len(merged.get(k, "")) > 0  # type: ignore[arg-type]
        for k in _ARTIFACT_KEYS
    )
    if all_present:
        updates[FORMATION_STATUS_KEY] = FormationStatus.COMPLETE

    await _write_state(session_service, user_id, app_name, updates)


async def reset_formation(
    session_service: SessionServiceLike,
    user_id: str,
    app_name: str = APP_NAME,
) -> None:
    """Clear all formation artifacts and reset status to PENDING."""
    updates: dict[str, object] = {
        DIRECTOR_IDENTITY_KEY: "",
        CEO_PROFILE_KEY: "",
        OPERATING_CONTRACT_KEY: "",
        FORMATION_STATUS_KEY: FormationStatus.PENDING,
    }
    await _write_state(session_service, user_id, app_name, updates)


FORMATION_INSTRUCTION: str = """\
You are beginning a formation conversation with the CEO. Your goal is to \
establish a productive working relationship through ~5-10 professional but \
warm questions.

You will shape three artifacts through this conversation:

1. **Director Identity** — Your name (optional), personality traits, \
communication style, working metaphor, decision approach, team management \
philosophy.
2. **CEO Profile** — CEO's name, working style, communication preferences, \
domain expertise, collaboration patterns, autonomy comfort, decision-making \
style.
3. **Operating Contract** — Proactivity level, escalation sensitivity, \
decision-making autonomy, feedback style, notification preferences, when to \
push back, when to just execute.

Guidelines:
- Ask questions conversationally, not as a checklist
- Propose artifact values based on the conversation; let the CEO approve or \
adjust
- Write each artifact when the CEO confirms it
- Track progress naturally — formation is complete when all three artifacts \
are written
- Be warm and professional, not robotic"""

EVOLUTION_INSTRUCTION: str = """\
The formation artifacts are established. In this Settings conversation, \
either party can propose changes to any artifact. To update an artifact, \
propose the change clearly and wait for CEO confirmation before writing."""
