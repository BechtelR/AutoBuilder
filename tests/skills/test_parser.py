"""Tests for skill frontmatter parser and validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from app.models.enums import TriggerType
from app.skills.library import CascadeRef, SkillEntry, TriggerSpec
from app.skills.parser import parse_skill_frontmatter, validate_skill_frontmatter

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FULL_SKILL_MD = """\
---
name: fastapi-endpoint
description: How to implement a REST API endpoint following project conventions
triggers:
  - deliverable_type: api_endpoint
  - file_pattern: "*/routes/*.py"
  - tag_match: api
  - explicit: fastapi-endpoint
  - always: true
tags: [api, http, routing, fastapi]
applies_to: [coder, reviewer]
priority: 10
cascades:
  - reference: error-handling
  - reference: project-conventions
extra_unknown_field: should_be_ignored
---

## API Endpoint Implementation

This is the body content.
"""

MINIMAL_SKILL_MD = """\
---
name: minimal-skill
description: A minimal skill
---

Body here.
"""


# ---------------------------------------------------------------------------
# parse_skill_frontmatter — happy path
# ---------------------------------------------------------------------------


class TestParseSkillFrontmatter:
    def test_full_frontmatter(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "fastapi-endpoint"
        skill_dir.mkdir()
        (skill_dir / "references").mkdir()
        (skill_dir / "assets").mkdir()
        (skill_dir / "scripts").mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(FULL_SKILL_MD)

        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        assert entry.name == "fastapi-endpoint"
        assert "REST API endpoint" in entry.description
        assert len(entry.triggers) == 5
        assert entry.tags == ["api", "http", "routing", "fastapi"]
        assert entry.applies_to == ["coder", "reviewer"]
        assert entry.priority == 10
        assert len(entry.cascades) == 2
        assert entry.cascades[0] == CascadeRef(reference="error-handling")
        assert entry.cascades[1] == CascadeRef(reference="project-conventions")
        assert entry.has_references is True
        assert entry.has_assets is True
        assert entry.has_scripts is True
        assert entry.path == skill_file

    def test_minimal_frontmatter(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(MINIMAL_SKILL_MD)

        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        assert entry.name == "minimal-skill"
        assert entry.description == "A minimal skill"
        assert entry.triggers == []
        assert entry.tags == []
        assert entry.applies_to == []
        assert entry.priority == 0
        assert entry.cascades == []
        assert entry.has_references is False
        assert entry.has_assets is False

    def test_no_references_or_assets_or_scripts(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(MINIMAL_SKILL_MD)

        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        assert entry.has_references is False
        assert entry.has_assets is False
        assert entry.has_scripts is False

    def test_has_scripts_detection(self, tmp_path: Path) -> None:
        """has_scripts is True when scripts/ subdir exists."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "scripts").mkdir()
        (skill_dir / "SKILL.md").write_text(MINIMAL_SKILL_MD)

        entry = parse_skill_frontmatter(skill_dir / "SKILL.md")
        assert entry is not None
        assert entry.has_scripts is True

    def test_unknown_fields_ignored(self, tmp_path: Path) -> None:
        """Lenient parsing: extra fields in frontmatter are silently ignored."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(FULL_SKILL_MD)

        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        # extra_unknown_field should not cause failure
        assert entry.name == "fastapi-endpoint"


# ---------------------------------------------------------------------------
# parse_skill_frontmatter — trigger conversion
# ---------------------------------------------------------------------------


class TestTriggerConversion:
    def test_deliverable_type_trigger(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\nname: t\ndescription: d\ntriggers:\n  - deliverable_type: api_endpoint\n---\n"
        )
        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        assert len(entry.triggers) == 1
        assert entry.triggers[0] == TriggerSpec(
            trigger_type=TriggerType.DELIVERABLE_TYPE, value="api_endpoint"
        )

    def test_file_pattern_trigger(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            '---\nname: t\ndescription: d\ntriggers:\n  - file_pattern: "*/routes/*.py"\n---\n'
        )
        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        assert entry.triggers[0].trigger_type == TriggerType.FILE_PATTERN
        assert entry.triggers[0].value == "*/routes/*.py"

    def test_tag_match_trigger(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\nname: t\ndescription: d\ntriggers:\n  - tag_match: security\n---\n"
        )
        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        assert entry.triggers[0].trigger_type == TriggerType.TAG_MATCH
        assert entry.triggers[0].value == "security"

    def test_explicit_trigger(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\nname: t\ndescription: d\ntriggers:\n  - explicit: my-skill\n---\n"
        )
        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        assert entry.triggers[0].trigger_type == TriggerType.EXPLICIT
        assert entry.triggers[0].value == "my-skill"

    def test_always_trigger_with_true(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: t\ndescription: d\ntriggers:\n  - always: true\n---\n")
        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        assert entry.triggers[0].trigger_type == TriggerType.ALWAYS
        assert entry.triggers[0].value == ""

    def test_always_trigger_with_null(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: t\ndescription: d\ntriggers:\n  - always:\n---\n")
        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        assert entry.triggers[0].trigger_type == TriggerType.ALWAYS
        assert entry.triggers[0].value == ""


# ---------------------------------------------------------------------------
# parse_skill_frontmatter — error cases
# ---------------------------------------------------------------------------


class TestParseErrors:
    def test_missing_name(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\ndescription: A skill\n---\nBody.\n")

        entry = parse_skill_frontmatter(skill_file)
        assert entry is None

    def test_missing_description(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: test\n---\nBody.\n")

        entry = parse_skill_frontmatter(skill_file)
        assert entry is None

    def test_empty_name(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text('---\nname: ""\ndescription: A skill\n---\nBody.\n')

        entry = parse_skill_frontmatter(skill_file)
        assert entry is None

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: [invalid yaml\n---\nBody.\n")

        entry = parse_skill_frontmatter(skill_file)
        assert entry is None

    def test_no_frontmatter_delimiters(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("Just some content without frontmatter.\n")

        entry = parse_skill_frontmatter(skill_file)
        assert entry is None

    def test_file_not_found(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent" / "SKILL.md"
        entry = parse_skill_frontmatter(missing)
        assert entry is None

    def test_frontmatter_not_a_mapping(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\n- just a list\n---\nBody.\n")

        entry = parse_skill_frontmatter(skill_file)
        assert entry is None

    def test_unknown_trigger_type_skipped(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\nname: t\ndescription: d\ntriggers:\n"
            "  - unknown_type: val\n  - deliverable_type: api\n---\n"
        )
        entry = parse_skill_frontmatter(skill_file)
        assert entry is not None
        assert len(entry.triggers) == 1
        assert entry.triggers[0].trigger_type == TriggerType.DELIVERABLE_TYPE


# ---------------------------------------------------------------------------
# validate_skill_frontmatter
# ---------------------------------------------------------------------------


class TestValidateSkillFrontmatter:
    def test_valid_minimal(self) -> None:
        errors = validate_skill_frontmatter({"name": "test", "description": "A test"})
        assert errors == []

    def test_valid_full(self) -> None:
        errors = validate_skill_frontmatter(
            {
                "name": "test",
                "description": "A test",
                "triggers": [{"deliverable_type": "api"}],
                "tags": ["api"],
                "applies_to": ["coder"],
                "priority": 10,
                "cascades": [{"reference": "other"}],
            }
        )
        assert errors == []

    def test_missing_name(self) -> None:
        errors = validate_skill_frontmatter({"description": "A test"})
        assert any("name" in e for e in errors)

    def test_missing_description(self) -> None:
        errors = validate_skill_frontmatter({"name": "test"})
        assert any("description" in e for e in errors)

    def test_empty_name(self) -> None:
        errors = validate_skill_frontmatter({"name": "", "description": "A test"})
        assert any("name" in e for e in errors)

    def test_empty_description(self) -> None:
        errors = validate_skill_frontmatter({"name": "test", "description": ""})
        assert any("description" in e for e in errors)

    def test_wrong_type_name(self) -> None:
        errors = validate_skill_frontmatter({"name": 123, "description": "A test"})
        assert any("name" in e and "string" in e for e in errors)

    def test_wrong_type_triggers(self) -> None:
        errors = validate_skill_frontmatter(
            {"name": "t", "description": "d", "triggers": "not a list"}
        )
        assert any("triggers" in e for e in errors)

    def test_wrong_type_tags(self) -> None:
        errors = validate_skill_frontmatter({"name": "t", "description": "d", "tags": "not a list"})
        assert any("tags" in e for e in errors)

    def test_wrong_type_priority(self) -> None:
        errors = validate_skill_frontmatter({"name": "t", "description": "d", "priority": "high"})
        assert any("priority" in e for e in errors)

    def test_unknown_fields_not_errors(self) -> None:
        """Unknown fields are allowed (lenient for third-party skills)."""
        errors = validate_skill_frontmatter(
            {"name": "t", "description": "d", "custom_field": "value"}
        )
        assert errors == []


# ---------------------------------------------------------------------------
# SkillEntry immutability
# ---------------------------------------------------------------------------


class TestSkillEntryImmutability:
    def test_frozen(self) -> None:
        entry = SkillEntry(name="test", description="A test skill")
        with pytest.raises(ValidationError):
            entry.name = "modified"  # type: ignore[misc]
