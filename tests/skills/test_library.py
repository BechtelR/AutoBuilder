"""Tests for SkillLibrary: scan, match, load, cascade resolution."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.agents.protocols import SkillContent, SkillMatchContext
from app.skills.library import SkillEntry, SkillLibrary

if TYPE_CHECKING:
    import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_skill(
    base_dir: Path,
    name: str,
    *,
    description: str = "A test skill",
    triggers: str = "",
    tags: str = "",
    priority: int = 0,
    cascades: str = "",
    body: str = "Skill body content.",
    dir_name: str | None = None,
    create_references: bool = False,
    create_assets: bool = False,
) -> Path:
    """Write a SKILL.md file into base_dir/<dir_name>/SKILL.md."""
    folder_name = dir_name if dir_name is not None else name
    skill_dir = base_dir / folder_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
    ]
    if triggers:
        lines.append(f"triggers:\n{triggers}")
    if tags:
        lines.append(f"tags: {tags}")
    if priority:
        lines.append(f"priority: {priority}")
    if cascades:
        lines.append(f"cascades:\n{cascades}")
    lines.append("---")
    lines.append("")
    lines.append(body)

    (skill_dir / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")

    if create_references:
        (skill_dir / "references").mkdir(exist_ok=True)
    if create_assets:
        (skill_dir / "assets").mkdir(exist_ok=True)

    return skill_dir


# ---------------------------------------------------------------------------
# scan() tests
# ---------------------------------------------------------------------------


class TestScan:
    """Tests for SkillLibrary.scan()."""

    def test_scan_builds_index(self, tmp_path: Path) -> None:
        """scan() finds SKILL.md files and populates the index."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "alpha", description="Alpha skill")
        _write_skill(global_dir, "beta", description="Beta skill")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        index = lib.get_index()
        assert len(index) == 2
        assert "alpha" in index
        assert "beta" in index
        assert index["alpha"].description == "Alpha skill"

    def test_scan_clears_previous_index(self, tmp_path: Path) -> None:
        """Repeated scan() calls reset the index."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "alpha")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()
        assert len(lib.get_index()) == 1

        # Remove the skill and rescan
        (global_dir / "alpha" / "SKILL.md").unlink()
        lib.scan()
        assert len(lib.get_index()) == 0

    def test_scan_nonexistent_global_dir(self, tmp_path: Path) -> None:
        """scan() with non-existent global dir produces empty index."""
        lib = SkillLibrary(global_dir=tmp_path / "nonexistent")
        lib.scan()
        assert lib.get_index() == {}


class TestTwoTierScan:
    """Tests for two-tier (global + project-local) scanning."""

    def test_project_overrides_global(self, tmp_path: Path) -> None:
        """FR-6.18: Project-local skill overrides global by name."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        _write_skill(global_dir, "shared", description="Global version")
        _write_skill(project_dir, "shared", description="Project version")

        lib = SkillLibrary(global_dir=global_dir, project_dir=project_dir)
        lib.scan()

        index = lib.get_index()
        assert len(index) == 1
        assert index["shared"].description == "Project version"

    def test_project_additive(self, tmp_path: Path) -> None:
        """FR-6.19: Unique project-local skills are additive."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        _write_skill(global_dir, "alpha", description="Global alpha")
        _write_skill(project_dir, "beta", description="Project beta")

        lib = SkillLibrary(global_dir=global_dir, project_dir=project_dir)
        lib.scan()

        index = lib.get_index()
        assert len(index) == 2
        assert "alpha" in index
        assert "beta" in index

    def test_no_project_dir(self, tmp_path: Path) -> None:
        """FR-6.20: No project dir — global only, no errors."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "alpha")

        lib = SkillLibrary(global_dir=global_dir, project_dir=None)
        lib.scan()

        assert len(lib.get_index()) == 1

    def test_project_dir_missing(self, tmp_path: Path) -> None:
        """Project dir configured but doesn't exist — global only."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "alpha")

        lib = SkillLibrary(
            global_dir=global_dir,
            project_dir=tmp_path / "nonexistent",
        )
        lib.scan()

        assert len(lib.get_index()) == 1

    def test_project_override_logged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """FR-6.21: Project-local override is logged."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        _write_skill(global_dir, "shared")
        _write_skill(project_dir, "shared")

        lib = SkillLibrary(global_dir=global_dir, project_dir=project_dir)
        with caplog.at_level("INFO", logger="app.skills.library"):
            lib.scan()

        assert any("overrides previous" in r.message for r in caplog.records)


class TestDuplicateAndMismatch:
    """Tests for duplicate names and name/directory mismatches."""

    def test_duplicate_same_scope_first_wins(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """FR-6.06: Duplicate name in same scope — first wins with warning."""
        global_dir = tmp_path / "global"
        # Create two directories with different dir names but same skill name
        dir_a = global_dir / "aaa"
        dir_a.mkdir(parents=True)
        (dir_a / "SKILL.md").write_text(
            "---\nname: dupe\ndescription: First\n---\nBody A",
            encoding="utf-8",
        )
        dir_b = global_dir / "zzz"
        dir_b.mkdir(parents=True)
        (dir_b / "SKILL.md").write_text(
            "---\nname: dupe\ndescription: Second\n---\nBody B",
            encoding="utf-8",
        )

        lib = SkillLibrary(global_dir=global_dir)
        with caplog.at_level("WARNING", logger="app.skills.library"):
            lib.scan()

        index = lib.get_index()
        assert len(index) == 1
        # Sorted rglob: aaa/ before zzz/, so first found wins
        assert index["dupe"].description == "First"
        assert any("Duplicate skill name" in r.message for r in caplog.records)

    def test_name_directory_mismatch_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """FR-6.04: Name != directory name logs warning, frontmatter name used."""
        global_dir = tmp_path / "global"
        _write_skill(
            global_dir,
            "actual-name",
            dir_name="different-directory",
            description="Mismatch skill",
        )

        lib = SkillLibrary(global_dir=global_dir)
        with caplog.at_level("WARNING", logger="app.skills.library"):
            lib.scan()

        index = lib.get_index()
        assert "actual-name" in index
        assert "different-directory" not in index
        assert any("does not match directory" in r.message for r in caplog.records)


class TestReferencesAndAssets:
    """FR-6.05: has_references and has_assets detection."""

    def test_references_detected(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "with-refs", create_references=True)

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        assert lib.get_index()["with-refs"].has_references is True
        assert lib.get_index()["with-refs"].has_assets is False

    def test_assets_detected(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "with-assets", create_assets=True)

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        assert lib.get_index()["with-assets"].has_assets is True
        assert lib.get_index()["with-assets"].has_references is False

    def test_both_detected(self, tmp_path: Path) -> None:
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "with-both", create_references=True, create_assets=True)

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        entry = lib.get_index()["with-both"]
        assert entry.has_references is True
        assert entry.has_assets is True


# ---------------------------------------------------------------------------
# match() tests
# ---------------------------------------------------------------------------


class TestMatch:
    """Tests for SkillLibrary.match()."""

    def test_trigger_match(self, tmp_path: Path) -> None:
        """Skills with matching triggers are returned."""
        global_dir = tmp_path / "global"
        _write_skill(
            global_dir,
            "api-skill",
            description="API skill",
            triggers="  - deliverable_type: api_endpoint",
        )
        _write_skill(
            global_dir,
            "other-skill",
            description="Other skill",
            triggers="  - deliverable_type: cli_command",
        )

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        ctx = SkillMatchContext(deliverable_type="api_endpoint")
        matched = lib.match(ctx)

        assert len(matched) == 1
        assert matched[0].name == "api-skill"

    def test_always_trigger(self, tmp_path: Path) -> None:
        """Always trigger matches any context."""
        global_dir = tmp_path / "global"
        _write_skill(
            global_dir,
            "universal",
            description="Always applies",
            triggers="  - always: true",
        )

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        matched = lib.match(SkillMatchContext())
        assert len(matched) == 1
        assert matched[0].name == "universal"

    def test_keyword_fallback(self, tmp_path: Path) -> None:
        """FR-6.15: Skills without triggers use description keyword fallback."""
        global_dir = tmp_path / "global"
        _write_skill(
            global_dir,
            "python-testing",
            description="Python testing integration validation framework",
        )

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        ctx = SkillMatchContext(
            tags=["python", "testing", "integration"],
        )
        matched = lib.match(ctx)

        assert len(matched) == 1
        assert matched[0].name == "python-testing"

    def test_no_match(self, tmp_path: Path) -> None:
        """FR-6.14: No match returns empty list."""
        global_dir = tmp_path / "global"
        _write_skill(
            global_dir,
            "api-skill",
            triggers="  - deliverable_type: api_endpoint",
        )

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        matched = lib.match(SkillMatchContext(deliverable_type="cli_command"))
        assert matched == []

    def test_sort_priority_desc_name_asc(self, tmp_path: Path) -> None:
        """FR-6.13: Results sorted by priority desc, then name asc."""
        global_dir = tmp_path / "global"
        _write_skill(
            global_dir,
            "beta",
            triggers="  - always: true",
            priority=5,
        )
        _write_skill(
            global_dir,
            "alpha",
            triggers="  - always: true",
            priority=10,
        )
        _write_skill(
            global_dir,
            "gamma",
            triggers="  - always: true",
            priority=5,
        )

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        matched = lib.match(SkillMatchContext())
        names = [e.name for e in matched]
        # alpha (priority 10), then beta/gamma (priority 5) alphabetical
        assert names == ["alpha", "beta", "gamma"]

    def test_empty_index(self, tmp_path: Path) -> None:
        """match() on empty index returns empty."""
        lib = SkillLibrary(global_dir=tmp_path / "empty")
        lib.scan()
        assert lib.match(SkillMatchContext()) == []


# ---------------------------------------------------------------------------
# load() tests
# ---------------------------------------------------------------------------


class TestLoad:
    """Tests for SkillLibrary.load()."""

    def test_load_body(self, tmp_path: Path) -> None:
        """load() extracts body below frontmatter."""
        global_dir = tmp_path / "global"
        _write_skill(
            global_dir,
            "loadable",
            body="## Section\n\nParagraph content here.",
        )

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        entry = lib.get_index()["loadable"]
        content = lib.load(entry)

        assert isinstance(content, SkillContent)
        assert content.entry is entry
        assert "## Section" in content.content
        assert "Paragraph content here." in content.content

    def test_load_no_path(self) -> None:
        """load() with None path returns empty content."""
        entry = SkillEntry(name="orphan", description="No path", path=None)
        lib = SkillLibrary(global_dir=Path("/nonexistent"))
        content = lib.load(entry)
        assert content.content == ""

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """load() with deleted file returns empty content."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "transient")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        entry = lib.get_index()["transient"]
        # Delete the file after scanning
        assert entry.path is not None
        entry.path.unlink()

        content = lib.load(entry)
        assert content.content == ""

    def test_load_word_count_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """NFR-6.03: Body exceeding 3000 words triggers warning."""
        global_dir = tmp_path / "global"
        long_body = " ".join(["word"] * 3500)
        _write_skill(global_dir, "verbose", body=long_body)

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        entry = lib.get_index()["verbose"]
        with caplog.at_level("WARNING", logger="app.skills.library"):
            lib.load(entry)

        assert any(">3000" in r.message for r in caplog.records)

    def test_load_under_word_limit_no_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Body under 3000 words does not trigger warning."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "short", body="Short body.")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        entry = lib.get_index()["short"]
        with caplog.at_level("WARNING", logger="app.skills.library"):
            lib.load(entry)

        assert not any(">3000" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# resolve_cascades() tests
# ---------------------------------------------------------------------------


class TestResolveCascades:
    """Tests for SkillLibrary.resolve_cascades()."""

    def test_simple_cascade(self, tmp_path: Path) -> None:
        """Single cascade dependency resolved."""
        global_dir = tmp_path / "global"
        _write_skill(
            global_dir,
            "primary",
            cascades="  - reference: helper",
        )
        _write_skill(global_dir, "helper")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        primary = lib.get_index()["primary"]
        resolved = lib.resolve_cascades([primary])

        names = {e.name for e in resolved}
        assert names == {"primary", "helper"}

    def test_transitive_cascade(self, tmp_path: Path) -> None:
        """FR-6.23: Transitive cascade resolution."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "a", cascades="  - reference: b")
        _write_skill(global_dir, "b", cascades="  - reference: c")
        _write_skill(global_dir, "c")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        resolved = lib.resolve_cascades([lib.get_index()["a"]])
        names = [e.name for e in resolved]
        assert "a" in names
        assert "b" in names
        assert "c" in names

    def test_cycle_detection(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """FR-6.24: Cascade cycle does not loop forever."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "x", cascades="  - reference: y")
        _write_skill(global_dir, "y", cascades="  - reference: x")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        with caplog.at_level("DEBUG", logger="app.skills.library"):
            resolved = lib.resolve_cascades([lib.get_index()["x"]])

        names = {e.name for e in resolved}
        assert names == {"x", "y"}
        assert any("Cascade skip" in r.message for r in caplog.records)

    def test_missing_cascade_reference(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """FR-6.25: Missing cascade reference logged as warning."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "lonely", cascades="  - reference: ghost")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        with caplog.at_level("WARNING", logger="app.skills.library"):
            resolved = lib.resolve_cascades([lib.get_index()["lonely"]])

        assert len(resolved) == 1
        assert resolved[0].name == "lonely"
        assert any("not found in index" in r.message for r in caplog.records)

    def test_no_cascades(self, tmp_path: Path) -> None:
        """Skills without cascades return unchanged list."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "standalone")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        entry = lib.get_index()["standalone"]
        resolved = lib.resolve_cascades([entry])
        assert len(resolved) == 1
        assert resolved[0].name == "standalone"


# ---------------------------------------------------------------------------
# get_index() tests
# ---------------------------------------------------------------------------


class TestGetIndex:
    """Tests for SkillLibrary.get_index()."""

    def test_returns_copy(self, tmp_path: Path) -> None:
        """get_index() returns a copy, not the internal dict."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "alpha")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        index_copy = lib.get_index()
        index_copy.clear()

        # Internal index unchanged
        assert len(lib.get_index()) == 1
