"""Workflow registry -- discovery, indexing, matching, and pipeline instantiation."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import logging
import sys
from typing import TYPE_CHECKING, cast

import yaml

from app.lib.exceptions import ConfigurationError, NotFoundError
from app.workflows.manifest import WorkflowEntry, WorkflowManifest

if TYPE_CHECKING:
    from pathlib import Path

    from arq.connections import ArqRedis
    from google.adk.agents import BaseAgent

    from app.workflows.context import PipelineContext

logger = logging.getLogger(__name__)


def _extract_strings(items: list[object]) -> list[str]:
    """Extract string elements from a mixed-type list."""
    result: list[str] = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
    return result


class WorkflowRegistry:
    """Discovers, indexes, caches, and instantiates workflow definitions."""

    def __init__(
        self,
        workflows_dir: Path,
        user_workflows_dir: Path | None = None,
        redis: ArqRedis | None = None,
    ) -> None:
        self._workflows_dir = workflows_dir
        self._user_workflows_dir = user_workflows_dir
        self._redis = redis
        self._index: dict[str, WorkflowEntry] = {}
        self._manifests: dict[str, WorkflowManifest] = {}
        self._file_mtimes: dict[str, float] = {}
        self._directories: list[Path] = [workflows_dir]
        if user_workflows_dir is not None:
            self._directories.append(user_workflows_dir)

    def scan(self) -> None:
        """Discover WORKFLOW.yaml files from built-in and user directories."""
        self._index.clear()
        self._manifests.clear()
        self._file_mtimes.clear()

        self._scan_directory(self._workflows_dir, scope="built-in")

        user_count = 0
        if self._user_workflows_dir is not None and self._user_workflows_dir.is_dir():
            before = len(self._index)
            self._scan_directory(self._user_workflows_dir, scope="user")
            user_count = len(self._index) - before

        total = len(self._index)
        logger.info(
            "Discovered %d workflows (%d from user-level)",
            total,
            user_count,
        )

    def _scan_directory(self, directory: Path, *, scope: str) -> None:
        """Scan a single directory for subdirectories containing WORKFLOW.yaml."""
        if not directory.is_dir():
            return

        for child in sorted(directory.iterdir()):
            manifest_path = child / "WORKFLOW.yaml"
            if not child.is_dir() or not manifest_path.exists():
                continue

            try:
                raw = manifest_path.read_text(encoding="utf-8")
                data = yaml.safe_load(raw)
                if not isinstance(data, dict):
                    logger.warning(
                        "Invalid WORKFLOW.yaml in '%s' -- not a mapping",
                        child.name,
                    )
                    continue
                manifest = WorkflowManifest.model_validate(data)
            except Exception:
                logger.warning(
                    "Failed to parse WORKFLOW.yaml in '%s' -- skipping",
                    child.name,
                    exc_info=True,
                )
                continue

            name = manifest.name

            if name in self._index:
                existing = self._index[name]
                same_scope = existing.path.is_relative_to(directory)
                if same_scope:
                    logger.warning(
                        "Duplicate workflow name '%s' in %s scope -- keeping first found",
                        name,
                        scope,
                    )
                    continue
                else:
                    logger.info(
                        "User-level workflow '%s' overrides built-in",
                        name,
                    )

            entry = WorkflowEntry(
                name=name,
                description=manifest.description,
                path=child,
                pipeline_type=manifest.pipeline_type,
                triggers=manifest.triggers,
            )
            self._index[name] = entry
            self._manifests[name] = manifest
            self._file_mtimes[str(manifest_path)] = manifest_path.stat().st_mtime

    def get(self, name: str) -> WorkflowEntry:
        """Lookup workflow entry by name. Raises NotFoundError if missing."""
        entry = self._index.get(name)
        if entry is None:
            raise NotFoundError(f"Workflow '{name}' not found")
        return entry

    def get_manifest(self, name: str) -> WorkflowManifest:
        """Lookup full manifest by name. Raises NotFoundError if missing."""
        manifest = self._manifests.get(name)
        if manifest is None:
            raise NotFoundError(f"Workflow manifest '{name}' not found")
        return manifest

    def match(self, user_request: str) -> list[WorkflowEntry]:
        """Match workflows against a user request string.

        Two priority levels:
        - Explicit: user_request exactly equals a trigger's ``explicit`` value
        - Keyword: user_request contains a trigger keyword

        Explicit matches take priority; keyword matches returned only if
        no explicit matches found.
        """
        explicit_matches: list[WorkflowEntry] = []
        keyword_matches: list[WorkflowEntry] = []
        request_lower = user_request.lower()

        for entry in self._index.values():
            for trigger in entry.triggers:
                # Explicit trigger
                explicit_val = trigger.get("explicit")
                if isinstance(explicit_val, str) and user_request == explicit_val:
                    explicit_matches.append(entry)
                    break

                # Keyword trigger
                keywords_raw = trigger.get("keywords")
                if isinstance(keywords_raw, list):
                    keywords = _extract_strings(cast("list[object]", keywords_raw))
                    for kw in keywords:
                        if kw.lower() in request_lower:
                            keyword_matches.append(entry)
                            break
                    else:
                        continue
                    break  # already matched this entry via keyword

        if explicit_matches:
            return explicit_matches
        return keyword_matches

    def list_available(self) -> list[WorkflowEntry]:
        """Return all workflow entries sorted by name."""
        return sorted(self._index.values(), key=lambda e: e.name)

    async def create_pipeline(
        self,
        workflow_name: str,
        ctx: PipelineContext,
    ) -> BaseAgent:
        """Dynamically import pipeline.py and invoke its create_pipeline."""
        entry = self.get(workflow_name)
        pipeline_path = entry.path / "pipeline.py"
        if not pipeline_path.exists():
            raise NotFoundError(f"No pipeline.py found for workflow '{workflow_name}'")

        module_name = f"_autobuilder_workflow_{workflow_name.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, pipeline_path)
        if spec is None or spec.loader is None:
            raise ConfigurationError(f"Cannot load pipeline.py for workflow '{workflow_name}'")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            del sys.modules[module_name]
            raise ConfigurationError(
                f"Failed to import pipeline.py for '{workflow_name}': {e}"
            ) from e

        factory = getattr(module, "create_pipeline", None)
        if factory is None:
            raise ConfigurationError(
                f"pipeline.py for '{workflow_name}' has no 'create_pipeline' function"
            )

        if not inspect.iscoroutinefunction(factory):
            raise ConfigurationError(f"create_pipeline in '{workflow_name}' must be async")

        result: BaseAgent = await factory(ctx)
        return result

    # ------------------------------------------------------------------
    # Redis cache (mirrors SkillLibrary)
    # ------------------------------------------------------------------

    def _cache_key(self) -> str:
        """Deterministic cache key based on configured directories."""
        scope = ":".join(str(d) for d in self._directories)
        scope_hash = hashlib.md5(scope.encode(), usedforsecurity=False).hexdigest()[:12]
        return f"autobuilder:workflow_index:{scope_hash}"

    async def save_to_cache(self) -> None:
        """Serialize index + manifests to Redis. No-op without Redis."""
        if self._redis is None:
            return
        try:
            data: dict[str, object] = {
                "index": {
                    name: entry.model_dump(mode="json") for name, entry in self._index.items()
                },
                "manifests": {
                    name: manifest.model_dump(mode="json")
                    for name, manifest in self._manifests.items()
                },
                "mtimes": self._file_mtimes,
            }
            await self._redis.set(self._cache_key(), json.dumps(data))
        except Exception:
            logger.warning("Failed to save workflow index to Redis cache")

    async def load_from_cache(self) -> bool:
        """Load index from Redis. Returns True on hit, False on miss."""
        if self._redis is None:
            return False
        try:
            raw = await self._redis.get(self._cache_key())
            if raw is None:
                return False
            data = json.loads(raw)
            self._index = {
                name: WorkflowEntry.model_validate(entry_data)
                for name, entry_data in data["index"].items()
            }
            self._manifests = {
                name: WorkflowManifest.model_validate(manifest_data)
                for name, manifest_data in data["manifests"].items()
            }
            self._file_mtimes = data.get("mtimes", {})
            return True
        except Exception:
            logger.warning("Failed to load workflow index from Redis cache")
            return False

    async def invalidate_cache(self) -> None:
        """Delete cached index key. No-op without Redis."""
        if self._redis is None:
            return
        try:
            await self._redis.delete(self._cache_key())
        except Exception:
            logger.warning("Failed to invalidate workflow index cache")
