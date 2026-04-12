"""Stage lifecycle management -- initialization, transitions, state keys."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from app.models.constants import (
    STAGE_COMPLETED_LIST,
    STAGE_CURRENT,
    STAGE_INDEX,
    STAGE_STATUS,
    STAGE_WORKFLOW_STAGES,
)
from app.models.enums import StageStatus

if TYPE_CHECKING:
    from app.workflows.manifest import WorkflowManifest

logger = logging.getLogger(__name__)


def initialize_stage_state(manifest: WorkflowManifest) -> dict[str, object]:
    """Build initial state delta for a staged workflow.

    Returns empty dict for stageless workflows (no-op).
    """
    if not manifest.stages:
        return {}

    first = manifest.stages[0]
    return {
        STAGE_CURRENT: first.name,
        STAGE_INDEX: 0,
        STAGE_STATUS: StageStatus.PENDING,
        STAGE_COMPLETED_LIST: [],
        STAGE_WORKFLOW_STAGES: [s.model_dump() for s in manifest.stages],
    }


def reconfigure_stage(
    state: dict[str, object],
    manifest: WorkflowManifest,
    target_stage: str,
) -> dict[str, object]:
    """Advance to the next sequential stage, returning a state delta.

    Raises ValueError if target is not the immediate next stage.
    Returns empty dict for stageless workflows.
    """
    if not manifest.stages:
        return {}

    # Validate target exists
    stage_names = [s.name for s in manifest.stages]
    if target_stage not in stage_names:
        msg = f"Stage '{target_stage}' not found in workflow stages"
        raise ValueError(msg)

    current_index = int(state.get(STAGE_INDEX, 0))  # type: ignore[arg-type]
    target_index = stage_names.index(target_stage)

    # Enforce sequential advancement
    if target_index < current_index:
        msg = "Cannot revisit completed stage"
        raise ValueError(msg)
    if target_index == current_index:
        msg = "Cannot reconfigure to the current stage"
        raise ValueError(msg)
    if target_index > current_index + 1:
        msg = "Cannot skip stages"
        raise ValueError(msg)

    # Build completed list without mutating input
    raw_completed = state.get(STAGE_COMPLETED_LIST, [])
    existing_completed = cast("list[str]", raw_completed) if isinstance(raw_completed, list) else []
    current_stage_name = stage_names[current_index]
    completed: list[str] = [*existing_completed, current_stage_name]

    return {
        STAGE_CURRENT: target_stage,
        STAGE_INDEX: target_index,
        STAGE_STATUS: StageStatus.ACTIVE,
        STAGE_COMPLETED_LIST: completed,
    }
