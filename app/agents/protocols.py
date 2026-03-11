"""Protocol definitions and stubs for agent subsystem interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SkillMatchContext:
    """Context for skill matching."""

    deliverable_type: str | None = None
    file_patterns: list[str] = field(default_factory=lambda: list[str]())
    tags: list[str] = field(default_factory=lambda: list[str]())
    agent_role: str | None = None


@dataclass(frozen=True)
class SkillEntry:
    """Skill metadata from frontmatter."""

    name: str
    description: str = ""
    applies_to: list[str] = field(default_factory=lambda: list[str]())


@dataclass(frozen=True)
class SkillContent:
    """Loaded skill content."""

    entry: SkillEntry
    content: str


class SkillLibraryProtocol(Protocol):
    """Interface for skill resolution."""

    def match(self, context: SkillMatchContext) -> list[SkillEntry]: ...
    def load(self, entry: SkillEntry) -> SkillContent: ...


class NullSkillLibrary:
    """Returns empty results. Phase 5a stub."""

    def match(self, context: SkillMatchContext) -> list[SkillEntry]:
        return []

    def load(self, entry: SkillEntry) -> SkillContent:
        return SkillContent(entry=entry, content="")
