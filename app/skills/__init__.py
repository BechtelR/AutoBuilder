"""Skills system for AutoBuilder — types, parser, and library."""

from app.skills.library import CascadeRef, SkillEntry, SkillLibrary, TriggerSpec
from app.skills.parser import parse_skill_frontmatter, validate_skill_frontmatter

__all__ = [
    "CascadeRef",
    "SkillEntry",
    "SkillLibrary",
    "TriggerSpec",
    "parse_skill_frontmatter",
    "validate_skill_frontmatter",
]
