"""Health check response models."""

from typing import Literal

from app.models.base import BaseModel

ServiceStatus = Literal["ok", "unavailable"]
HealthStatus = Literal["ok", "degraded"]


class HealthResponse(BaseModel):
    """Health check response with per-service status."""

    status: HealthStatus
    version: str
    services: dict[str, ServiceStatus]
