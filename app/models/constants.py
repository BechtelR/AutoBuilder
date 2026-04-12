"""Global constants for AutoBuilder."""

from app.models.enums import AgentTier

APP_NAME: str = "autobuilder"
APP_VERSION: str = "0.1.0"
SYSTEM_USER_ID: str = "system"
INIT_SESSION_ID: str = "__init__"

# ---------------------------------------------------------------------------
# State key constants for Phase 5b
# ---------------------------------------------------------------------------

# Director-tier keys
DIRECTOR_GOVERNANCE_KEY: str = "director:governance_override"
DIRECTOR_QUEUE_PROCESSED_KEY: str = "director:last_queue_check"

# Formation artifacts (user: scope)
DIRECTOR_IDENTITY_KEY: str = "user:director_identity"
CEO_PROFILE_KEY: str = "user:ceo_profile"
OPERATING_CONTRACT_KEY: str = "user:operating_contract"
FORMATION_STATUS_KEY: str = "user:formation_status"

# PM-tier keys
PM_BATCH_POSITION_KEY: str = "pm:batch_position"
PM_ESCALATION_CONTEXT_KEY: str = "pm:escalation_context"

# Approval resolution pattern
APPROVAL_RESOLUTION_PREFIX: str = "pm:approval:"

# Shared workspace keys
DELIVERABLE_STATUS_PREFIX: str = "deliverable_status:"
BATCH_RESULT_KEY: str = "batch_result"

# Tier prefix authorization mapping
# Maps key prefix -> minimum required tier for write access
TIER_PREFIX_WRITE_ACCESS: dict[str, AgentTier] = {
    "director:": AgentTier.DIRECTOR,
    "pm:": AgentTier.PM,
    "app:": AgentTier.PM,
    "worker:": AgentTier.WORKER,
    "user:": AgentTier.WORKER,
    "temp:": AgentTier.WORKER,
}
# Keys with no recognized prefix -> writable by all tiers (WORKER and above)

# ---------------------------------------------------------------------------
# Stage state keys (Phase 7 — all pm: prefixed for tier authorization)
# ---------------------------------------------------------------------------
STAGE_CURRENT: str = "pm:current_stage"
STAGE_INDEX: str = "pm:stage_index"
STAGE_STATUS: str = "pm:stage_status"
STAGE_COMPLETED_LIST: str = "pm:stages_completed"
STAGE_WORKFLOW_STAGES: str = "pm:workflow_stages"
