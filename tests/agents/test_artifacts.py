"""Tests for ArtifactStore — real PostgreSQL + real filesystem (tmp_path)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.agents.artifacts import ArtifactStore
from app.db.models import Artifact
from tests.conftest import require_infra


@require_infra
class TestArtifactStore:
    @pytest.mark.asyncio
    async def test_save_and_load(self, engine: AsyncEngine, tmp_path: Path) -> None:
        """save() writes file + DB record; load() returns exact bytes."""
        factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)

        entity_id = uuid.uuid4()
        project_id = uuid.uuid4()
        content = b"print('hello')"

        artifact_id = await store.save(
            entity_type="deliverable",
            entity_id=entity_id,
            filename="output.py",
            content=content,
            content_type="text/x-python",
            project_id=project_id,
        )

        # Verify DB record
        async with factory() as db:
            artifact = (
                await db.execute(select(Artifact).where(Artifact.id == artifact_id))
            ).scalar_one()
            assert artifact.content_type == "text/x-python"
            assert artifact.size_bytes == len(content)
            assert artifact.entity_type == "deliverable"
            assert artifact.entity_id == entity_id

        # Verify filesystem content matches
        loaded = await store.load(artifact_id)
        assert loaded == content

    @pytest.mark.asyncio
    async def test_save_without_project_id(self, engine: AsyncEngine, tmp_path: Path) -> None:
        """save() without project_id stores under {entity_type}/{entity_id}/."""
        factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)

        entity_id = uuid.uuid4()
        content = b"# report"

        artifact_id = await store.save(
            entity_type="taskgroup_execution",
            entity_id=entity_id,
            filename="report.md",
            content=content,
            content_type="text/markdown",
        )

        loaded = await store.load(artifact_id)
        assert loaded == content

        # Path should NOT contain a project UUID segment
        async with factory() as db:
            artifact = (
                await db.execute(select(Artifact).where(Artifact.id == artifact_id))
            ).scalar_one()
            stored_path = Path(artifact.path)
            assert stored_path.name == "report.md"
            # No project UUID in path — entity_type is directly under artifacts_root
            assert stored_path.parts[-3] == "taskgroup_execution"

    @pytest.mark.asyncio
    async def test_list_for_entity(self, engine: AsyncEngine, tmp_path: Path) -> None:
        """list_for_entity() returns all artifacts for an entity, ordered by created_at."""
        factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)

        entity_id = uuid.uuid4()
        other_entity_id = uuid.uuid4()

        await store.save(
            entity_type="deliverable",
            entity_id=entity_id,
            filename="a.py",
            content=b"# a",
            content_type="text/x-python",
        )
        await store.save(
            entity_type="deliverable",
            entity_id=entity_id,
            filename="b.py",
            content=b"# b",
            content_type="text/x-python",
        )
        # Different entity — should not appear in results
        await store.save(
            entity_type="deliverable",
            entity_id=other_entity_id,
            filename="other.py",
            content=b"# other",
            content_type="text/x-python",
        )

        results = await store.list_for_entity("deliverable", entity_id)

        assert len(results) == 2
        filenames = {Path(r["path"]).name for r in results}  # type: ignore[arg-type]
        assert filenames == {"a.py", "b.py"}

        # Verify all required keys are present
        for r in results:
            assert "id" in r
            assert "entity_type" in r
            assert "entity_id" in r
            assert "path" in r
            assert "content_type" in r
            assert "size_bytes" in r
            assert "created_at" in r
            assert r["entity_type"] == "deliverable"
            assert r["entity_id"] == str(entity_id)

    @pytest.mark.asyncio
    async def test_list_for_entity_empty(self, engine: AsyncEngine, tmp_path: Path) -> None:
        """list_for_entity() returns empty list when no artifacts exist."""
        factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)

        results = await store.list_for_entity("deliverable", uuid.uuid4())
        assert results == []

    @pytest.mark.asyncio
    async def test_load_nonexistent_artifact(self, engine: AsyncEngine, tmp_path: Path) -> None:
        """load() returns None for an artifact ID that doesn't exist in DB."""
        factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)

        result = await store.load(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_load_missing_file(self, engine: AsyncEngine, tmp_path: Path) -> None:
        """load() returns None when DB record exists but file has been deleted."""
        factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)

        entity_id = uuid.uuid4()
        artifact_id = await store.save(
            entity_type="deliverable",
            entity_id=entity_id,
            filename="gone.py",
            content=b"data",
            content_type="text/x-python",
        )

        # Delete the file manually
        async with factory() as db:
            artifact = (
                await db.execute(select(Artifact).where(Artifact.id == artifact_id))
            ).scalar_one()
            Path(artifact.path).unlink()

        result = await store.load(artifact_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_save_creates_nested_directories(
        self, engine: AsyncEngine, tmp_path: Path
    ) -> None:
        """save() creates all parent directories automatically."""
        factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)

        project_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        artifact_id = await store.save(
            entity_type="deliverable",
            entity_id=entity_id,
            filename="nested.txt",
            content=b"hello",
            content_type="text/plain",
            project_id=project_id,
        )

        expected_dir = tmp_path / str(project_id) / "deliverable" / str(entity_id)
        assert expected_dir.is_dir()
        assert (expected_dir / "nested.txt").exists()

        loaded = await store.load(artifact_id)
        assert loaded == b"hello"

    @pytest.mark.asyncio
    async def test_save_records_correct_size(self, engine: AsyncEngine, tmp_path: Path) -> None:
        """size_bytes in DB matches actual content length."""
        factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)

        content = b"x" * 1024  # 1 KiB
        artifact_id = await store.save(
            entity_type="deliverable",
            entity_id=uuid.uuid4(),
            filename="large.bin",
            content=content,
            content_type="application/octet-stream",
        )

        async with factory() as db:
            artifact = (
                await db.execute(select(Artifact).where(Artifact.id == artifact_id))
            ).scalar_one()
            assert artifact.size_bytes == 1024

    @pytest.mark.asyncio
    async def test_arbitrary_file_types(self, engine: AsyncEngine, tmp_path: Path) -> None:
        """Arbitrary file types (code, binary, markdown) are supported."""
        factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        store = ArtifactStore(db_session_factory=factory, artifacts_root=tmp_path)

        entity_id = uuid.uuid4()
        cases: list[tuple[str, bytes, str]] = [
            ("test_result.json", b'{"passed": true}', "application/json"),
            ("report.md", b"# Report\n\nAll good.", "text/markdown"),
            ("artifact.bin", bytes(range(256)), "application/octet-stream"),
        ]

        for filename, content, content_type in cases:
            artifact_id = await store.save(
                entity_type="deliverable",
                entity_id=entity_id,
                filename=filename,
                content=content,
                content_type=content_type,
            )
            loaded = await store.load(artifact_id)
            assert loaded == content, f"Content mismatch for {filename}"
