"""Management tools for PM and Director agents.

PM tools handle deliverable lifecycle, batching, escalation, and dependencies.
Director tools handle project oversight, CEO escalation, and PM overrides.
"""

import json
import tomllib
import uuid
from pathlib import Path
from typing import cast

from google.adk.tools.tool_context import ToolContext

from app.lib.logging import get_logger
from app.models.constants import (
    STAGE_WORKFLOW_STAGES,
)
from app.models.enums import (
    CeoItemType,
    DependencyAction,
    EscalationPriority,
    EscalationRequestType,
    PmOverrideAction,
)

logger = get_logger("tools.management")

# Config files that indicate a project and its ecosystem
_PROJECT_CONFIG_FILES: dict[str, str] = {
    "pyproject.toml": "Python",
    "package.json": "JavaScript/TypeScript",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java (Gradle)",
}


# ===================================================================
# PM Tools
# ===================================================================


def select_ready_batch(project_id: str) -> str:
    """Dependency-aware batch selection via topological sort.

    Returns the next set of deliverables whose prerequisites are satisfied.

    Args:
        project_id: The project to select a ready batch for.

    Returns:
        A description of the selected batch.
    """
    return f"Ready batch for project {project_id} (placeholder — dependency resolution in Phase 5)"


def escalate_to_director(
    priority: EscalationPriority,
    context: str,
    request_type: EscalationRequestType,
) -> str:
    """Escalate an issue from PM to the Director queue for resolution.

    Used by PM agents when they encounter situations requiring
    higher-level decision-making or cross-project coordination.

    Args:
        priority: Urgency level — LOW, NORMAL, HIGH, or CRITICAL.
        context: Detailed description of the situation.
        request_type: Category — ESCALATION, STATUS_REPORT,
            RESOURCE_REQUEST, or PATTERN_ALERT.

    Returns:
        Confirmation string with the queued escalation ID.
    """
    escalation_id = uuid.uuid4().hex[:8]
    logger.info(
        "Escalation %s queued: type=%s priority=%s context=%s",
        escalation_id,
        request_type,
        priority,
        context[:120],
    )
    return (
        f"Escalation {escalation_id} queued to Director: "
        f"{request_type} [{priority}] "
        "(placeholder — Director queue in Phase 5)"
    )


def update_deliverable(
    deliverable_id: str,
    status: str,
    notes: str | None = None,
) -> str:
    """Update a deliverable's lifecycle status with optional notes.

    Args:
        deliverable_id: Unique identifier of the deliverable.
        status: New status value to set.
        notes: Optional freeform notes about the update.

    Returns:
        Confirmation of the update.
    """
    suffix = f" notes='{notes}'" if notes else ""
    return (
        f"Deliverable {deliverable_id} updated to status '{status}'"
        f"{suffix} (placeholder — persistence in Phase 5)"
    )


def query_deliverables(
    project_id: str,
    status: str | None = None,
) -> str:
    """Query deliverable state for a project, optionally filtered by status.

    Args:
        project_id: The project whose deliverables to query.
        status: Optional status filter.

    Returns:
        Summary of matching deliverables.
    """
    filter_msg = f" with status '{status}'" if status else ""
    return f"Deliverables for project {project_id}{filter_msg} (placeholder — query in Phase 5)"


def reorder_deliverables(project_id: str, order: list[str]) -> str:
    """Change execution priority by reordering deliverables.

    Args:
        project_id: The project to reorder deliverables in.
        order: Ordered list of deliverable IDs defining the new sequence.

    Returns:
        Confirmation with count of reordered items.
    """
    return (
        f"Reordered {len(order)} deliverables for project {project_id} "
        "(placeholder — persistence in Phase 5)"
    )


def reconfigure_stage(
    tool_context: ToolContext,
    target_stage: str,
    reason: str,
) -> str:
    """Advance the workflow to the next sequential stage.

    Validates that the transition is legal (no backwards, no skipping),
    then writes the stage state delta via ToolContext. Delegates validation
    and delta computation to the domain function in ``app.workflows.stages``.

    Args:
        tool_context: ADK-injected session context (excluded from LLM schema).
        target_stage: Name of the stage to transition to.
        reason: Why the PM is transitioning to this stage.

    Returns:
        JSON string describing the transition result, or an error message.
    """
    from app.models.constants import (
        STAGE_COMPLETED_LIST,
        STAGE_CURRENT,
        STAGE_INDEX,
        STAGE_STATUS,
    )
    from app.workflows.manifest import StageDef, WorkflowManifest
    from app.workflows.stages import reconfigure_stage as _domain_reconfigure

    # Read serialized stage schema from session state
    raw_stages: object = tool_context.state.get(STAGE_WORKFLOW_STAGES)  # type: ignore[union-attr]
    if raw_stages is None or not isinstance(raw_stages, list):
        return json.dumps({"error": "No workflow stages configured in session state"})

    stages_data: list[dict[str, object]] = cast("list[dict[str, object]]", raw_stages)

    # Reconstruct minimal manifest from serialized state for domain function
    stage_defs = [StageDef.model_validate(s) for s in stages_data]
    manifest = WorkflowManifest(name="__tool_ctx__", description="", stages=stage_defs)

    # Build current state snapshot for domain function
    state: dict[str, object] = {
        STAGE_CURRENT: tool_context.state.get(STAGE_CURRENT, ""),  # type: ignore[union-attr]
        STAGE_INDEX: tool_context.state.get(STAGE_INDEX, 0),  # type: ignore[union-attr]
        STAGE_STATUS: tool_context.state.get(STAGE_STATUS, ""),  # type: ignore[union-attr]
        STAGE_COMPLETED_LIST: tool_context.state.get(  # type: ignore[union-attr]
            STAGE_COMPLETED_LIST, []
        ),
    }

    try:
        delta = _domain_reconfigure(state, manifest, target_stage)
    except ValueError as exc:
        stage_names = [s.name for s in stage_defs]
        current_name = str(state.get(STAGE_CURRENT, ""))
        return json.dumps(
            {
                "error": str(exc),
                "current_stage": current_name,
                "target_stage": target_stage,
                "available_stages": stage_names,
            }
        )

    if not delta:
        # No-stages workflow — no-op
        return json.dumps({"status": "ok", "message": "No stages configured (no-op)"})

    # Write state delta via ToolContext (ADK pattern)
    for key, value in delta.items():
        tool_context.actions.state_delta[key] = value  # type: ignore[index]

    previous_stage = str(state.get(STAGE_CURRENT, ""))
    logger.info(
        "Stage transition: %s -> %s (reason: %s)",
        previous_stage,
        target_stage,
        reason[:120],
    )

    return json.dumps(
        {
            "status": "ok",
            "previous_stage": previous_stage,
            "current_stage": target_stage,
            "stage_index": delta.get(STAGE_INDEX),
            "completed_stages": delta.get(STAGE_COMPLETED_LIST),
            "reason": reason,
        }
    )


def manage_dependencies(
    action: DependencyAction,
    source_id: str,
    target_id: str | None = None,
) -> str:
    """Add, remove, or query deliverable dependency relationships.

    Args:
        action: Operation to perform — ADD, REMOVE, or QUERY.
        source_id: The deliverable that depends on another.
        target_id: The deliverable being depended upon (required for
            ADD and REMOVE).

    Returns:
        Confirmation or query result.
    """
    if action in {DependencyAction.ADD, DependencyAction.REMOVE} and target_id is None:
        return f"target_id is required for {action} action"

    target_msg = f" -> {target_id}" if target_id else ""
    return (
        f"Dependency {action} on {source_id}{target_msg} "
        "(placeholder — dependency graph in Phase 5)"
    )


# ===================================================================
# Director Tools
# ===================================================================


def escalate_to_ceo(
    item_type: CeoItemType,
    priority: EscalationPriority,
    message: str,
    metadata: str,
) -> str:
    """Push a notification, approval request, escalation, or task to the unified CEO queue.

    Director-only -- PM uses escalate_to_director instead.

    Args:
        item_type: Category — NOTIFICATION, APPROVAL, ESCALATION,
            or TASK.
        priority: Urgency level — LOW, NORMAL, HIGH, or CRITICAL.
        message: Human-readable description of the item.
        metadata: JSON-encoded supplementary data.

    Returns:
        Confirmation string with the queued item ID.
    """
    item_id = uuid.uuid4().hex[:8]
    logger.info(
        "CEO queue item %s: type=%s priority=%s message=%s",
        item_id,
        item_type,
        priority,
        message[:120],
    )
    return (
        f"CEO queue item {item_id}: {item_type} [{priority}] (placeholder — CEO queue in Phase 5)"
    )


def list_projects(status: str | None = None) -> str:
    """List all projects with optional status filter for cross-project visibility.

    Args:
        status: Optional status filter.

    Returns:
        Summary of matching projects.
    """
    filter_msg = f" with status '{status}'" if status else ""
    return f"Projects{filter_msg} (placeholder — query in Phase 5)"


def query_project_status(project_id: str) -> str:
    """Query detailed project status including PM state, batch progress, and cost.

    Args:
        project_id: The project to query.

    Returns:
        Status summary for the project.
    """
    return f"Status for project {project_id} (placeholder — query in Phase 5)"


def override_pm(project_id: str, action: PmOverrideAction, reason: str) -> str:
    """Direct PM intervention: pause, resume, reorder, or correct a PM's behavior.

    Args:
        project_id: The project whose PM to override.
        action: Override type — PAUSE, RESUME, REORDER, or CORRECT.
        reason: Justification for the override.

    Returns:
        Confirmation of the override.
    """
    logger.info(
        "PM override on project %s: action=%s reason=%s",
        project_id,
        action,
        reason[:120],
    )
    return (
        f"PM override on project {project_id}: {action} "
        f"reason='{reason}' (placeholder — PM control in Phase 5)"
    )


def get_project_context(path: str | None = None) -> str:
    """Detect project type, technology stack, and conventions from the codebase.

    Args:
        path: Directory to scan. Defaults to current working directory.

    Returns:
        Formatted project context summary.
    """
    scan_dir = Path(path) if path else Path.cwd()

    if not scan_dir.is_dir():
        return f"Path is not a directory: {scan_dir}"

    findings: list[str] = []

    for config_file, language in _PROJECT_CONFIG_FILES.items():
        config_path = scan_dir / config_file

        if not config_path.is_file():
            continue

        try:
            if config_file == "pyproject.toml":
                info = _parse_pyproject(config_path)
            elif config_file == "package.json":
                info = _parse_package_json(config_path)
            else:
                info = f"Detected {language} project ({config_file} present)"

            findings.append(info)
        except Exception as exc:  # noqa: BLE001
            findings.append(f"Error reading {config_file}: {exc}")

    if not findings:
        return f"No recognised project config files found in {scan_dir}"

    header = f"Project context for {scan_dir}:"
    return "\n".join([header, *findings])


def _parse_pyproject(config_path: Path) -> str:
    """Extract name and dependencies from pyproject.toml."""
    with config_path.open("rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    name = project.get("name", "unknown")

    deps: list[str] = project.get("dependencies", [])
    dep_summary = ", ".join(deps[:10]) if deps else "none listed"
    truncated = f" (+{len(deps) - 10} more)" if len(deps) > 10 else ""

    return f"Python project: {name}\n  Dependencies: {dep_summary}{truncated}"


class _PackageJson:
    """Typed wrapper for package.json parsing."""

    def __init__(self, name: str, dependencies: dict[str, str]) -> None:
        self.name = name
        self.dependencies = dependencies

    @classmethod
    def from_file(cls, path: Path) -> "_PackageJson":
        raw_text = path.read_text(encoding="utf-8")
        data: dict[str, object] = json.loads(raw_text)
        name = str(data.get("name", "unknown"))
        raw_deps = data.get("dependencies")
        deps: dict[str, str] = {}
        if isinstance(raw_deps, dict):
            # json.loads guarantees str keys for JSON objects
            for k, v in raw_deps.items():  # type: ignore[reportUnknownVariableType]
                deps[str(k)] = str(v)  # type: ignore[reportUnknownArgumentType]
        return cls(name=name, dependencies=deps)


def _parse_package_json(config_path: Path) -> str:
    """Extract name and dependencies from package.json."""
    pkg = _PackageJson.from_file(config_path)

    name = pkg.name
    deps = list(pkg.dependencies.keys())
    dep_summary = ", ".join(deps[:10]) if deps else "none listed"
    truncated = f" (+{len(deps) - 10} more)" if len(deps) > 10 else ""

    return f"JavaScript/TypeScript project: {name}\n  Dependencies: {dep_summary}{truncated}"


def query_dependency_graph(
    project_id: str,
    deliverable_id: str | None = None,
) -> str:
    """Query or visualize the deliverable dependency graph for a project.

    Args:
        project_id: The project whose dependency graph to query.
        deliverable_id: Optional deliverable to focus the query on.

    Returns:
        Dependency graph summary.
    """
    focus = f" focused on deliverable {deliverable_id}" if deliverable_id else ""
    return (
        f"Dependency graph for project {project_id}{focus} (placeholder — graph query in Phase 5)"
    )
