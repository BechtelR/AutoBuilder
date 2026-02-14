"""Shared domain definitions — enums, constants, base models."""

from app.models.base import BaseModel
from app.models.constants import APP_NAME, APP_VERSION
from app.models.enums import (
    AgentRole,
    DeliverableStatus,
    ErrorCode,
    SpecificationStatus,
    WorkflowStatus,
)

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "AgentRole",
    "BaseModel",
    "DeliverableStatus",
    "ErrorCode",
    "SpecificationStatus",
    "WorkflowStatus",
]
