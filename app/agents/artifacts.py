"""Persistent artifact storage — filesystem content with DB metadata.

Content stored at: {artifacts_root}/{project_id}/{entity_type}/{entity_id}/{filename}
  or without project: {artifacts_root}/{entity_type}/{entity_id}/{filename}
Metadata stored in: artifacts DB table (polymorphic entity_type + entity_id)
"""

from __future__ import annotations

import asyncio
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.db.models import Artifact
from app.lib.logging import get_logger

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = get_logger("agents.artifacts")

DEFAULT_ARTIFACTS_ROOT = Path("artifacts")


class ArtifactStore:
    """Persistent artifact storage with filesystem content and DB metadata."""

    def __init__(
        self,
        db_session_factory: async_sessionmaker[AsyncSession],
        artifacts_root: Path = DEFAULT_ARTIFACTS_ROOT,
    ) -> None:
        self._db_session_factory: async_sessionmaker[AsyncSession] = db_session_factory
        self._artifacts_root = artifacts_root

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Extract bare filename, rejecting path traversal attempts."""
        safe_name = PurePosixPath(filename).name
        if not safe_name or safe_name in (".", ".."):
            msg = f"Invalid artifact filename: {filename!r}"
            raise ValueError(msg)
        return safe_name

    @staticmethod
    def _sanitize_entity_type(entity_type: str) -> str:
        """Validate entity_type is a simple identifier, rejecting path traversal."""
        if not entity_type or "/" in entity_type or "\\" in entity_type or ".." in entity_type:
            msg = f"Invalid entity_type: {entity_type!r}"
            raise ValueError(msg)
        return entity_type

    def _validate_path_containment(self, path: Path) -> None:
        """Ensure resolved path is under _artifacts_root. Prevents directory escape."""
        resolved = path.resolve()
        root_resolved = self._artifacts_root.resolve()
        if not str(resolved).startswith(str(root_resolved) + "/") and resolved != root_resolved:
            msg = f"Path {path} escapes artifacts root {self._artifacts_root}"
            raise ValueError(msg)

    async def save(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        filename: str,
        content: bytes,
        content_type: str,
        *,
        project_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        """Save artifact content to filesystem and metadata to DB.

        Returns the artifact record ID.
        """
        safe_filename = self._sanitize_filename(filename)
        safe_entity_type = self._sanitize_entity_type(entity_type)

        if project_id is not None:
            dir_path = self._artifacts_root / str(project_id) / safe_entity_type / str(entity_id)
        else:
            dir_path = self._artifacts_root / safe_entity_type / str(entity_id)

        self._validate_path_containment(dir_path)
        file_path = dir_path / safe_filename

        artifact = Artifact(
            entity_type=entity_type,
            entity_id=entity_id,
            path=str(file_path),
            content_type=content_type,
            size_bytes=len(content),
        )
        async with self._db_session_factory() as db:
            db.add(artifact)
            await db.commit()
            await db.refresh(artifact)

        # Write file AFTER DB commit succeeds — avoids orphaned files on DB failure.
        # If the file write fails, load() gracefully returns None for the DB record.
        await asyncio.to_thread(dir_path.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(file_path.write_bytes, content)

        return artifact.id  # type: ignore[return-value]  # SQLAlchemy Mapped[UUID] vs UUID

    async def load(self, artifact_id: uuid.UUID) -> bytes | None:
        """Load artifact content from filesystem using DB-stored path."""
        async with self._db_session_factory() as db:
            artifact = (
                await db.execute(select(Artifact).where(Artifact.id == artifact_id))
            ).scalar_one_or_none()
            if artifact is None:
                return None
            path = Path(artifact.path)
            try:
                self._validate_path_containment(path)
            except ValueError:
                logger.warning("Artifact path fails containment check: %s", path)
                return None
            if not await asyncio.to_thread(path.exists):
                logger.warning("Artifact file not found: %s", path)
                return None
            return await asyncio.to_thread(path.read_bytes)

    async def list_for_entity(
        self, entity_type: str, entity_id: uuid.UUID
    ) -> list[dict[str, object]]:
        """List artifact metadata for an entity (deliverable, taskgroup_execution, etc.)."""
        async with self._db_session_factory() as db:
            stmt = (
                select(Artifact)
                .where(
                    Artifact.entity_type == entity_type,
                    Artifact.entity_id == entity_id,
                )
                .order_by(Artifact.created_at)
            )
            results = (await db.execute(stmt)).scalars().all()
            return [
                {
                    "id": str(a.id),
                    "entity_type": a.entity_type,
                    "entity_id": str(a.entity_id),
                    "path": a.path,
                    "content_type": a.content_type,
                    "size_bytes": a.size_bytes,
                    "created_at": a.created_at.isoformat(),
                }
                for a in results
            ]
