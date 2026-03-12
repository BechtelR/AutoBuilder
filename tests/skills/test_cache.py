"""Tests for SkillLibrary Redis cache methods.

Uses real Redis — skipped when unavailable.
Degraded-path tests use broken connection URLs, not mock objects.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from arq.connections import ArqRedis, create_pool

from app.config import parse_redis_settings
from app.skills.library import SkillLibrary
from tests.conftest import TEST_REDIS_URL, require_redis

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SKILL_CACHE_PREFIX = "autobuilder:skill_index:"


@pytest_asyncio.fixture
async def arq_redis() -> AsyncIterator[ArqRedis]:
    """Yield a real ArqRedis connection for cache tests."""
    pool: ArqRedis = await create_pool(parse_redis_settings(TEST_REDIS_URL))
    yield pool
    # Clean up skill cache keys
    keys: list[bytes] = await pool.keys(f"{_SKILL_CACHE_PREFIX}*")  # type: ignore[assignment]
    if keys:
        await pool.delete(*keys)
    await pool.aclose()


def _write_skill(base_dir: Path, name: str, *, description: str = "Test skill") -> Path:
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nBody.",
        encoding="utf-8",
    )
    return skill_dir / "SKILL.md"


def _make_library(tmp_path: Path, redis: ArqRedis | None = None) -> SkillLibrary:
    global_dir = tmp_path / "global"
    global_dir.mkdir(exist_ok=True)
    return SkillLibrary(global_dir=global_dir, redis=redis)


# ---------------------------------------------------------------------------
# save_to_cache
# ---------------------------------------------------------------------------


@require_redis
class TestSaveToCache:
    async def test_save_persists_to_redis(self, tmp_path: Path, arq_redis: ArqRedis) -> None:
        """save_to_cache() serializes index to Redis."""
        lib = _make_library(tmp_path, arq_redis)
        _write_skill(tmp_path / "global", "alpha")
        lib.scan()

        await lib.save_to_cache()

        raw = await arq_redis.get(lib._cache_key())  # type: ignore[reportPrivateUsage]
        assert raw is not None
        import json

        data = json.loads(raw)
        assert "alpha" in data["index"]
        assert "mtimes" in data

    async def test_save_with_no_skills(self, tmp_path: Path, arq_redis: ArqRedis) -> None:
        """save_to_cache() with empty index still writes to Redis."""
        lib = _make_library(tmp_path, arq_redis)
        lib.scan()

        await lib.save_to_cache()

        raw = await arq_redis.get(lib._cache_key())  # type: ignore[reportPrivateUsage]
        assert raw is not None


# ---------------------------------------------------------------------------
# load_from_cache
# ---------------------------------------------------------------------------


@require_redis
class TestLoadFromCache:
    async def test_cache_hit_returns_true(self, tmp_path: Path, arq_redis: ArqRedis) -> None:
        """load_from_cache() returns True on a valid cache hit."""
        # Save first
        lib = _make_library(tmp_path, arq_redis)
        _write_skill(tmp_path / "global", "alpha", description="Alpha skill")
        lib.scan()
        await lib.save_to_cache()

        # Load into a fresh library
        lib2 = _make_library(tmp_path, arq_redis)
        result = await lib2.load_from_cache()

        assert result is True
        assert "alpha" in lib2.get_index()
        assert lib2.get_index()["alpha"].description == "Alpha skill"

    async def test_cache_miss_returns_false(self, tmp_path: Path, arq_redis: ArqRedis) -> None:
        """load_from_cache() returns False when Redis has no entry."""
        lib = _make_library(tmp_path, arq_redis)

        result = await lib.load_from_cache()

        assert result is False
        assert lib.get_index() == {}

    async def test_mtimes_restored(self, tmp_path: Path, arq_redis: ArqRedis) -> None:
        """load_from_cache() restores file modification times."""
        lib = _make_library(tmp_path, arq_redis)
        _write_skill(tmp_path / "global", "alpha")
        lib.scan()
        await lib.save_to_cache()

        # Load into fresh library and verify mtimes restored
        lib2 = _make_library(tmp_path, arq_redis)
        await lib2.load_from_cache()

        assert len(lib2._file_mtimes) > 0  # type: ignore[reportPrivateUsage]
        for path_str, mtime in lib2._file_mtimes.items():  # type: ignore[reportPrivateUsage]
            assert isinstance(mtime, float)
            assert Path(path_str).name == "SKILL.md"


# ---------------------------------------------------------------------------
# invalidate_cache
# ---------------------------------------------------------------------------


@require_redis
class TestInvalidateCache:
    async def test_invalidate_removes_key(self, tmp_path: Path, arq_redis: ArqRedis) -> None:
        """invalidate_cache() removes the cached index from Redis."""
        lib = _make_library(tmp_path, arq_redis)
        _write_skill(tmp_path / "global", "alpha")
        lib.scan()
        await lib.save_to_cache()

        # Verify key exists
        assert await arq_redis.get(lib._cache_key()) is not None  # type: ignore[reportPrivateUsage]

        await lib.invalidate_cache()

        # Verify key is gone
        assert await arq_redis.get(lib._cache_key()) is None  # type: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# Redis is None — all cache methods are no-ops
# ---------------------------------------------------------------------------


class TestNoRedis:
    async def test_save_noop_when_no_redis(self, tmp_path: Path) -> None:
        lib = _make_library(tmp_path)
        await lib.save_to_cache()  # must not raise

    async def test_load_returns_false_when_no_redis(self, tmp_path: Path) -> None:
        lib = _make_library(tmp_path)
        result = await lib.load_from_cache()
        assert result is False

    async def test_invalidate_noop_when_no_redis(self, tmp_path: Path) -> None:
        lib = _make_library(tmp_path)
        await lib.invalidate_cache()  # must not raise


# ---------------------------------------------------------------------------
# Redis error — degraded path with broken connection URL
# ---------------------------------------------------------------------------


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
class TestRedisErrors:
    """Degraded-path tests use a broken connection URL, not mock objects."""

    @pytest_asyncio.fixture
    async def broken_redis(self) -> AsyncIterator[ArqRedis]:
        """ArqRedis connected to a non-listening port — all ops will fail."""
        pool = ArqRedis(host="localhost", port=59999, socket_connect_timeout=0.5)
        yield pool
        with contextlib.suppress(Exception):
            await pool.aclose()

    async def test_save_error_logs_warning(
        self, tmp_path: Path, broken_redis: ArqRedis, caplog: pytest.LogCaptureFixture
    ) -> None:
        """save_to_cache() logs warning and does not propagate Redis errors."""
        lib = _make_library(tmp_path, broken_redis)

        with caplog.at_level("WARNING", logger="app.skills.library"):
            await lib.save_to_cache()  # must not raise

        assert any("Failed to save" in r.message for r in caplog.records)

    async def test_load_error_logs_warning(
        self, tmp_path: Path, broken_redis: ArqRedis, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load_from_cache() logs warning and returns False on Redis error."""
        lib = _make_library(tmp_path, broken_redis)

        with caplog.at_level("WARNING", logger="app.skills.library"):
            result = await lib.load_from_cache()

        assert result is False
        assert any("Failed to load" in r.message for r in caplog.records)

    async def test_invalidate_error_logs_warning(
        self, tmp_path: Path, broken_redis: ArqRedis, caplog: pytest.LogCaptureFixture
    ) -> None:
        """invalidate_cache() logs warning and does not propagate Redis errors."""
        lib = _make_library(tmp_path, broken_redis)

        with caplog.at_level("WARNING", logger="app.skills.library"):
            await lib.invalidate_cache()  # must not raise

        assert any("Failed to invalidate" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# check_for_changes
# ---------------------------------------------------------------------------


class TestCheckForChanges:
    def test_no_changes_returns_false(self, tmp_path: Path) -> None:
        """check_for_changes() returns False when nothing has changed."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "alpha")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        assert lib.check_for_changes() is False

    def test_modified_file_returns_true(self, tmp_path: Path) -> None:
        """check_for_changes() returns True when a file's mtime changes."""
        global_dir = tmp_path / "global"
        skill_path = _write_skill(global_dir, "alpha")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        # Manually corrupt the stored mtime to simulate a stale cache
        lib._file_mtimes[str(skill_path)] = 0.0  # type: ignore[reportPrivateUsage]

        assert lib.check_for_changes() is True

    def test_deleted_file_returns_true(self, tmp_path: Path) -> None:
        """check_for_changes() returns True when a tracked file is deleted."""
        global_dir = tmp_path / "global"
        skill_path = _write_skill(global_dir, "alpha")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        skill_path.unlink()

        assert lib.check_for_changes() is True

    def test_new_file_returns_true(self, tmp_path: Path) -> None:
        """check_for_changes() returns True when a new SKILL.md appears."""
        global_dir = tmp_path / "global"
        _write_skill(global_dir, "alpha")

        lib = SkillLibrary(global_dir=global_dir)
        lib.scan()

        # Add a second skill after scanning
        _write_skill(global_dir, "beta")

        assert lib.check_for_changes() is True

    def test_empty_index_no_changes(self, tmp_path: Path) -> None:
        """check_for_changes() returns False for empty index with empty directory."""
        lib = SkillLibrary(global_dir=tmp_path / "empty")
        lib.scan()

        assert lib.check_for_changes() is False


# ---------------------------------------------------------------------------
# Cache key determinism
# ---------------------------------------------------------------------------


class TestCacheKey:
    def test_key_deterministic(self, tmp_path: Path) -> None:
        """_cache_key() returns the same key for the same directory paths."""
        global_dir = tmp_path / "global"
        lib1 = SkillLibrary(global_dir=global_dir)
        lib2 = SkillLibrary(global_dir=global_dir)

        assert lib1._cache_key() == lib2._cache_key()  # type: ignore[reportPrivateUsage]

    def test_key_differs_by_global_dir(self, tmp_path: Path) -> None:
        """Different global dirs produce different cache keys."""
        lib1 = SkillLibrary(global_dir=tmp_path / "a")
        lib2 = SkillLibrary(global_dir=tmp_path / "b")

        assert lib1._cache_key() != lib2._cache_key()  # type: ignore[reportPrivateUsage]

    def test_key_differs_by_project_dir(self, tmp_path: Path) -> None:
        """Different project dirs produce different cache keys."""
        global_dir = tmp_path / "global"
        lib1 = SkillLibrary(global_dir=global_dir, project_dir=tmp_path / "proj_a")
        lib2 = SkillLibrary(global_dir=global_dir, project_dir=tmp_path / "proj_b")

        assert lib1._cache_key() != lib2._cache_key()  # type: ignore[reportPrivateUsage]

    def test_key_contains_prefix(self, tmp_path: Path) -> None:
        """Cache key uses the expected prefix."""
        lib = SkillLibrary(global_dir=tmp_path / "global")
        assert lib._cache_key().startswith("autobuilder:skill_index:")  # type: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# Roundtrip: save_to_cache → load_from_cache
# ---------------------------------------------------------------------------


@require_redis
class TestRoundtrip:
    async def test_roundtrip_restores_equivalent_index(
        self, tmp_path: Path, arq_redis: ArqRedis
    ) -> None:
        """save_to_cache() followed by load_from_cache() restores equivalent index."""
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        _write_skill(global_dir, "alpha")
        _write_skill(global_dir, "beta")

        lib_save = SkillLibrary(global_dir=global_dir, redis=arq_redis)
        lib_save.scan()
        await lib_save.save_to_cache()

        # Load into a fresh library
        lib_load = SkillLibrary(global_dir=global_dir, redis=arq_redis)
        result = await lib_load.load_from_cache()

        assert result is True
        loaded_index = lib_load.get_index()
        assert set(loaded_index.keys()) == {"alpha", "beta"}
        assert loaded_index["alpha"].description == "Test skill"
        assert loaded_index["beta"].description == "Test skill"
