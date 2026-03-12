"""Frontmatter parser for SKILL.md files."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import yaml

from app.models.enums import TriggerType
from app.skills.library import CascadeRef, SkillEntry, TriggerSpec

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def _parse_triggers(raw_triggers: object) -> list[TriggerSpec]:
    """Convert raw YAML trigger list to TriggerSpec objects.

    Each trigger is a dict with one key (the trigger type) and one value.
    Example YAML: ``- deliverable_type: api_endpoint``
    """
    if not isinstance(raw_triggers, list):
        return []

    specs: list[TriggerSpec] = []
    trigger_list = cast("list[object]", raw_triggers)
    for raw_item in trigger_list:
        if not isinstance(raw_item, dict):
            continue
        item = cast("dict[str, object]", raw_item)
        for key, val in item.items():
            try:
                trigger_type = TriggerType(key.upper())
            except ValueError:
                logger.warning("Unknown trigger type: %s", key)
                continue
            # 'always' trigger has no meaningful value
            value = "" if val is None or val is True else str(val)
            specs.append(TriggerSpec(trigger_type=trigger_type, value=value))
    return specs


def _parse_cascades(raw_cascades: object) -> list[CascadeRef]:
    """Convert raw YAML cascade list to CascadeRef objects."""
    if not isinstance(raw_cascades, list):
        return []

    refs: list[CascadeRef] = []
    cascade_list = cast("list[object]", raw_cascades)
    for raw_item in cascade_list:
        if not isinstance(raw_item, dict):
            continue
        item = cast("dict[str, object]", raw_item)
        ref_val = item.get("reference")
        if isinstance(ref_val, str):
            refs.append(CascadeRef(reference=ref_val))
    return refs


def parse_skill_frontmatter(file_path: Path) -> SkillEntry | None:
    """Parse YAML frontmatter from a SKILL.md file.

    Returns SkillEntry on success, None on failure (with warning log).
    Lenient: unknown fields ignored (Pydantic extra="ignore").
    Strict on required: missing name or description returns None.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to read skill file %s: %s", file_path, exc)
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        logger.warning("No valid frontmatter delimiters in %s", file_path)
        return None

    raw_frontmatter: object = None
    try:
        raw_frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        logger.warning("Invalid YAML in %s: %s", file_path, exc)
        return None

    if not isinstance(raw_frontmatter, dict):
        logger.warning("Frontmatter is not a mapping in %s", file_path)
        return None

    frontmatter = cast("dict[str, object]", raw_frontmatter)

    # Validate required fields
    errors = validate_skill_frontmatter(frontmatter)
    if errors:
        for err in errors:
            logger.warning("Skill validation error in %s: %s", file_path, err)
        return None

    # Build SkillEntry fields
    triggers = _parse_triggers(frontmatter.get("triggers"))
    cascades = _parse_cascades(frontmatter.get("cascades"))

    tags_raw = frontmatter.get("tags")
    tags: list[str] = (
        [str(t) for t in cast("list[object]", tags_raw)] if isinstance(tags_raw, list) else []
    )

    applies_raw = frontmatter.get("applies_to")
    applies_to: list[str] = (
        [str(a) for a in cast("list[object]", applies_raw)] if isinstance(applies_raw, list) else []
    )

    priority_raw = frontmatter.get("priority", 0)
    priority = int(priority_raw) if isinstance(priority_raw, (int, float)) else 0

    # Detect references/, assets/, and scripts/ subdirectories
    parent_dir = file_path.parent
    has_references = (parent_dir / "references").is_dir()
    has_assets = (parent_dir / "assets").is_dir()
    has_scripts = (parent_dir / "scripts").is_dir()

    try:
        entry = SkillEntry.model_validate(
            {
                "name": frontmatter["name"],
                "description": frontmatter.get("description", ""),
                "triggers": [t.model_dump() for t in triggers],
                "tags": tags,
                "applies_to": applies_to,
                "priority": priority,
                "cascades": [c.model_dump() for c in cascades],
                "has_references": has_references,
                "has_assets": has_assets,
                "has_scripts": has_scripts,
                "path": file_path,
            }
        )
    except Exception as exc:
        logger.warning("Failed to create SkillEntry from %s: %s", file_path, exc)
        return None

    return entry


def validate_skill_frontmatter(frontmatter: dict[str, object]) -> list[str]:
    """Validate frontmatter dict against skill schema.

    Returns list of error strings (empty = valid).
    Callable by agents before writing skill files.
    """
    errors: list[str] = []

    if "name" not in frontmatter or not frontmatter["name"]:
        errors.append("Missing required field: name")

    if "description" not in frontmatter or not frontmatter["description"]:
        errors.append("Missing required field: description")

    name = frontmatter.get("name")
    if name is not None and not isinstance(name, str):
        errors.append("Field 'name' must be a string")

    desc = frontmatter.get("description")
    if desc is not None and not isinstance(desc, str):
        errors.append("Field 'description' must be a string")

    triggers = frontmatter.get("triggers")
    if triggers is not None and not isinstance(triggers, list):
        errors.append("Field 'triggers' must be a list")

    tags = frontmatter.get("tags")
    if tags is not None and not isinstance(tags, list):
        errors.append("Field 'tags' must be a list")

    applies_to = frontmatter.get("applies_to")
    if applies_to is not None and not isinstance(applies_to, list):
        errors.append("Field 'applies_to' must be a list")

    priority = frontmatter.get("priority")
    if priority is not None and not isinstance(priority, (int, float)):
        errors.append("Field 'priority' must be a number")

    cascades_val = frontmatter.get("cascades")
    if cascades_val is not None and not isinstance(cascades_val, list):
        errors.append("Field 'cascades' must be a list")

    return errors
