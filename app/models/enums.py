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


class ModelRole(enum.StrEnum):
    """LLM model role for routing — which persona handles a job."""

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


class GitBranchAction(enum.StrEnum):
    """Action to perform on a git branch."""

    CREATE = "CREATE"
    SWITCH = "SWITCH"
    DELETE = "DELETE"


class TodoAction(enum.StrEnum):
    """Action to perform on a todo item."""

    ADD = "ADD"
    UPDATE = "UPDATE"
    COMPLETE = "COMPLETE"
    REMOVE = "REMOVE"


class TodoStatus(enum.StrEnum):
    """Status of a todo item."""

    PENDING = "PENDING"
    DONE = "DONE"


class GitWorktreeAction(enum.StrEnum):
    """Action to perform on a git worktree."""

    ADD = "ADD"
    LIST = "LIST"
    REMOVE = "REMOVE"


class EscalationPriority(enum.StrEnum):
    """Priority level for escalations."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EscalationRequestType(enum.StrEnum):
    """Type of escalation request from PM to Director."""

    ESCALATION = "ESCALATION"
    STATUS_REPORT = "STATUS_REPORT"
    RESOURCE_REQUEST = "RESOURCE_REQUEST"
    PATTERN_ALERT = "PATTERN_ALERT"


class CeoItemType(enum.StrEnum):
    """Type of item escalated to the CEO queue."""

    NOTIFICATION = "NOTIFICATION"
    APPROVAL = "APPROVAL"
    ESCALATION = "ESCALATION"
    TASK = "TASK"


class DependencyAction(enum.StrEnum):
    """Action to perform on deliverable dependencies."""

    ADD = "ADD"
    REMOVE = "REMOVE"
    QUERY = "QUERY"


class PmOverrideAction(enum.StrEnum):
    """Action for Director to override a PM."""

    PAUSE = "PAUSE"
    RESUME = "RESUME"
    REORDER = "REORDER"
    CORRECT = "CORRECT"


class TaskStatus(enum.StrEnum):
    """Status of a shared cross-session task."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class DirectorQueueStatus(enum.StrEnum):
    """Status of an item in the Director queue (BOM V22)."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    FORWARDED_TO_CEO = "FORWARDED_TO_CEO"


class ChatType(enum.StrEnum):
    """Type of chat session."""

    DIRECTOR = "DIRECTOR"
    PROJECT = "PROJECT"
    SETTINGS = "SETTINGS"


class ChatStatus(enum.StrEnum):
    """Status of a chat session."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ChatMessageRole(enum.StrEnum):
    """Role of a message sender in a chat."""

    USER = "USER"
    DIRECTOR = "DIRECTOR"


class CeoQueueStatus(enum.StrEnum):
    """Status of an item in the CEO queue."""

    PENDING = "PENDING"
    SEEN = "SEEN"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class AgentType(enum.StrEnum):
    """Type of agent definition."""

    LLM = "LLM"
    CUSTOM = "CUSTOM"


class DefinitionScope(enum.StrEnum):
    """Scope level for agent definition files."""

    GLOBAL = "GLOBAL"
    WORKFLOW = "WORKFLOW"
    PROJECT = "PROJECT"


class FragmentType(enum.StrEnum):
    """Instruction fragment type for InstructionAssembler."""

    SAFETY = "SAFETY"
    IDENTITY = "IDENTITY"
    GOVERNANCE = "GOVERNANCE"
    PROJECT = "PROJECT"
    TASK = "TASK"
    SKILL = "SKILL"


class ErrorCode(enum.StrEnum):
    """Machine-readable error codes for API error responses."""

    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    WORKER_ERROR = "WORKER_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AgentTier(enum.StrEnum):
    """Tier-based authorization level for agent state key access."""

    DIRECTOR = "DIRECTOR"
    PM = "PM"
    WORKER = "WORKER"


class SupervisionEventType(enum.StrEnum):
    """Event types for supervision and oversight."""

    PM_INVOCATION = "PM_INVOCATION"
    PM_COMPLETION = "PM_COMPLETION"
    ESCALATION_DETECTED = "ESCALATION_DETECTED"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    STATE_AUTH_VIOLATION = "STATE_AUTH_VIOLATION"


class CeoQueueAction(enum.StrEnum):
    """Action a CEO can take on a queue item."""

    RESOLVE = "RESOLVE"
    DISMISS = "DISMISS"


class FormationStatus(enum.StrEnum):
    """Status of the Director formation process."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
