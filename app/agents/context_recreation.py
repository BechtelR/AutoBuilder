"""Context recreation pipeline -- 4-step process for session context budget recovery.

Supports both generic context recreation (Phase 5b) and TaskGroup-aware resume
(Phase 8a D13) where checkpoint data from completed TaskGroups is merged into
the seeded state for a fresh session.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from app.lib.exceptions import WorkerError
from app.models.constants import DELIVERABLE_STATUS_PREFIX

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
    *,
    stage_completion_keys: dict[str, str] | None = None,
) -> list[str]:
    """Determine which pipeline stages still need to run.

    Uses ``completed_stages`` if provided; otherwise infers from state
    by checking for known completion keys.

    Args:
        all_stages: Ordered list of all pipeline stage names.
        completed_stages: Explicit list of completed stage names.
        state: Session state dict for inference-based detection.
        stage_completion_keys: Stage->key mapping for state-based detection.
            Required when using state-based inference.
    """
    if completed_stages is not None:
        completed = set(completed_stages)
    elif state is not None and stage_completion_keys is not None:
        completed: set[str] = {
            stage
            for stage, key in stage_completion_keys.items()
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
    stages: list[str] | None = None,
    stage_completion_keys: dict[str, str] | None = None,
) -> RecreationResult:
    """Orchestrate the 4-step context recreation pipeline.

    1. Persist progress to memory (degraded in Phase 5b)
    2. Seed critical keys from old session
    3. Create fresh session with seed state
    4. Determine remaining stages for pipeline rebuild

    Args:
        stages: Ordered stage names for this workflow. Required.
        stage_completion_keys: Stage->key mapping for state-based detection.

    Publishes audit events at start and completion/failure.
    """
    from app.models.enums import PipelineEventType

    if publisher is not None:
        await publisher.publish_lifecycle(
            old_session_id,
            PipelineEventType.CONTEXT_RECREATED,
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
        if stages is None:
            raise WorkerError(message="stages parameter is required for context recreation")
        remaining = determine_remaining_stages(
            stages,
            completed_stages=completed_stages,
            state=old_state,
            stage_completion_keys=stage_completion_keys,
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
                PipelineEventType.CONTEXT_RECREATED,
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


# ---------------------------------------------------------------------------
# TaskGroup-aware context recreation (Phase 8a D13)
# ---------------------------------------------------------------------------

# Keys from checkpoint data that should always be seeded into the fresh session,
# even if they don't match _CRITICAL_KEY_PREFIXES or _OUTPUT_KEY_SUFFIXES.
_CHECKPOINT_SEED_KEYS: tuple[str, ...] = (
    "completed_stages",
    "loaded_skill_names",
    "deliverable_statuses",
    "stage_progress",
    "accumulated_cost",
    "workflow_id",
    "current_taskgroup_id",
)


async def load_taskgroup_checkpoint(
    db_session_factory: async_sessionmaker[AsyncSession],
    taskgroup_execution_id: uuid.UUID,
) -> dict[str, object] | None:
    """Load checkpoint_data from a TaskGroupExecution record.

    Returns the checkpoint dict if present, or None if the record doesn't
    exist or has no checkpoint data.
    """
    from sqlalchemy import select

    from app.db.models import TaskGroupExecution

    async with db_session_factory() as db:
        result = await db.execute(  # type: ignore[union-attr]
            select(TaskGroupExecution).where(TaskGroupExecution.id == taskgroup_execution_id)
        )
        tge = result.scalar_one_or_none()  # type: ignore[union-attr]
        if tge is not None and tge.checkpoint_data is not None:  # type: ignore[union-attr]
            return dict(tge.checkpoint_data)  # type: ignore[union-attr]
        return None


async def recreate_context_at_taskgroup(
    session_service: SessionServiceProtocol,
    old_session: SessionProtocol,
    app_name: str,
    user_id: str,
    *,
    db_session_factory: async_sessionmaker[AsyncSession] | None = None,
    current_taskgroup_id: uuid.UUID | None = None,
    publisher: EventPublisher | None = None,
    workflow_id: str | None = None,
    completed_stages: list[str] | None = None,
    stages: list[str] | None = None,
    stage_completion_keys: dict[str, str] | None = None,
) -> RecreationResult:
    """Context recreation specialized for TaskGroup boundary resume.

    Steps:
    1. If checkpoint exists, load it from TaskGroupExecution.checkpoint_data
    2. Merge checkpoint into old session state (checkpoint wins on conflict)
    3. Seed critical keys from merged state
    4. Ensure checkpoint-specific keys are preserved in seed
    5. Create fresh session with seeded state
    6. Determine remaining stages
    7. Publish context recreation events

    Returns RecreationResult with new_session_id, seeded_keys, remaining_stages.
    """
    from app.models.enums import PipelineEventType

    old_session_id = getattr(old_session, "id", "unknown")
    if not isinstance(old_session_id, str):
        old_session_id = str(old_session_id)

    # Publish initiation event
    if publisher is not None and workflow_id:
        await publisher.publish_lifecycle(
            workflow_id,
            PipelineEventType.CONTEXT_RECREATED,
            metadata={
                "recreation": "started",
                "recreation_type": "taskgroup_boundary",
                "old_session_id": old_session_id,
                "taskgroup_id": str(current_taskgroup_id) if current_taskgroup_id else None,
            },
        )

    try:
        # Step 1: Load checkpoint if available
        checkpoint_data: dict[str, object] = {}
        if db_session_factory is not None and current_taskgroup_id is not None:
            loaded = await load_taskgroup_checkpoint(db_session_factory, current_taskgroup_id)
            if loaded is not None:
                checkpoint_data = loaded
                logger.info(
                    "Loaded checkpoint from TaskGroup %s: %d keys",
                    str(current_taskgroup_id)[:8],
                    len(checkpoint_data),
                )

        # Step 2: Merge checkpoint into old state (checkpoint wins)
        old_state = dict(old_session.state) if old_session.state else {}
        merged_state: dict[str, object] = {**old_state, **checkpoint_data}

        # Step 3: Seed critical keys from merged state
        seeded = seed_critical_keys(merged_state)

        # Step 4: Ensure checkpoint-specific keys are in the seed
        # Check merged_state (not just checkpoint_data) because these keys
        # should always be preserved in TaskGroup-aware recreation regardless
        # of whether they originated from the checkpoint or the old session.
        for key in _CHECKPOINT_SEED_KEYS:
            if key in merged_state and key not in seeded:
                seeded[key] = merged_state[key]

        # Step 5: Create fresh session
        new_session_id = await create_fresh_session(session_service, app_name, user_id, seeded)

        # Step 6: Determine remaining stages
        if stages is not None:
            remaining = determine_remaining_stages(
                stages,
                completed_stages=completed_stages,
                state=merged_state,
                stage_completion_keys=stage_completion_keys,
            )
        else:
            remaining = list[str]()

        result = RecreationResult(
            new_session_id=new_session_id,
            remaining_stages=remaining,
            seeded_keys=sorted(seeded.keys()),
            memory_available=False,
        )

        # Step 7: Publish completion event
        if publisher is not None and workflow_id:
            await publisher.publish_lifecycle(
                workflow_id,
                PipelineEventType.CONTEXT_RECREATED,
                metadata={
                    "recreation": "completed",
                    "recreation_type": "taskgroup_boundary",
                    "old_session_id": old_session_id,
                    "new_session_id": new_session_id,
                    "seeded_keys": list(seeded.keys()),
                    "remaining_stages": remaining,
                    "taskgroup_id": str(current_taskgroup_id) if current_taskgroup_id else None,
                },
            )

        logger.info(
            "TaskGroup context recreation completed: old=%s new=%s remaining=%d stages",
            old_session_id,
            new_session_id,
            len(remaining),
        )
        return result

    except WorkerError:
        if publisher is not None and workflow_id:
            await publisher.publish_lifecycle(
                workflow_id,
                PipelineEventType.ERROR,
                metadata={
                    "recreation": "failed",
                    "recreation_type": "taskgroup_boundary",
                    "old_session_id": old_session_id,
                },
            )
        raise
    except Exception as exc:
        if publisher is not None and workflow_id:
            await publisher.publish_lifecycle(
                workflow_id,
                PipelineEventType.ERROR,
                metadata={
                    "recreation": "failed",
                    "recreation_type": "taskgroup_boundary",
                    "old_session_id": old_session_id,
                    "error": str(exc),
                },
            )
        raise WorkerError(message=f"TaskGroup context recreation failed: {exc}") from exc
