"""Tests for trigger matchers in the skill system."""

from app.agents.protocols import SkillMatchContext
from app.models.enums import TriggerType
from app.skills.library import SkillEntry, TriggerSpec
from app.skills.matchers import match_description_keywords, match_triggers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(
    *,
    name: str = "test-skill",
    description: str = "",
    triggers: list[TriggerSpec] | None = None,
    tags: list[str] | None = None,
) -> SkillEntry:
    return SkillEntry(
        name=name,
        description=description,
        triggers=triggers or [],
        tags=tags or [],
    )


def _trigger(trigger_type: TriggerType, value: str = "") -> TriggerSpec:
    return TriggerSpec(trigger_type=trigger_type, value=value)


# ---------------------------------------------------------------------------
# DELIVERABLE_TYPE
# ---------------------------------------------------------------------------


class TestDeliverableType:
    def test_exact_match(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.DELIVERABLE_TYPE, "api")])
        ctx = SkillMatchContext(deliverable_type="api")
        assert match_triggers(entry, ctx) == [TriggerType.DELIVERABLE_TYPE.value]

    def test_no_match_different_value(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.DELIVERABLE_TYPE, "api")])
        ctx = SkillMatchContext(deliverable_type="frontend")
        assert match_triggers(entry, ctx) == []

    def test_no_match_none_deliverable_type(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.DELIVERABLE_TYPE, "api")])
        ctx = SkillMatchContext(deliverable_type=None)
        assert match_triggers(entry, ctx) == []

    def test_case_sensitive(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.DELIVERABLE_TYPE, "API")])
        ctx = SkillMatchContext(deliverable_type="api")
        assert match_triggers(entry, ctx) == []


# ---------------------------------------------------------------------------
# FILE_PATTERN
# ---------------------------------------------------------------------------


class TestFilePattern:
    def test_exact_filename_match(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.FILE_PATTERN, "*.py")])
        ctx = SkillMatchContext(file_patterns=["main.py"])
        assert match_triggers(entry, ctx) == [TriggerType.FILE_PATTERN.value]

    def test_glob_wildcard_match(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.FILE_PATTERN, "**/*.ts")])
        ctx = SkillMatchContext(file_patterns=["src/components/App.ts"])
        assert match_triggers(entry, ctx) == [TriggerType.FILE_PATTERN.value]

    def test_no_match(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.FILE_PATTERN, "*.py")])
        ctx = SkillMatchContext(file_patterns=["index.ts", "styles.css"])
        assert match_triggers(entry, ctx) == []

    def test_any_file_in_list_matches(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.FILE_PATTERN, "*.py")])
        ctx = SkillMatchContext(file_patterns=["readme.md", "main.py", "config.yaml"])
        assert match_triggers(entry, ctx) == [TriggerType.FILE_PATTERN.value]

    def test_empty_file_patterns_no_match(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.FILE_PATTERN, "*.py")])
        ctx = SkillMatchContext(file_patterns=[])
        assert match_triggers(entry, ctx) == []


# ---------------------------------------------------------------------------
# TAG_MATCH
# ---------------------------------------------------------------------------


class TestTagMatch:
    def test_single_tag_intersection(self) -> None:
        entry = _entry(
            triggers=[_trigger(TriggerType.TAG_MATCH)],
            tags=["python", "backend"],
        )
        ctx = SkillMatchContext(tags=["python"])
        assert match_triggers(entry, ctx) == [TriggerType.TAG_MATCH.value]

    def test_no_overlap(self) -> None:
        entry = _entry(
            triggers=[_trigger(TriggerType.TAG_MATCH)],
            tags=["python"],
        )
        ctx = SkillMatchContext(tags=["frontend", "react"])
        assert match_triggers(entry, ctx) == []

    def test_empty_skill_tags_no_match(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.TAG_MATCH)], tags=[])
        ctx = SkillMatchContext(tags=["python"])
        assert match_triggers(entry, ctx) == []

    def test_empty_context_tags_no_match(self) -> None:
        entry = _entry(
            triggers=[_trigger(TriggerType.TAG_MATCH)],
            tags=["python"],
        )
        ctx = SkillMatchContext(tags=[])
        assert match_triggers(entry, ctx) == []

    def test_multiple_tag_overlap(self) -> None:
        entry = _entry(
            triggers=[_trigger(TriggerType.TAG_MATCH)],
            tags=["python", "fastapi", "backend"],
        )
        ctx = SkillMatchContext(tags=["fastapi", "docker"])
        assert match_triggers(entry, ctx) == [TriggerType.TAG_MATCH.value]


# ---------------------------------------------------------------------------
# EXPLICIT
# ---------------------------------------------------------------------------


class TestExplicit:
    def test_name_in_requested_skills(self) -> None:
        entry = _entry(
            name="my-skill",
            triggers=[_trigger(TriggerType.EXPLICIT, "my-skill")],
        )
        ctx = SkillMatchContext(requested_skills=["other-skill", "my-skill"])
        assert match_triggers(entry, ctx) == [TriggerType.EXPLICIT.value]

    def test_name_not_in_requested_skills(self) -> None:
        entry = _entry(
            name="my-skill",
            triggers=[_trigger(TriggerType.EXPLICIT, "my-skill")],
        )
        ctx = SkillMatchContext(requested_skills=["other-skill"])
        assert match_triggers(entry, ctx) == []

    def test_empty_requested_skills(self) -> None:
        entry = _entry(
            name="my-skill",
            triggers=[_trigger(TriggerType.EXPLICIT, "my-skill")],
        )
        ctx = SkillMatchContext(requested_skills=[])
        assert match_triggers(entry, ctx) == []


# ---------------------------------------------------------------------------
# ALWAYS
# ---------------------------------------------------------------------------


class TestAlways:
    def test_always_matches_empty_context(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.ALWAYS)])
        ctx = SkillMatchContext()
        assert match_triggers(entry, ctx) == [TriggerType.ALWAYS.value]

    def test_always_matches_non_empty_context(self) -> None:
        entry = _entry(triggers=[_trigger(TriggerType.ALWAYS)])
        ctx = SkillMatchContext(
            deliverable_type="api",
            tags=["python"],
            file_patterns=["*.py"],
        )
        assert match_triggers(entry, ctx) == [TriggerType.ALWAYS.value]


# ---------------------------------------------------------------------------
# match_triggers: OR logic and edge cases
# ---------------------------------------------------------------------------


class TestMatchTriggersOrLogic:
    def test_empty_triggers_returns_empty(self) -> None:
        entry = _entry(triggers=[])
        ctx = SkillMatchContext(deliverable_type="api")
        assert match_triggers(entry, ctx) == []

    def test_multiple_triggers_only_one_matches(self) -> None:
        entry = _entry(
            triggers=[
                _trigger(TriggerType.DELIVERABLE_TYPE, "frontend"),
                _trigger(TriggerType.DELIVERABLE_TYPE, "api"),
            ]
        )
        ctx = SkillMatchContext(deliverable_type="api")
        result = match_triggers(entry, ctx)
        assert result == [TriggerType.DELIVERABLE_TYPE.value]

    def test_multiple_triggers_all_match(self) -> None:
        entry = _entry(
            triggers=[
                _trigger(TriggerType.ALWAYS),
                _trigger(TriggerType.DELIVERABLE_TYPE, "api"),
            ]
        )
        ctx = SkillMatchContext(deliverable_type="api")
        result = match_triggers(entry, ctx)
        assert TriggerType.ALWAYS.value in result
        assert TriggerType.DELIVERABLE_TYPE.value in result
        assert len(result) == 2

    def test_multiple_triggers_none_match(self) -> None:
        entry = _entry(
            triggers=[
                _trigger(TriggerType.DELIVERABLE_TYPE, "frontend"),
                _trigger(TriggerType.FILE_PATTERN, "*.rs"),
            ]
        )
        ctx = SkillMatchContext(deliverable_type="api", file_patterns=["main.py"])
        assert match_triggers(entry, ctx) == []

    def test_mixed_trigger_types(self) -> None:
        entry = _entry(
            name="poly-skill",
            triggers=[
                _trigger(TriggerType.DELIVERABLE_TYPE, "api"),
                _trigger(TriggerType.FILE_PATTERN, "*.py"),
                _trigger(TriggerType.EXPLICIT, "poly-skill"),
            ],
            tags=["backend"],
        )
        ctx = SkillMatchContext(
            deliverable_type="frontend",
            file_patterns=["main.py"],
            requested_skills=[],
        )
        result = match_triggers(entry, ctx)
        # Only FILE_PATTERN matches
        assert result == [TriggerType.FILE_PATTERN.value]


# ---------------------------------------------------------------------------
# match_description_keywords
# ---------------------------------------------------------------------------


class TestMatchDescriptionKeywords:
    def test_two_keywords_match(self) -> None:
        ctx = SkillMatchContext(
            deliverable_type="python-backend",
            tags=["fastapi", "testing"],
        )
        assert match_description_keywords("fastapi testing patterns", ctx) is True

    def test_one_keyword_insufficient(self) -> None:
        ctx = SkillMatchContext(tags=["fastapi"])
        assert match_description_keywords("fastapi patterns", ctx) is False

    def test_stopwords_excluded(self) -> None:
        # "skill", "provides", "guidance" are stopwords — should not count
        ctx = SkillMatchContext(tags=["skill", "provides", "guidance"])
        assert match_description_keywords("skill provides coding guidance", ctx) is False

    def test_short_words_excluded(self) -> None:
        # Words <=4 chars excluded: "api", "rest", "data"
        ctx = SkillMatchContext(tags=["api", "rest", "data"])
        assert match_description_keywords("api rest data patterns", ctx) is False

    def test_empty_description_no_match(self) -> None:
        ctx = SkillMatchContext(deliverable_type="backend", tags=["python"])
        assert match_description_keywords("", ctx) is False

    def test_no_significant_words_after_filter(self) -> None:
        # All words are short or stopwords
        ctx = SkillMatchContext(tags=["api"])
        assert match_description_keywords("this that with", ctx) is False

    def test_keywords_matched_from_file_patterns(self) -> None:
        ctx = SkillMatchContext(file_patterns=["fastapi-routes.py", "testing-helpers.py"])
        assert match_description_keywords("fastapi testing framework", ctx) is True

    def test_case_insensitive_matching(self) -> None:
        ctx = SkillMatchContext(tags=["FastAPI", "Testing"])
        assert match_description_keywords("FastAPI Testing patterns", ctx) is True

    def test_deliverable_type_contributes_to_pool(self) -> None:
        ctx = SkillMatchContext(deliverable_type="python-backend")
        assert match_description_keywords("python backend service pattern", ctx) is True

    def test_empty_context_no_match(self) -> None:
        assert match_description_keywords("fastapi testing patterns", SkillMatchContext()) is False


# ---------------------------------------------------------------------------
# Integration: SkillEntry with multiple trigger types
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_full_skill_entry_always_trigger(self) -> None:
        entry = SkillEntry(
            name="universal",
            description="Universal coding standards",
            triggers=[TriggerSpec(trigger_type=TriggerType.ALWAYS)],
            tags=["general"],
            priority=0,
        )
        ctx = SkillMatchContext()
        assert match_triggers(entry, ctx) == [TriggerType.ALWAYS.value]

    def test_full_skill_entry_tag_and_file_triggers(self) -> None:
        entry = SkillEntry(
            name="python-style",
            description="Python style guidance",
            triggers=[
                TriggerSpec(trigger_type=TriggerType.TAG_MATCH),
                TriggerSpec(trigger_type=TriggerType.FILE_PATTERN, value="*.py"),
            ],
            tags=["python"],
            priority=10,
        )
        ctx = SkillMatchContext(tags=["python"], file_patterns=["app/main.py"])
        result = match_triggers(entry, ctx)
        assert TriggerType.TAG_MATCH.value in result
        assert TriggerType.FILE_PATTERN.value in result

    def test_no_triggers_description_keyword_fallback(self) -> None:
        entry = SkillEntry(
            name="react-patterns",
            description="React component patterns hooks",
            triggers=[],
            tags=[],
        )
        ctx = SkillMatchContext(
            deliverable_type="react-component",
            tags=["react", "hooks"],
        )
        # No triggers → use description fallback
        assert match_triggers(entry, ctx) == []
        assert match_description_keywords(entry.description, ctx) is True
