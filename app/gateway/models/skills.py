"""Skill catalog API models."""

from pydantic import BaseModel

from app.skills.library import TriggerSpec


class SkillCatalogEntry(BaseModel):
    """Lightweight skill entry for catalog API."""

    name: str
    description: str
    triggers: list[TriggerSpec]
    tags: list[str]
    applies_to: list[str]
    priority: int
    has_references: bool
    has_assets: bool
    has_scripts: bool
