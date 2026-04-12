"""Skill types and library for the AutoBuilder skills system."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TriggerType  # noqa: TC001 - required at runtime for Pydantic field

if TYPE_CHECKING:
    from arq.connections import ArqRedis

    from app.agents.protocols import SkillContent, SkillMatchContext

logger = logging.getLogger(__name__)


class TriggerSpec(BaseModel):
    """Single trigger condition in skill frontmatter."""

    model_config = ConfigDict(frozen=True)

    trigger_type: TriggerType
    value: str = ""


class CascadeRef(BaseModel):
    """Reference to a cascaded skill."""

    model_config = ConfigDict(frozen=True)

    reference: str


class SkillEntry(BaseModel):
    """Skill metadata from YAML frontmatter. Immutable after creation."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    description: str = ""
    triggers: list[TriggerSpec] = Field(default_factory=lambda: list[TriggerSpec]())
    tags: list[str] = Field(default_factory=lambda: list[str]())
    applies_to: list[str] = Field(default_factory=lambda: list[str]())
    priority: int = 0
    cascades: list[CascadeRef] = Field(default_factory=lambda: list[CascadeRef]())
    has_references: bool = False
    has_assets: bool = False
    has_scripts: bool = False
    path: Path | None = None


class SkillLibrary:
    """Production skill library: filesystem scan, trigger matching, content loading.

    Structurally implements SkillLibraryProtocol (duck typing).
    """

    def __init__(
        self,
        global_dir: Path,
        workflow_dir: Path | None = None,
        project_dir: Path | None = None,
        redis: ArqRedis | None = None,
    ) -> None:
        self._global_dir = global_dir
        self._workflow_dir = workflow_dir
        self._project_dir = project_dir
        self._redis = redis
        self._index: dict[str, SkillEntry] = {}
        self._file_mtimes: dict[str, float] = {}

    def scan(self) -> None:
        """Recursively scan configured directories, parse frontmatter, build index.

        Global directory scanned first, project-local second (overrides by name).
        """
        self._index.clear()
        self._file_mtimes.clear()

        self._scan_directory(self._global_dir, scope="global")

        if self._workflow_dir is not None and self._workflow_dir.is_dir():
            self._scan_directory(self._workflow_dir, scope="workflow")

        if self._project_dir is not None and self._project_dir.is_dir():
            self._scan_directory(self._project_dir, scope="project")

    def _scan_directory(self, directory: Path, *, scope: str) -> None:
        """Scan a single directory for SKILL.md files."""
        if not directory.is_dir():
            return

        from app.skills.parser import parse_skill_frontmatter

        for skill_path in sorted(directory.rglob("SKILL.md")):
            entry = parse_skill_frontmatter(skill_path)
            if entry is None:
                continue

            # FR-6.04: Name vs directory mismatch warning
            if entry.name != skill_path.parent.name:
                logger.warning(
                    "Skill name '%s' does not match directory '%s' — using frontmatter name",
                    entry.name,
                    skill_path.parent.name,
                )

            # FR-6.06: Duplicate names within same scope — first wins
            if entry.name in self._index:
                existing = self._index[entry.name]
                existing_in_same_scope = existing.path is not None and existing.path.is_relative_to(
                    directory
                )
                if existing_in_same_scope:
                    logger.warning(
                        "Duplicate skill name '%s' in %s scope — keeping first found",
                        entry.name,
                        scope,
                    )
                    continue

            # FR-6.21: Override logging for workflow and project scopes
            if scope == "workflow" and entry.name in self._index:
                logger.info(
                    "Workflow skill '%s' overrides global skill",
                    entry.name,
                )
            elif scope == "project" and entry.name in self._index:
                logger.info(
                    "Project-local skill '%s' overrides previous skill",
                    entry.name,
                )

            self._index[entry.name] = entry
            self._file_mtimes[str(skill_path)] = skill_path.stat().st_mtime

    def match(self, context: SkillMatchContext) -> list[SkillEntry]:
        """Deterministic trigger matching against the full index.

        Returns matched entries sorted by priority desc, then name asc.
        Skills without triggers use description keyword fallback.
        """
        from app.skills.matchers import match_description_keywords, match_triggers

        matched: list[SkillEntry] = []
        for entry in self._index.values():
            if entry.triggers:
                trigger_matches = match_triggers(entry, context)
                if trigger_matches:
                    matched.append(entry)
            else:
                # No triggers — description keyword fallback (FR-6.15)
                if match_description_keywords(entry.description, context):
                    matched.append(entry)

        # Sort: priority desc, name asc (FR-6.13)
        matched.sort(key=lambda e: (-e.priority, e.name))
        return matched

    def load(self, entry: SkillEntry) -> SkillContent:
        """Load full markdown body (below frontmatter) from disk."""
        from app.agents.protocols import SkillContent as SC

        if entry.path is None:
            return SC(entry=entry, content="")

        try:
            text = entry.path.read_text(encoding="utf-8")
        except OSError:
            logger.warning("Failed to read skill file: %s", entry.path)
            return SC(entry=entry, content="")

        # Extract body below frontmatter
        parts = text.split("---", 2)
        body = parts[2].strip() if len(parts) > 2 else ""

        # NFR-6.03: Warn if body exceeds 3000 words
        word_count = len(body.split())
        if word_count > 3000:
            logger.warning(
                "Skill '%s' body has %d words (>3000) — consider moving content to references/",
                entry.name,
                word_count,
            )

        return SC(entry=entry, content=body)

    def resolve_cascades(self, entries: list[SkillEntry]) -> list[SkillEntry]:
        """Transitively resolve cascade dependencies.

        Uses visited-name tracking to prevent cycles (FR-6.24).
        Missing references logged as warnings (FR-6.25).
        """
        result: list[SkillEntry] = list(entries)
        visited: set[str] = {e.name for e in entries}

        pending: list[str] = []
        for entry in entries:
            for cascade in entry.cascades:
                if cascade.reference not in visited:
                    pending.append(cascade.reference)

        while pending:
            ref_name = pending.pop(0)
            if ref_name in visited:
                # Diamond deps (A->B, A->C, B->D, C->D) are normal — skip silently.
                # True cycles are also safe (visited set prevents infinite loops).
                continue

            visited.add(ref_name)

            cascaded = self._index.get(ref_name)
            if cascaded is None:
                logger.warning(
                    "Cascade reference '%s' not found in index — skipping",
                    ref_name,
                )
                continue

            result.append(cascaded)

            for cascade in cascaded.cascades:
                if cascade.reference in visited:
                    logger.debug(
                        "Cascade skip: skill '%s' references already-resolved '%s'",
                        ref_name,
                        cascade.reference,
                    )
                else:
                    pending.append(cascade.reference)

        return result

    def get_index(self) -> dict[str, SkillEntry]:
        """Return a copy of the full index for inspection (FR-6.39)."""
        return dict(self._index)

    # ------------------------------------------------------------------
    # Redis cache methods (FR-6.34)
    # ------------------------------------------------------------------

    def _cache_key(self) -> str:
        """Deterministic cache key based on configured directory paths."""
        scope = f"{self._global_dir}:{self._workflow_dir or ''}:{self._project_dir or ''}"
        scope_hash = hashlib.md5(scope.encode(), usedforsecurity=False).hexdigest()[:12]
        return f"autobuilder:skill_index:{scope_hash}"

    async def save_to_cache(self) -> None:
        """Serialize index to Redis as JSON.

        Atomic: old index serves until new SET completes.
        No-op when Redis is not configured.
        """
        if self._redis is None:
            return
        try:
            # model_dump(mode="json") already converts Path→str
            data: dict[str, object] = {
                "index": {
                    name: entry.model_dump(mode="json") for name, entry in self._index.items()
                },
                "mtimes": self._file_mtimes,
            }
            await self._redis.set(self._cache_key(), json.dumps(data))
        except Exception:
            logger.warning("Failed to save skill index to Redis cache")

    async def load_from_cache(self) -> bool:
        """Load index from Redis cache.

        Returns True on cache hit, False on miss or any error.
        """
        if self._redis is None:
            return False
        try:
            raw = await self._redis.get(self._cache_key())
            if raw is None:
                return False
            data = json.loads(raw)
            self._index = {
                name: SkillEntry.model_validate(entry_data)
                for name, entry_data in data["index"].items()
            }
            self._file_mtimes = data.get("mtimes", {})
            return True
        except Exception:
            logger.warning("Failed to load skill index from Redis cache")
            return False

    async def invalidate_cache(self) -> None:
        """Delete cached index key.

        Next access triggers filesystem rescan. No-op when Redis is not configured.
        """
        if self._redis is None:
            return
        try:
            await self._redis.delete(self._cache_key())
        except Exception:
            logger.warning("Failed to invalidate skill index cache")

    def check_for_changes(self) -> bool:
        """Compare cached file modification timestamps against current disk state.

        Returns True if any changes are detected (modified, deleted, or new files).
        """
        for path_str, cached_mtime in self._file_mtimes.items():
            path = Path(path_str)
            if not path.exists():
                return True
            if path.stat().st_mtime != cached_mtime:
                return True

        current_files: set[str] = set()
        if self._global_dir.is_dir():
            current_files.update(str(p) for p in self._global_dir.rglob("SKILL.md"))
        if self._workflow_dir is not None and self._workflow_dir.is_dir():
            current_files.update(str(p) for p in self._workflow_dir.rglob("SKILL.md"))
        if self._project_dir is not None and self._project_dir.is_dir():
            current_files.update(str(p) for p in self._project_dir.rglob("SKILL.md"))

        return current_files != set(self._file_mtimes.keys())
