"""Shared fixtures for Phase 7 workflow composition tests."""

from __future__ import annotations

import logging
import textwrap
from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


# ---------------------------------------------------------------------------
# Logging fixture (mirrors tests/skills/conftest.py)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _enable_log_propagation() -> Generator[None, None, None]:  # type: ignore[reportUnusedFunction]
    """Ensure the ``app`` logger propagates during tests so caplog works."""
    app_logger = logging.getLogger("app")
    original = app_logger.propagate
    app_logger.propagate = True
    yield
    app_logger.propagate = original


# ---------------------------------------------------------------------------
# WORKFLOW.yaml writers
# ---------------------------------------------------------------------------


def write_workflow(
    base_dir: Path,
    name: str,
    *,
    description: str = "A test workflow",
    pipeline_type: str | None = None,
    stages: list[dict[str, Any]] | None = None,
    validators: list[dict[str, Any]] | None = None,
    triggers: list[dict[str, Any]] | None = None,
    required_tools: list[str] | None = None,
    optional_tools: list[str] | None = None,
    default_models: dict[str, str] | None = None,
    completion_report: dict[str, Any] | None = None,
    resources: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    conventions: list[str] | None = None,
    extra_fields: dict[str, Any] | None = None,
    write_pipeline: bool = False,
    pipeline_content: str | None = None,
) -> Path:
    """Write a WORKFLOW.yaml (and optionally pipeline.py) into base_dir/<name>/."""
    workflow_dir = base_dir / name
    workflow_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {"name": name, "description": description}
    if pipeline_type is not None:
        manifest["pipeline_type"] = pipeline_type
    if stages is not None:
        manifest["stages"] = stages
    if validators is not None:
        manifest["validators"] = validators
    if triggers is not None:
        manifest["triggers"] = triggers
    if required_tools is not None:
        manifest["required_tools"] = required_tools
    if optional_tools is not None:
        manifest["optional_tools"] = optional_tools
    if default_models is not None:
        manifest["default_models"] = default_models
    if completion_report is not None:
        manifest["completion_report"] = completion_report
    if resources is not None:
        manifest["resources"] = resources
    if config is not None:
        manifest["config"] = config
    if conventions is not None:
        manifest["conventions"] = conventions
    if extra_fields:
        manifest.update(extra_fields)

    (workflow_dir / "WORKFLOW.yaml").write_text(
        yaml.dump(manifest, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    if write_pipeline:
        content = pipeline_content or textwrap.dedent("""\
            from __future__ import annotations
            from typing import TYPE_CHECKING
            if TYPE_CHECKING:
                from google.adk.agents import BaseAgent
                from app.workflows.context import PipelineContext

            async def create_pipeline(ctx: PipelineContext) -> BaseAgent:
                return ctx.registry.build("stub", ctx.instruction_ctx)
        """)
        (workflow_dir / "pipeline.py").write_text(content, encoding="utf-8")

    return workflow_dir


def write_workflow_agent(
    workflow_dir: Path,
    name: str,
    *,
    description: str = "Test agent",
    agent_type: str = "llm",
    body: str = "Test instructions.",
) -> Path:
    """Write an agent .md definition into workflow_dir/agents/."""
    agents_dir = workflow_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\ntype: {agent_type}\n---\n\n{body}\n"
    agent_file = agents_dir / f"{name}.md"
    agent_file.write_text(content, encoding="utf-8")
    return agent_file


# ---------------------------------------------------------------------------
# Minimal manifests for progressive disclosure tiers
# ---------------------------------------------------------------------------

TIER1_MANIFEST: dict[str, Any] = {
    "name": "minimal-test",
    "description": "Two-field minimum",
}

TIER2_MANIFEST: dict[str, Any] = {
    "name": "stages-test",
    "description": "Stages only",
    "stages": [
        {"name": "alpha", "description": "First stage"},
        {"name": "beta", "description": "Second stage"},
    ],
}

TIER3_MANIFEST: dict[str, Any] = {
    "name": "full-test",
    "description": "Full manifest with all fields",
    "version": "1",
    "pipeline_type": "SEQUENTIAL",
    "triggers": [{"keywords": ["test", "validate"]}, {"explicit": "full-test"}],
    "required_tools": ["file_read", "file_write"],
    "optional_tools": ["web_search"],
    "default_models": {
        "PLAN": "anthropic/claude-opus-4-6",
        "CODE": "anthropic/claude-sonnet-4-6",
    },
    "stages": [
        {
            "name": "prepare",
            "description": "Preparation stage",
            "agents": ["planner"],
            "validators": [
                {
                    "name": "prep_check",
                    "type": "DETERMINISTIC",
                    "schedule": "PER_STAGE",
                }
            ],
            "approval": "auto",
        },
        {
            "name": "execute",
            "description": "Execution stage",
            "agents": ["coder", "reviewer"],
            "validators": [
                {
                    "name": "lint_check",
                    "type": "DETERMINISTIC",
                    "agent": "linter",
                    "schedule": "PER_DELIVERABLE",
                },
                {
                    "name": "test_suite",
                    "type": "DETERMINISTIC",
                    "agent": "tester",
                    "schedule": "PER_DELIVERABLE",
                },
            ],
            "approval": "director",
        },
        {
            "name": "verify",
            "description": "Verification stage",
            "agents": ["tester", "reviewer"],
            "validators": [
                {
                    "name": "final_check",
                    "type": "APPROVAL",
                    "schedule": "PER_STAGE",
                },
            ],
            "approval": "ceo",
        },
    ],
    "completion_report": {
        "layers": [
            {
                "name": "functional",
                "description": "Does it work?",
                "evidence_sources": ["test_suite"],
            },
            {
                "name": "contract",
                "description": "Were deliverables completed?",
                "evidence_sources": ["prep_check"],
            },
        ],
    },
    "resources": {"credentials": ["ANTHROPIC_API_KEY"], "services": [], "knowledge": []},
    "conventions": ["Follow code style", "Tests required"],
    "config": {"max_review_cycles": 3},
}
