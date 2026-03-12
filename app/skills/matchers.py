"""Trigger matchers for the skill system."""

import fnmatch
import logging
from collections.abc import Callable

from app.agents.protocols import SkillMatchContext
from app.models.enums import TriggerType
from app.skills.library import SkillEntry, TriggerSpec

logger = logging.getLogger(__name__)

# Stopwords for description keyword fallback
_STOPWORDS: frozenset[str] = frozenset(
    {
        "this",
        "that",
        "with",
        "from",
        "will",
        "have",
        "been",
        "when",
        "what",
        "which",
        "where",
        "there",
        "their",
        "about",
        "should",
        "would",
        "could",
        "does",
        "into",
        "also",
        "more",
        "most",
        "some",
        "than",
        "then",
        "them",
        "they",
        "these",
        "those",
        "other",
        "each",
        "every",
        "such",
        "only",
        "very",
        "just",
        "over",
        "after",
        "before",
        "between",
        "under",
        "through",
        "during",
        "above",
        "below",
        "skill",
        "provides",
        "guidance",
        "guide",
    }
)


def _match_deliverable_type(trigger: TriggerSpec, context: SkillMatchContext) -> bool:
    """Exact string match: trigger value == context.deliverable_type."""
    return context.deliverable_type is not None and trigger.value == context.deliverable_type


def _match_file_pattern(trigger: TriggerSpec, context: SkillMatchContext) -> bool:
    """Glob match: any file in context.file_patterns matches trigger pattern."""
    return any(fnmatch.fnmatch(f, trigger.value) for f in context.file_patterns)


def _match_explicit(trigger: TriggerSpec, context: SkillMatchContext, *, skill_name: str) -> bool:
    """Skill name checked against context.requested_skills (FR-6.10)."""
    return skill_name in context.requested_skills


def _match_always(_trigger: TriggerSpec, _context: SkillMatchContext) -> bool:
    """Unconditional match."""
    return True


_TRIGGER_MATCHERS: dict[TriggerType, Callable[[TriggerSpec, SkillMatchContext], bool]] = {
    TriggerType.DELIVERABLE_TYPE: _match_deliverable_type,
    TriggerType.FILE_PATTERN: _match_file_pattern,
    TriggerType.ALWAYS: _match_always,
    # TAG_MATCH and EXPLICIT handled specially in match_triggers
}


def match_triggers(entry: SkillEntry, context: SkillMatchContext) -> list[str]:
    """Evaluate all triggers on a skill entry against context.

    Returns list of matched trigger type values (empty = no match).
    OR logic: any single trigger match is sufficient, but all matches are returned.
    TAG_MATCH uses the skill's own tags list intersected with context.tags.
    """
    matched: list[str] = []
    for trigger in entry.triggers:
        if trigger.trigger_type == TriggerType.TAG_MATCH:
            if set(entry.tags) & set(context.tags):
                matched.append(trigger.trigger_type.value)
        elif trigger.trigger_type == TriggerType.EXPLICIT:
            if _match_explicit(trigger, context, skill_name=entry.name):
                matched.append(trigger.trigger_type.value)
        else:
            matcher = _TRIGGER_MATCHERS.get(trigger.trigger_type)
            if matcher is not None and matcher(trigger, context):
                matched.append(trigger.trigger_type.value)
    return matched


def match_description_keywords(description: str, context: SkillMatchContext) -> bool:
    """Conservative keyword fallback for third-party skills without triggers.

    Extracts significant words (>4 chars, not stopwords) from description.
    Requires >=2 keywords to appear across context strings.
    """
    words = {w.lower() for w in description.split() if len(w) > 4 and w.lower() not in _STOPWORDS}
    if not words:
        return False

    context_parts: list[str] = []
    if context.deliverable_type:
        context_parts.append(context.deliverable_type.lower())
    context_parts.extend(t.lower() for t in context.tags)
    context_parts.extend(f.lower() for f in context.file_patterns)
    context_text = " ".join(context_parts)

    hits = sum(1 for w in words if w in context_text)
    return hits >= 2
