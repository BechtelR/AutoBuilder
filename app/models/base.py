"""Shared Pydantic base models."""

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    """Base model with shared configuration for all API models."""

    model_config = ConfigDict(from_attributes=True, strict=True)
