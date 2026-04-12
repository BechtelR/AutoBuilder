"""Tests for WorkflowRegistry -- scan, get, match, list, cache."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from app.lib.exceptions import NotFoundError
from app.workflows.registry import WorkflowRegistry
from tests.workflows.conftest import write_workflow

# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


class TestScan:
    def test_discovers_single_workflow(self, tmp_path: Path) -> None:
        write_workflow(tmp_path, "test-wf")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        assert len(registry.list_available()) == 1
        assert registry.list_available()[0].name == "test-wf"

    def test_discovers_multiple_workflows(self, tmp_path: Path) -> None:
        write_workflow(tmp_path, "alpha")
        write_workflow(tmp_path, "beta")
        write_workflow(tmp_path, "gamma")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        assert len(registry.list_available()) == 3

    def test_empty_directory(self, tmp_path: Path) -> None:
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        assert len(registry.list_available()) == 0

    def test_ignores_invalid_manifest(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        bad_dir = tmp_path / "bad-wf"
        bad_dir.mkdir()
        (bad_dir / "WORKFLOW.yaml").write_text("not: valid: yaml: {{", encoding="utf-8")
        write_workflow(tmp_path, "good-wf")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        assert len(registry.list_available()) == 1

    def test_ignores_manifest_missing_required_fields(self, tmp_path: Path) -> None:
        bad_dir = tmp_path / "incomplete"
        bad_dir.mkdir()
        (bad_dir / "WORKFLOW.yaml").write_text("name: incomplete\n", encoding="utf-8")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        assert len(registry.list_available()) == 0

    def test_rescan_clears_previous(self, tmp_path: Path) -> None:
        write_workflow(tmp_path, "first")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        assert len(registry.list_available()) == 1

        new_dir = tmp_path / "second-scan"
        new_dir.mkdir()
        write_workflow(new_dir, "second")
        registry2 = WorkflowRegistry(new_dir)
        registry2.scan()
        assert len(registry2.list_available()) == 1
        assert registry2.list_available()[0].name == "second"

    def test_stores_manifest_path(self, tmp_path: Path) -> None:
        wf_dir = write_workflow(tmp_path, "path-test")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        entry = registry.get("path-test")
        assert entry.path == wf_dir


# ---------------------------------------------------------------------------
# User-level override
# ---------------------------------------------------------------------------


class TestUserLevelOverride:
    def test_user_overrides_builtin(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        write_workflow(builtin, "shared", description="Built-in version")
        write_workflow(user, "shared", description="User version")
        registry = WorkflowRegistry(builtin, user)
        registry.scan()
        manifest = registry.get_manifest("shared")
        assert manifest.description == "User version"

    def test_user_additive(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        write_workflow(builtin, "builtin-only")
        write_workflow(user, "user-only")
        registry = WorkflowRegistry(builtin, user)
        registry.scan()
        assert len(registry.list_available()) == 2

    def test_user_dir_missing_no_error(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        write_workflow(builtin, "test-wf")
        registry = WorkflowRegistry(builtin, tmp_path / "nonexistent")
        registry.scan()
        assert len(registry.list_available()) == 1

    def test_user_dir_none(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        write_workflow(builtin, "test-wf")
        registry = WorkflowRegistry(builtin, None)
        registry.scan()
        assert len(registry.list_available()) == 1


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


class TestGet:
    def test_existing(self, tmp_path: Path) -> None:
        write_workflow(tmp_path, "exists")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        entry = registry.get("exists")
        assert entry.name == "exists"

    def test_missing_raises(self, tmp_path: Path) -> None:
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        with pytest.raises(NotFoundError):
            registry.get("nope")

    def test_get_manifest(self, tmp_path: Path) -> None:
        write_workflow(
            tmp_path,
            "manifest-test",
            stages=[{"name": "alpha", "description": "First"}],
        )
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        m = registry.get_manifest("manifest-test")
        assert len(m.stages) == 1


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------


class TestMatch:
    def test_keyword_match(self, tmp_path: Path) -> None:
        write_workflow(
            tmp_path,
            "builder",
            triggers=[{"keywords": ["build", "construct"]}],
        )
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        results = registry.match("I want to build something")
        assert len(results) == 1
        assert results[0].name == "builder"

    def test_explicit_match(self, tmp_path: Path) -> None:
        write_workflow(
            tmp_path,
            "my-wf",
            triggers=[{"explicit": "my-wf"}],
        )
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        results = registry.match("my-wf")
        assert len(results) == 1

    def test_explicit_takes_precedence(self, tmp_path: Path) -> None:
        write_workflow(
            tmp_path,
            "exact",
            triggers=[
                {"explicit": "build"},
                {"keywords": ["build"]},
            ],
        )
        write_workflow(
            tmp_path,
            "keyword",
            triggers=[{"keywords": ["build"]}],
        )
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        results = registry.match("build")
        assert len(results) == 1
        assert results[0].name == "exact"

    def test_no_match(self, tmp_path: Path) -> None:
        write_workflow(
            tmp_path,
            "test-wf",
            triggers=[{"keywords": ["code"]}],
        )
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        results = registry.match("unrelated request")
        assert len(results) == 0

    def test_multiple_keyword_matches(self, tmp_path: Path) -> None:
        write_workflow(
            tmp_path,
            "alpha",
            triggers=[{"keywords": ["build"]}],
        )
        write_workflow(
            tmp_path,
            "beta",
            triggers=[{"keywords": ["build"]}],
        )
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        results = registry.match("let's build")
        assert len(results) == 2

    def test_no_triggers_no_match(self, tmp_path: Path) -> None:
        write_workflow(tmp_path, "no-triggers")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        results = registry.match("anything")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# List available
# ---------------------------------------------------------------------------


class TestListAvailable:
    def test_sorted_by_name(self, tmp_path: Path) -> None:
        write_workflow(tmp_path, "charlie")
        write_workflow(tmp_path, "alpha")
        write_workflow(tmp_path, "bravo")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        names = [e.name for e in registry.list_available()]
        assert names == ["alpha", "bravo", "charlie"]

    def test_empty(self, tmp_path: Path) -> None:
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        assert registry.list_available() == []


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class TestCache:
    @pytest.mark.asyncio
    async def test_no_redis_save_noop(self, tmp_path: Path) -> None:
        write_workflow(tmp_path, "test-wf")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        await registry.save_to_cache()  # should not raise

    @pytest.mark.asyncio
    async def test_no_redis_load_returns_false(self, tmp_path: Path) -> None:
        registry = WorkflowRegistry(tmp_path)
        result = await registry.load_from_cache()
        assert result is False

    @pytest.mark.asyncio
    async def test_no_redis_invalidate_noop(self, tmp_path: Path) -> None:
        registry = WorkflowRegistry(tmp_path)
        await registry.invalidate_cache()  # should not raise
