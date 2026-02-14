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


class ErrorCode(enum.StrEnum):
    """Machine-readable error codes for API error responses."""

    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    WORKER_ERROR = "WORKER_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
