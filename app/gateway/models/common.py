"""Common API response models."""

from pydantic import Field

from app.models.base import BaseModel
from app.models.enums import ErrorCode


class ErrorDetail(BaseModel):
    """Inner envelope for structured error responses."""

    code: ErrorCode
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response envelope. All errors follow this shape."""

    error: ErrorDetail
