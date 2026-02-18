"""Global enums for AutoBuilder domain."""

import enum


class WorkflowStatus(enum.StrEnum):
    """Status of a workflow execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DeliverableStatus(enum.StrEnum):
    """Status of a deliverable within a workflow."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class AgentRole(enum.StrEnum):
    """Role of an agent in a workflow pipeline."""

    PLANNER = "PLANNER"
    CODER = "CODER"
    REVIEWER = "REVIEWER"
    FIXER = "FIXER"


class SpecificationStatus(enum.StrEnum):
    """Status of a specification through its lifecycle."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskType(enum.StrEnum):
    """LLM task type for model routing."""

    CODE = "CODE"
    PLAN = "PLAN"
    REVIEW = "REVIEW"
    FAST = "FAST"


class PipelineEventType(enum.StrEnum):
    """Event types emitted during pipeline execution."""

    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_RESULT = "TOOL_RESULT"
    STATE_UPDATED = "STATE_UPDATED"
    ERROR = "ERROR"


class ErrorCode(enum.StrEnum):
    """Machine-readable error codes for API error responses."""

    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    WORKER_ERROR = "WORKER_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
