"""AgentRegistry — scans definition files, resolves 3-scope cascade, builds ADK agents."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

import yaml

from app.lib.exceptions import NotFoundError, ValidationError
from app.models.enums import AgentType, DefinitionScope, ModelRole

if TYPE_CHECKING:
    from pathlib import Path

    from google.adk.agents import BaseAgent
    from google.adk.tools.base_tool import BaseTool

    from app.agents.assembler import InstructionAssembler, InstructionContext
    from app.router.router import LlmRouter
    from app.tools._toolset import GlobalToolset
    from app.workflows.manifest import WorkflowManifest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

_REQUIRED_FRONTMATTER = {"name", "description", "type"}
_VALID_TYPES = {"llm", "custom"}


@dataclass
class AgentFileEntry:
    """Parsed agent definition file."""

    name: str
    description: str
    agent_type: AgentType
    tool_role: str | None = None
    model_role: str | None = None
    output_key: str | None = None
    class_ref: str | None = None
    applies_to: list[str] = field(default_factory=lambda: list[str]())
    body: str | None = None
    source_path: Path | None = None
    scope: DefinitionScope | None = None


@dataclass(frozen=True)
class AgentResolutionEntry:
    """Audit record for agent definition resolution."""

    agent_name: str
    scope: DefinitionScope
    file_path: str
    partial_override: bool = False


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def parse_definition_file(file_path: Path, scope: DefinitionScope) -> AgentFileEntry:
    """Parse a .md agent definition file. Extracts YAML frontmatter and body."""
    raw = file_path.read_text(encoding="utf-8")
    lines = raw.split("\n")

    if not lines or lines[0].strip() != "---":
        raise ValidationError(
            message=f"Definition file {file_path} must start with '---' frontmatter marker"
        )

    # Find second --- marker
    end_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ValidationError(
            message=f"Definition file {file_path} missing closing '---' frontmatter marker"
        )

    frontmatter_text = "\n".join(lines[1:end_idx])
    raw_fm: object = yaml.safe_load(frontmatter_text)
    if not isinstance(raw_fm, dict):
        raise ValidationError(message=f"Definition file {file_path} has invalid YAML frontmatter")
    fm: dict[str, object] = {str(k): v for k, v in cast("dict[object, object]", raw_fm).items()}

    # Validate required fields
    missing = _REQUIRED_FRONTMATTER - set(fm.keys())
    if missing:
        raise ValidationError(
            message=f"Definition file {file_path} missing required fields: {sorted(missing)}"
        )

    type_val = str(fm["type"]).lower()
    if type_val not in _VALID_TYPES:
        raise ValidationError(
            message=(
                f"Definition file {file_path} has invalid type "
                f"'{fm['type']}'. Must be one of: {sorted(_VALID_TYPES)}"
            )
        )

    agent_type = AgentType.LLM if type_val == "llm" else AgentType.CUSTOM

    if agent_type == AgentType.CUSTOM and "class" not in fm:
        raise ValidationError(
            message=f"Definition file {file_path}: type 'custom' requires 'class' field"
        )

    # Body: everything after the second ---
    body_text = "\n".join(lines[end_idx + 1 :])
    body: str | None = body_text if body_text.strip() else None

    # Parse optional list field
    raw_applies = fm.get("applies_to")
    applies_to: list[str] = []
    if isinstance(raw_applies, list):
        applies_to = [str(a) for a in cast("list[object]", raw_applies)]

    return AgentFileEntry(
        name=str(fm["name"]),
        description=str(fm["description"]),
        agent_type=agent_type,
        tool_role=str(fm["tool_role"]) if "tool_role" in fm else None,
        model_role=str(fm["model_role"]) if "model_role" in fm else None,
        output_key=str(fm["output_key"]) if "output_key" in fm else None,
        class_ref=str(fm["class"]) if "class" in fm else None,
        applies_to=applies_to,
        body=body,
        source_path=file_path,
        scope=scope,
    )


# ---------------------------------------------------------------------------
# Class registry for custom agents
# ---------------------------------------------------------------------------

CLASS_REGISTRY: dict[str, type[BaseAgent]] = {}


def register_custom_agent(name: str, cls: type[BaseAgent]) -> None:
    """Register a CustomAgent class by name."""
    CLASS_REGISTRY[name] = cls


# ---------------------------------------------------------------------------
# AgentRegistry
# ---------------------------------------------------------------------------


class AgentRegistry:
    """Scans agent definition files, resolves 3-scope cascade, builds ADK agents."""

    def __init__(
        self,
        assembler: InstructionAssembler,
        router: LlmRouter,
        toolset: GlobalToolset,
    ) -> None:
        self._assembler = assembler
        self._router = router
        self._toolset = toolset
        self._definitions: dict[str, AgentFileEntry] = {}
        self._scoped_entries: dict[DefinitionScope, dict[str, AgentFileEntry]] = {
            DefinitionScope.GLOBAL: {},
            DefinitionScope.WORKFLOW: {},
            DefinitionScope.PROJECT: {},
        }
        self._resolution_sources: dict[str, AgentResolutionEntry] = {}
        self._scanned = False

    def scan(self, *dirs: tuple[Path, DefinitionScope]) -> None:
        """Scan directories for .md agent definition files.

        Args:
            dirs: sequence of (path, scope) tuples. Later scopes override earlier.

        Validates frontmatter, rejects duplicates within same scope.
        """
        self._definitions.clear()
        self._resolution_sources.clear()
        for scope_dict in self._scoped_entries.values():
            scope_dict.clear()

        # 1. Parse all files per scope
        for dir_path, scope in dirs:
            if not dir_path.is_dir():
                continue
            for md_file in sorted(dir_path.glob("*.md")):
                entry = parse_definition_file(md_file, scope)

                # Same-scope collision check
                if entry.name in self._scoped_entries[scope]:
                    existing = self._scoped_entries[scope][entry.name]
                    raise ValidationError(
                        message=(
                            f"Duplicate agent name '{entry.name}' in scope {scope}: "
                            f"{existing.source_path} and {md_file}"
                        )
                    )

                self._scoped_entries[scope][entry.name] = entry

        # 2. Project-scope type:custom rejection
        for entry in self._scoped_entries[DefinitionScope.PROJECT].values():
            if entry.agent_type == AgentType.CUSTOM:
                raise ValidationError(
                    message=(
                        f"Project-scope custom agents are not allowed: "
                        f"'{entry.name}' in {entry.source_path}"
                    )
                )

        # 3. Resolve cascade: project > workflow > global
        all_names: set[str] = set()
        for scope_dict in self._scoped_entries.values():
            all_names.update(scope_dict.keys())

        priority_order = [
            DefinitionScope.GLOBAL,
            DefinitionScope.WORKFLOW,
            DefinitionScope.PROJECT,
        ]

        for name in sorted(all_names):
            resolved: AgentFileEntry | None = None
            resolution_scope: DefinitionScope | None = None
            partial_override = False

            for scope in priority_order:
                candidate = self._scoped_entries[scope].get(name)
                if candidate is None:
                    continue

                if resolved is None:
                    # First (lowest priority) entry
                    resolved = candidate
                    resolution_scope = scope
                else:
                    # Higher-priority scope overrides
                    if candidate.body is None:
                        # Partial override: merge frontmatter, keep parent body
                        c_tool = candidate.tool_role
                        c_model = candidate.model_role
                        c_outkey = candidate.output_key
                        c_class = candidate.class_ref
                        resolved = AgentFileEntry(
                            name=candidate.name,
                            description=candidate.description,
                            agent_type=candidate.agent_type,
                            tool_role=c_tool if c_tool is not None else resolved.tool_role,
                            model_role=c_model if c_model is not None else resolved.model_role,
                            output_key=c_outkey if c_outkey is not None else resolved.output_key,
                            class_ref=c_class if c_class is not None else resolved.class_ref,
                            applies_to=candidate.applies_to or resolved.applies_to,
                            body=resolved.body,
                            source_path=candidate.source_path,
                            scope=scope,
                        )
                        partial_override = True
                    else:
                        # Full override: replace entirely
                        resolved = candidate
                        partial_override = False
                    resolution_scope = scope

            if resolved is not None and resolution_scope is not None:
                self._definitions[name] = resolved
                self._resolution_sources[name] = AgentResolutionEntry(
                    agent_name=name,
                    scope=resolution_scope,
                    file_path=str(resolved.source_path or ""),
                    partial_override=partial_override,
                )

        self._scanned = True

    def build(
        self,
        name: str,
        ctx: InstructionContext,
        *,
        definition: str | None = None,
        **overrides: object,
    ) -> BaseAgent:
        """Build a configured ADK agent from a resolved definition.

        Args:
            name: ADK agent name (can be dynamic, e.g., 'PM_alpha').
            ctx: Instruction assembly context.
            definition: Lookup key (defaults to name if None).
            **overrides: Additional kwargs passed to agent constructor.

        Returns:
            Configured ADK agent.
        """
        lookup_key = definition or name

        if lookup_key not in self._definitions:
            available = sorted(self._definitions.keys())
            raise NotFoundError(
                message=f"Agent definition '{lookup_key}' not found. Available: {available}"
            )

        entry = self._definitions[lookup_key]

        if entry.agent_type == AgentType.LLM:
            return self._build_llm_agent(name, entry, ctx, **overrides)
        return self._build_custom_agent(name, entry, ctx, **overrides)

    def _build_llm_agent(
        self,
        name: str,
        entry: AgentFileEntry,
        ctx: InstructionContext,
        **overrides: object,
    ) -> BaseAgent:
        """Build an LlmAgent from definition entry."""
        from google.adk.agents import LlmAgent

        # 1. Resolve model via router
        model_role_str = entry.model_role or "fast"
        model = self._router.select_model(ModelRole(model_role_str.upper()))

        # 2. Assemble instruction
        instruction = self._assembler.assemble(name, entry.body or "", ctx)

        # 3. Get tools for role
        tools: list[BaseTool] = []
        if entry.tool_role:
            tools = self._toolset.get_tools_for_role(entry.tool_role)

        # 4. Build LlmAgent
        agent_kwargs: dict[str, object] = {
            "name": name,
            "model": f"litellm/{model}",
            "instruction": instruction,
            "description": entry.description,
        }
        if tools:
            agent_kwargs["tools"] = tools
        if entry.output_key:
            agent_kwargs["output_key"] = entry.output_key

        # Merge overrides (before_model_callback, sub_agents, etc.)
        agent_kwargs.update(overrides)

        return LlmAgent(**agent_kwargs)  # type: ignore[arg-type]

    def _build_custom_agent(
        self,
        name: str,
        entry: AgentFileEntry,
        ctx: InstructionContext,
        **overrides: object,
    ) -> BaseAgent:
        """Build a CustomAgent from definition entry."""
        if not entry.class_ref:
            raise ValidationError(message=f"Custom agent '{name}' missing 'class' in definition")

        cls = CLASS_REGISTRY.get(entry.class_ref)
        if cls is None:
            raise NotFoundError(
                message=(
                    f"Class '{entry.class_ref}' not in class registry. "
                    f"Registered: {sorted(CLASS_REGISTRY.keys())}"
                )
            )

        agent_kwargs: dict[str, object] = {
            "name": name,
            "description": entry.description,
        }
        if entry.model_role:
            agent_kwargs["model_role"] = entry.model_role
        if entry.body:
            agent_kwargs["instruction_body"] = entry.body

        agent_kwargs.update(overrides)

        return cls(**agent_kwargs)  # type: ignore[arg-type]

    def validate_project_scope(self, manifest: WorkflowManifest) -> list[str]:
        """Validate that PROJECT-scope agents' tool_roles don't exceed manifest tool set.

        Compares each PROJECT-scope entry's tool_role permissions against the
        manifest's required_tools + optional_tools. Emits a warning for each
        agent that requests tools beyond the manifest's declared set.

        Returns list of warning messages (empty = all valid).
        """
        from app.tools._toolset import ROLE_PERMISSIONS

        manifest_tools = set(manifest.required_tools) | set(manifest.optional_tools)
        if not manifest_tools:
            return []

        warnings: list[str] = []
        for name, entry in self._scoped_entries[DefinitionScope.PROJECT].items():
            if entry.tool_role is None:
                continue
            role_tools = ROLE_PERMISSIONS.get(entry.tool_role, set())
            excess = role_tools - manifest_tools
            if excess:
                msg = (
                    f"Project-scope agent '{name}' has tool_role '{entry.tool_role}' "
                    f"granting tools beyond manifest '{manifest.name}': "
                    f"{sorted(excess)}"
                )
                logger.warning(msg)
                warnings.append(msg)

        return warnings

    def get_resolution_sources(self) -> dict[str, AgentResolutionEntry]:
        """Return resolution audit map."""
        return dict(self._resolution_sources)
