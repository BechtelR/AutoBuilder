"""Context recreation pipeline -- 4-step process for session context budget recovery."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from app.agents.pipeline import PIPELINE_STAGE_NAMES
from app.lib.exceptions import WorkerError
from app.models.constants import DELIVERABLE_STATUS_PREFIX

if TYPE_CHECKING:
    from app.events.publisher import EventPublisher

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Session service Protocol — structural alternative to ADK BaseSessionService
# ---------------------------------------------------------------------------


class SessionProtocol(Protocol):
    """Structural protocol for an ADK session object."""

    state: dict[str, object]


class SessionServiceProtocol(Protocol):
    """Structural protocol for ADK session services used in context recreation."""

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        state: dict[str, object] | None = None,
    ) -> SessionProtocol: ...

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> SessionProtocol | None: ...


# Module-level alias used by this module and tests
PIPELINE_STAGES = PIPELINE_STAGE_NAMES

# Stage name -> state key that indicates completion
STAGE_COMPLETION_KEYS: dict[str, str] = {
    "skill_loader": "loaded_skill_names",
    "memory_loader": "memory_context",
    "planner": "plan_output",
    "coder": "code_output",
    "formatter": "formatter_output",
    "linter": "linter_output",
    "tester": "tester_output",
    "diagnostics": "diagnostics_output",
    "review_cycle": "review_passed",
}

# Key prefixes to always seed into fresh session
_CRITICAL_KEY_PREFIXES: list[str] = [
    DELIVERABLE_STATUS_PREFIX,  # "deliverable_status:"
    "pm:",  # PM-tier state
    "director:",  # Director-tier state
    "project_config",  # Hard limits
    "workflow_id",  # Session identity
    "loaded_skill_names",  # Skills to reload
]

# Suffixes that indicate agent output keys worth preserving
_OUTPUT_KEY_SUFFIXES: tuple[str, ...] = ("_output", "_result", "_response")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecreationResult:
    """Result of a context recreation pipeline execution."""

    new_session_id: str
    remaining_stages: list[str] = field(default_factory=lambda: list[str]())
    seeded_keys: list[str] = field(default_factory=lambda: list[str]())
    memory_available: bool = False


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------


def identify_critical_keys(state: dict[str, object]) -> list[str]:
    """Return sorted list of state keys that should be preserved across recreation.

    Includes keys matching critical prefixes and agent output keys.
    """
    result: set[str] = set()

    for key in state:
        # Check critical prefixes
        for prefix in _CRITICAL_KEY_PREFIXES:
            if key.startswith(prefix):
                result.add(key)
                break
        else:
            # Check output key suffixes
            for suffix in _OUTPUT_KEY_SUFFIXES:
                if key.endswith(suffix):
                    result.add(key)
                    break

    return sorted(result)


def determine_remaining_stages(
    all_stages: list[str],
    completed_stages: list[str] | None = None,
    state: dict[str, object] | None = None,
) -> list[str]:
    """Determine which pipeline stages still need to run.

    Uses ``completed_stages`` if provided; otherwise infers from state
    by checking for known completion keys.
    """
    if completed_stages is not None:
        completed = set(completed_stages)
    elif state is not None:
        completed: set[str] = {
            stage
            for stage, key in STAGE_COMPLETION_KEYS.items()
            if key in state and state[key] is not None
        }
    else:
        completed = set[str]()

    return [s for s in all_stages if s not in completed]


def seed_critical_keys(old_state: dict[str, object]) -> dict[str, object]:
    """Extract critical keys from old session state for seeding into a new session."""
    keys = identify_critical_keys(old_state)
    return {k: old_state[k] for k in keys}


async def persist_to_memory(
    state: dict[str, object],
    memory_service: object | None,
) -> bool:
    """Step 1: Save progress markers to memory service.

    Phase 5b degraded mode: always returns False (no persistent memory).
    """
    if memory_service is None:
        logger.debug("Memory service unavailable — skipping persist step (degraded mode)")
        return False

    # Phase 5b: no real memory service integration yet
    logger.debug("Memory service present but Phase 5b degraded — skipping persist")
    return False


async def create_fresh_session(
    session_service: SessionServiceProtocol,
    app_name: str,
    user_id: str,
    seed_state: dict[str, object],
) -> str:
    """Step 3: Create a new ADK session with seeded state.

    Returns the new session ID. Old session is preserved (not deleted).
    """
    new_session_id = str(uuid.uuid4())

    await session_service.create_session(  # type: ignore[reportUnknownMemberType]
        app_name=app_name,
        user_id=user_id,
        session_id=new_session_id,
        state=seed_state,
    )

    logger.info("Created fresh session %s with %d seeded keys", new_session_id, len(seed_state))
    return new_session_id


async def recreate_context(
    session_service: SessionServiceProtocol,
    app_name: str,
    user_id: str,
    old_session_id: str,
    publisher: EventPublisher | None = None,
    *,
    memory_service: object | None = None,
    completed_stages: list[str] | None = None,
) -> RecreationResult:
    """Orchestrate the 4-step context recreation pipeline.

    1. Persist progress to memory (degraded in Phase 5b)
    2. Seed critical keys from old session
    3. Create fresh session with seed state
    4. Determine remaining stages for pipeline rebuild

    Publishes audit events at start and completion/failure.
    """
    from app.models.enums import PipelineEventType

    if publisher is not None:
        await publisher.publish_lifecycle(
            old_session_id,
            PipelineEventType.STATE_UPDATED,
            metadata={"recreation": "started", "old_session_id": old_session_id},
        )

    try:
        # Load old session state
        old_session = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=app_name,
            user_id=user_id,
            session_id=old_session_id,
        )
        if old_session is None:
            raise WorkerError(message=f"Old session {old_session_id} not found for recreation")

        old_state = dict(old_session.state)  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]

        # Step 1: Persist to memory (degraded)
        memory_available = await persist_to_memory(old_state, memory_service)

        # Step 2: Seed critical keys
        seed_state = seed_critical_keys(old_state)

        # Step 3: Create fresh session
        new_session_id = await create_fresh_session(session_service, app_name, user_id, seed_state)

        # Step 4: Determine remaining stages
        remaining = determine_remaining_stages(
            PIPELINE_STAGES,
            completed_stages=completed_stages,
            state=old_state,
        )

        result = RecreationResult(
            new_session_id=new_session_id,
            remaining_stages=remaining,
            seeded_keys=sorted(seed_state.keys()),
            memory_available=memory_available,
        )

        if publisher is not None:
            await publisher.publish_lifecycle(
                new_session_id,
                PipelineEventType.STATE_UPDATED,
                metadata={
                    "recreation": "completed",
                    "old_session_id": old_session_id,
                    "remaining_stages": len(remaining),
                    "seeded_keys": len(seed_state),
                },
            )

        logger.info(
            "Context recreation completed: old=%s new=%s remaining=%d stages",
            old_session_id,
            new_session_id,
            len(remaining),
        )
        return result

    except WorkerError:
        # Already a WorkerError — publish and re-raise
        if publisher is not None:
            await publisher.publish_lifecycle(
                old_session_id,
                PipelineEventType.ERROR,
                metadata={
                    "recreation": "failed",
                    "old_session_id": old_session_id,
                },
            )
        raise
    except Exception as exc:
        if publisher is not None:
            await publisher.publish_lifecycle(
                old_session_id,
                PipelineEventType.ERROR,
                metadata={
                    "recreation": "failed",
                    "old_session_id": old_session_id,
                    "error": str(exc),
                },
            )
        raise WorkerError(
            message=f"Context recreation failed for session {old_session_id}: {exc}"
        ) from exc
