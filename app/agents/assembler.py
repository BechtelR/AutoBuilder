"""Instruction composition system for agent instruction assembly."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.enums import FragmentType

_SEPARATOR = "\n\n---\n\n"

SAFETY_CONTENT = (
    "You are an AI agent operating within AutoBuilder. You MUST: "
    "never execute destructive operations without explicit authorization; "
    "never expose credentials, API keys, or secrets; "
    "never modify files outside the designated project workspace; "
    "always validate inputs before processing; "
    "report anomalies to your supervisor rather than attempting "
    "autonomous resolution of security-sensitive situations."
)

# Pattern for valid ADK template placeholders: {word_chars} or {word_chars?}
_PLACEHOLDER_RE = re.compile(r"\{(\w+\??)\}")


def escape_braces(text: str) -> str:
    """Escape { and } except for {key} and {key?} template placeholders."""
    # Find all valid placeholders first
    placeholders = _PLACEHOLDER_RE.findall(text)

    # Escape all braces
    escaped = text.replace("{", "{{").replace("}", "}}")

    # Restore valid placeholders: {{key}} -> {key}
    for ph in placeholders:
        escaped = escaped.replace("{{" + ph + "}}", "{" + ph + "}")

    return escaped


@dataclass(frozen=True)
class InstructionFragment:
    """A typed piece of agent instruction with audit trail."""

    fragment_type: FragmentType
    content: str
    source: str = ""


@dataclass(frozen=True)
class InstructionContext:
    """Per-invocation data for instruction assembly."""

    project_config: str | None = None
    task_context: str | None = None
    loaded_skills: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    agent_name: str = ""


class InstructionAssembler:
    """Assembles typed instruction fragments into a single instruction string.

    Assembly order: SAFETY -> body (IDENTITY/GOVERNANCE) -> PROJECT -> TASK -> SKILL.
    Deterministic: identical inputs always produce identical output.
    """

    def __init__(self) -> None:
        self._fragments: list[InstructionFragment] = []

    def assemble(self, agent_name: str, body: str, ctx: InstructionContext) -> str:
        """Assemble instruction fragments into a single instruction string.

        Args:
            agent_name: Name of the agent (for audit trail).
            body: The agent definition body (IDENTITY + GOVERNANCE content).
            ctx: Per-invocation context with optional PROJECT, TASK, SKILL data.

        Returns:
            Assembled instruction string with fragments separated by ``---``.
        """
        fragments: list[InstructionFragment] = []

        # SAFETY: always first, hardcoded
        fragments.append(
            InstructionFragment(
                fragment_type=FragmentType.SAFETY,
                content=SAFETY_CONTENT,
                source="hardcoded",
            )
        )

        # IDENTITY + GOVERNANCE: the body parameter
        fragments.append(
            InstructionFragment(
                fragment_type=FragmentType.IDENTITY,
                content=body,
                source=f"agent:{agent_name}",
            )
        )

        # PROJECT: from ctx.project_config
        if ctx.project_config is not None:
            fragments.append(
                InstructionFragment(
                    fragment_type=FragmentType.PROJECT,
                    content=escape_braces(ctx.project_config),
                    source=f"project_config:{ctx.agent_name or agent_name}",
                )
            )

        # TASK: from ctx.task_context
        if ctx.task_context is not None:
            fragments.append(
                InstructionFragment(
                    fragment_type=FragmentType.TASK,
                    content=ctx.task_context,
                    source="session_state",
                )
            )

        # SKILL: from ctx.loaded_skills
        if ctx.loaded_skills:
            skill_sections: list[str] = []
            for skill_name in sorted(ctx.loaded_skills):
                skill_content = escape_braces(ctx.loaded_skills[skill_name])
                skill_sections.append(f"## Skill: {skill_name}\n\n{skill_content}")
            fragments.append(
                InstructionFragment(
                    fragment_type=FragmentType.SKILL,
                    content="\n\n".join(skill_sections),
                    source=",".join(sorted(ctx.loaded_skills)),
                )
            )

        self._fragments = fragments
        return _SEPARATOR.join(f.content for f in fragments)

    def get_source_map(self) -> list[InstructionFragment]:
        """Return fragments from the last assembly for auditability."""
        return list(self._fragments)
