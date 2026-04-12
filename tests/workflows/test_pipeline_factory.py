"""Tests for dynamic pipeline import and PipelineContext."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from app.lib.exceptions import ConfigurationError, NotFoundError
from app.workflows.context import PipelineContext, PipelineFactory
from app.workflows.registry import WorkflowRegistry
from tests.workflows.conftest import write_workflow

# ---------------------------------------------------------------------------
# PipelineContext
# ---------------------------------------------------------------------------


class TestPipelineContext:
    def test_frozen(self) -> None:
        """PipelineContext is immutable."""
        ctx = PipelineContext(
            registry=MagicMock(),
            instruction_ctx=MagicMock(),
            manifest=MagicMock(),
            skill_library=MagicMock(),
            toolset=MagicMock(),
        )
        with pytest.raises(AttributeError):
            ctx.registry = MagicMock()  # type: ignore[misc]

    def test_callback_defaults_none(self) -> None:
        ctx = PipelineContext(
            registry=MagicMock(),
            instruction_ctx=MagicMock(),
            manifest=MagicMock(),
            skill_library=MagicMock(),
            toolset=MagicMock(),
        )
        assert ctx.before_model_callback is None

    def test_all_fields_accessible(self) -> None:
        mock = MagicMock()
        ctx = PipelineContext(
            registry=mock,
            instruction_ctx=mock,
            manifest=mock,
            skill_library=mock,
            toolset=mock,
            before_model_callback=mock,
        )
        assert ctx.registry is mock
        assert ctx.before_model_callback is mock


# ---------------------------------------------------------------------------
# PipelineFactory Protocol
# ---------------------------------------------------------------------------


class TestPipelineFactoryProtocol:
    def test_async_function_satisfies_protocol(self) -> None:
        """An async callable with correct signature satisfies Protocol."""

        async def factory(ctx: PipelineContext) -> object:
            return MagicMock()

        # runtime_checkable Protocol check
        assert isinstance(factory, PipelineFactory)


# ---------------------------------------------------------------------------
# create_pipeline (dynamic import)
# ---------------------------------------------------------------------------


class TestCreatePipeline:
    @pytest.mark.asyncio
    async def test_valid_pipeline(self, tmp_path: Path) -> None:
        """Dynamic import of valid pipeline.py works."""
        pipeline_code = textwrap.dedent("""\
            from __future__ import annotations

            class _StubAgent:
                def __init__(self, name: str) -> None:
                    self.name = name

            async def create_pipeline(ctx: object) -> _StubAgent:
                return _StubAgent(name="test-pipeline")
        """)
        write_workflow(
            tmp_path,
            "valid",
            write_pipeline=True,
            pipeline_content=pipeline_code,
        )
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        ctx = PipelineContext(
            registry=MagicMock(),
            instruction_ctx=MagicMock(),
            manifest=registry.get_manifest("valid"),
            skill_library=MagicMock(),
            toolset=MagicMock(),
        )
        result = await registry.create_pipeline("valid", ctx)
        assert result.name == "test-pipeline"  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_missing_pipeline_py(self, tmp_path: Path) -> None:
        """No pipeline.py raises NotFoundError."""
        write_workflow(tmp_path, "no-pipeline")
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        ctx = MagicMock()
        with pytest.raises(NotFoundError, match="pipeline.py"):
            await registry.create_pipeline("no-pipeline", ctx)

    @pytest.mark.asyncio
    async def test_pipeline_missing_function(self, tmp_path: Path) -> None:
        """pipeline.py without create_pipeline raises ConfigurationError."""
        write_workflow(
            tmp_path,
            "bad-func",
            write_pipeline=True,
            pipeline_content="x = 1\n",
        )
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        ctx = MagicMock()
        with pytest.raises(ConfigurationError, match="create_pipeline"):
            await registry.create_pipeline("bad-func", ctx)

    @pytest.mark.asyncio
    async def test_pipeline_sync_function_rejected(self, tmp_path: Path) -> None:
        """Sync create_pipeline raises ConfigurationError."""
        pipeline_code = textwrap.dedent("""\
            def create_pipeline(ctx):
                return None
        """)
        write_workflow(
            tmp_path,
            "sync-func",
            write_pipeline=True,
            pipeline_content=pipeline_code,
        )
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        ctx = MagicMock()
        with pytest.raises(ConfigurationError, match="async"):
            await registry.create_pipeline("sync-func", ctx)

    @pytest.mark.asyncio
    async def test_pipeline_import_error(self, tmp_path: Path) -> None:
        """pipeline.py with import error raises ConfigurationError."""
        write_workflow(
            tmp_path,
            "import-err",
            write_pipeline=True,
            pipeline_content="import nonexistent_module\n",
        )
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        ctx = MagicMock()
        with pytest.raises(ConfigurationError, match="Failed to import"):
            await registry.create_pipeline("import-err", ctx)

    @pytest.mark.asyncio
    async def test_unknown_workflow_raises(self, tmp_path: Path) -> None:
        """Creating pipeline for unknown workflow raises NotFoundError."""
        registry = WorkflowRegistry(tmp_path)
        registry.scan()
        ctx = MagicMock()
        with pytest.raises(NotFoundError):
            await registry.create_pipeline("ghost", ctx)
