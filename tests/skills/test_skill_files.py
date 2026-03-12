"""Tests that all shipped skill files have valid frontmatter."""

from pathlib import Path
from typing import cast

import pytest
import yaml

from app.skills.parser import parse_skill_frontmatter, validate_skill_frontmatter

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "skills"


def _find_all_skill_files() -> list[Path]:
    """Find all SKILL.md files in the skills directory."""
    return sorted(SKILLS_DIR.rglob("SKILL.md"))


class TestShippedSkills:
    def test_skill_files_exist(self) -> None:
        """All 17 shipped skills exist (7 domain + 4 authoring + 2 governance + 4 file-editing)."""
        files = _find_all_skill_files()
        assert len(files) >= 17, f"Expected >=17 skill files, found {len(files)}"

    @pytest.mark.parametrize("skill_path", _find_all_skill_files(), ids=lambda p: p.parent.name)
    def test_valid_frontmatter(self, skill_path: Path) -> None:
        """Each skill file has valid parseable frontmatter."""
        entry = parse_skill_frontmatter(skill_path)
        assert entry is not None, f"Failed to parse {skill_path}"
        assert entry.name, f"Missing name in {skill_path}"
        assert entry.description, f"Missing description in {skill_path}"

    @pytest.mark.parametrize("skill_path", _find_all_skill_files(), ids=lambda p: p.parent.name)
    def test_validates_clean(self, skill_path: Path) -> None:
        """Each skill passes validate_skill_frontmatter."""
        content = skill_path.read_text()
        parts = content.split("---", 2)
        if len(parts) >= 2:
            raw = yaml.safe_load(parts[1])
            if isinstance(raw, dict):
                frontmatter = cast("dict[str, object]", raw)
                errors = validate_skill_frontmatter(frontmatter)
                assert errors == [], f"Validation errors in {skill_path}: {errors}"

    @pytest.mark.parametrize("skill_path", _find_all_skill_files(), ids=lambda p: p.parent.name)
    def test_body_under_word_limit(self, skill_path: Path) -> None:
        """NFR-6.03: Each shipped skill body is under 3000 words."""
        content = skill_path.read_text()
        parts = content.split("---", 2)
        body = parts[2].strip() if len(parts) > 2 else ""
        word_count = len(body.split())
        assert word_count < 3000, (
            f"Skill {skill_path.parent.name} body has {word_count} words (>3000)"
        )

    @pytest.mark.parametrize("skill_path", _find_all_skill_files(), ids=lambda p: p.parent.name)
    def test_description_third_person(self, skill_path: Path) -> None:
        """FR-6.43: Each shipped skill description is written in third-person."""
        entry = parse_skill_frontmatter(skill_path)
        assert entry is not None
        desc_lower = entry.description.lower()
        # Third-person descriptions should not start with "Use", "Load", "You"
        # They should start with "This skill..." or similar third-person phrasing
        assert not desc_lower.startswith("you "), (
            f"Skill {entry.name} description starts with 'you' — use third-person"
        )
        assert not desc_lower.startswith("use "), (
            f"Skill {entry.name} description starts with 'use' — use third-person"
        )

    @pytest.mark.parametrize("skill_path", _find_all_skill_files(), ids=lambda p: p.parent.name)
    def test_has_triggers(self, skill_path: Path) -> None:
        """Each shipped skill has at least one trigger defined."""
        entry = parse_skill_frontmatter(skill_path)
        assert entry is not None
        assert len(entry.triggers) > 0, (
            f"Skill {entry.name} has no triggers — all shipped skills should have explicit triggers"
        )

    def test_file_editing_skills_have_scripts(self) -> None:
        """All 4 file-editing skills have scripts/ directories detected."""
        file_skills = [p for p in _find_all_skill_files() if "files/" in str(p)]
        assert len(file_skills) == 4, f"Expected 4 file-editing skills, found {len(file_skills)}"
        for skill_path in file_skills:
            entry = parse_skill_frontmatter(skill_path)
            assert entry is not None
            assert entry.has_scripts, f"Skill {entry.name} should have has_scripts=True"
