"""Tests for ADK engine factory functions."""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.genai.types import Content, Part

from app.agents.assembler import InstructionContext, LoadedSkillData
from app.agents.protocols import SkillContent, SkillMatchContext
from app.models.constants import APP_NAME
from app.models.enums import TriggerType
from app.skills.library import SkillEntry, SkillLibrary, TriggerSpec
from app.workers.adk import (
    LoggingPlugin,
    _resolve_skills_for_agent,  # type: ignore[reportPrivateUsage]
    build_chat_session_agent,
    create_app_container,
    create_echo_agent,
    create_runner,
    create_session_service,
)
from tests.conftest import TEST_DB_URL, require_llm, require_postgres


class TestCreateEchoAgent:
    def test_returns_llm_agent(self) -> None:
        agent = create_echo_agent("anthropic/claude-haiku-4-5-20251001")
        assert isinstance(agent, LlmAgent)

    def test_agent_name(self) -> None:
        agent = create_echo_agent("anthropic/claude-haiku-4-5-20251001")
        assert agent.name == "echo_agent"

    def test_output_key(self) -> None:
        agent = create_echo_agent("anthropic/claude-haiku-4-5-20251001")
        assert agent.output_key == "agent_response"


class TestCreateAppContainer:
    def test_returns_app(self) -> None:
        agent = create_echo_agent("anthropic/claude-haiku-4-5-20251001")
        app = create_app_container(agent)
        assert isinstance(app, App)

    def test_app_name(self) -> None:
        agent = create_echo_agent("anthropic/claude-haiku-4-5-20251001")
        app = create_app_container(agent)
        assert app.name == "autobuilder"

    def test_has_compaction_config(self) -> None:
        agent = create_echo_agent("anthropic/claude-haiku-4-5-20251001")
        app = create_app_container(agent)
        assert app.events_compaction_config is not None

    def test_has_resumability_config(self) -> None:
        agent = create_echo_agent("anthropic/claude-haiku-4-5-20251001")
        app = create_app_container(agent)
        assert app.resumability_config is not None

    def test_has_context_cache_config(self) -> None:
        agent = create_echo_agent("anthropic/claude-haiku-4-5-20251001")
        app = create_app_container(agent)
        assert app.context_cache_config is not None

    def test_default_plugins_include_logging(self) -> None:
        agent = create_echo_agent("anthropic/claude-haiku-4-5-20251001")
        app = create_app_container(agent)
        assert app.plugins is not None
        assert any(isinstance(p, LoggingPlugin) for p in app.plugins)


class TestLoggingPlugin:
    def test_is_base_plugin(self) -> None:
        plugin = LoggingPlugin()
        assert isinstance(plugin, BasePlugin)


@require_postgres
class TestCreateSessionService:
    def test_creates_session_service(self) -> None:
        service = create_session_service(TEST_DB_URL)
        assert service is not None

    @pytest.mark.asyncio
    async def test_can_create_session(self) -> None:
        service = create_session_service(TEST_DB_URL)
        session = await service.create_session(  # type: ignore[reportUnknownMemberType]
            app_name="test_app",
            user_id="test_user",
            session_id=f"test_session_{uuid.uuid4().hex[:8]}",
        )
        assert session is not None


@require_postgres
class TestCreateRunner:
    def test_returns_runner(self) -> None:
        agent = create_echo_agent("anthropic/claude-haiku-4-5-20251001")
        app_container = create_app_container(agent)
        session_service = create_session_service(TEST_DB_URL)
        runner = create_runner(app_container, session_service)
        assert isinstance(runner, Runner)


@require_postgres
@require_llm
class TestSessionPersistence:
    """Integration tests for ADK session state persistence with real PostgreSQL and LLM."""

    @pytest.mark.asyncio
    async def test_session_persists_agent_response(self) -> None:
        """Run echo agent, verify agent_response persists in session state across runs."""
        session_service = create_session_service(TEST_DB_URL)
        session_id = f"persist_{uuid.uuid4().hex[:8]}"

        # Create agent + runner
        echo_agent = create_echo_agent(model="anthropic/claude-haiku-4-5-20251001")
        app_container = create_app_container(root_agent=echo_agent)
        runner = create_runner(app_container, session_service)

        # Create session
        session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id="test_user",
            session_id=session_id,
        )
        assert session is not None

        # First run
        message = Content(parts=[Part(text="Say hello in one word.")])
        async for _event in runner.run_async(  # type: ignore[reportUnknownMemberType]
            user_id="test_user",
            session_id=session_id,
            new_message=message,
        ):
            pass  # consume all events

        # Retrieve session and verify agent_response exists in state
        retrieved = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id="test_user",
            session_id=session_id,
        )
        assert retrieved is not None
        state: dict[str, object] = retrieved.state  # type: ignore[reportUnknownMemberType]
        assert "agent_response" in state
        first_response = state["agent_response"]
        assert first_response is not None

        # Second run on the same session
        message2 = Content(parts=[Part(text="Say goodbye in one word.")])
        async for _event in runner.run_async(  # type: ignore[reportUnknownMemberType]
            user_id="test_user",
            session_id=session_id,
            new_message=message2,
        ):
            pass

        # Verify agent_response still exists (updated from second run)
        retrieved2 = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id="test_user",
            session_id=session_id,
        )
        assert retrieved2 is not None
        state2: dict[str, object] = retrieved2.state  # type: ignore[reportUnknownMemberType]
        assert "agent_response" in state2
        assert state2["agent_response"] is not None


@require_postgres
class TestAppScopeInitialization:
    """Integration tests for app: scope state initialization."""

    @pytest.mark.asyncio
    async def test_app_scope_keys_exist_after_init(self) -> None:
        """Simulate startup logic: create session with app: scope keys, verify they persist."""
        session_service = create_session_service(TEST_DB_URL)
        session_id = f"init_{uuid.uuid4().hex[:8]}"

        # Create session with app: scope state (mimics startup in settings.py)
        session = await session_service.create_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id="system",
            session_id=session_id,
            state={
                "app:skill_index": {},
                "app:workflow_registry": {},
            },
        )
        assert session is not None

        # Retrieve and verify app: scope keys exist
        retrieved = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id="system",
            session_id=session_id,
        )
        assert retrieved is not None
        state: dict[str, object] = retrieved.state  # type: ignore[reportUnknownMemberType]
        assert "app:skill_index" in state
        assert "app:workflow_registry" in state
        assert isinstance(state["app:skill_index"], dict)
        assert isinstance(state["app:workflow_registry"], dict)

    @pytest.mark.asyncio
    async def test_app_scope_shared_across_sessions(self) -> None:
        """app: scope keys are accessible from a different session with the same app_name."""
        session_service = create_session_service(TEST_DB_URL)
        sid_a = f"scope_a_{uuid.uuid4().hex[:8]}"
        sid_b = f"scope_b_{uuid.uuid4().hex[:8]}"

        # Session A writes app: scope
        await session_service.create_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id="user_x",
            session_id=sid_a,
            state={"app:shared_flag": "yes"},
        )

        # Session B (different user, different session) reads app: scope
        await session_service.create_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id="user_y",
            session_id=sid_b,
        )
        retrieved = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME, user_id="user_y", session_id=sid_b
        )
        assert retrieved is not None
        state: dict[str, object] = retrieved.state  # type: ignore[reportUnknownMemberType]
        assert state.get("app:shared_flag") == "yes"

    @pytest.mark.asyncio
    async def test_user_scope_shared_across_sessions(self) -> None:
        """user: scope keys are accessible across sessions with the same user_id."""
        session_service = create_session_service(TEST_DB_URL)
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        sid_1 = f"usess_1_{uuid.uuid4().hex[:8]}"
        sid_2 = f"usess_2_{uuid.uuid4().hex[:8]}"

        # Session 1 writes user: scope
        await session_service.create_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id=user_id,
            session_id=sid_1,
            state={"user:preference": "dark"},
        )

        # Session 2 (same user, different session) should see user: scope
        await session_service.create_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id=user_id,
            session_id=sid_2,
        )
        retrieved = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME, user_id=user_id, session_id=sid_2
        )
        assert retrieved is not None
        state: dict[str, object] = retrieved.state  # type: ignore[reportUnknownMemberType]
        assert state.get("user:preference") == "dark"

    @pytest.mark.asyncio
    async def test_temp_scope_not_persisted(self) -> None:
        """temp: scope keys are cleared between session retrievals."""
        session_service = create_session_service(TEST_DB_URL)
        session_id = f"temp_{uuid.uuid4().hex[:8]}"

        # Create session with temp: and session-scope keys
        await session_service.create_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME,
            user_id="system",
            session_id=session_id,
            state={
                "temp:scratch": "ephemeral",
                "persistent_key": "durable",
            },
        )

        # Retrieve — temp: keys should be stripped by DatabaseSessionService
        retrieved = await session_service.get_session(  # type: ignore[reportUnknownMemberType]
            app_name=APP_NAME, user_id="system", session_id=session_id
        )
        assert retrieved is not None
        state: dict[str, object] = retrieved.state  # type: ignore[reportUnknownMemberType]
        # Session-scope key persists
        assert state.get("persistent_key") == "durable"
        # temp: key should NOT persist (ADK strips temp: prefix on retrieval)
        assert "temp:scratch" not in state


# ---------------------------------------------------------------------------
# Build-Time Skill Resolution Tests
# ---------------------------------------------------------------------------


def _make_skill_entry(
    name: str,
    *,
    applies_to: list[str] | None = None,
    trigger_type: TriggerType = TriggerType.ALWAYS,
    priority: int = 0,
) -> SkillEntry:
    """Create a SkillEntry for testing."""
    return SkillEntry(
        name=name,
        description=f"Test skill: {name}",
        triggers=[TriggerSpec(trigger_type=trigger_type, value="")],
        applies_to=applies_to or [],
        priority=priority,
        path=Path(f"/fake/{name}/SKILL.md"),
    )


def _make_mock_skill_library(
    entries: list[SkillEntry],
) -> MagicMock:
    """Create a mock SkillLibrary that returns given entries for any match."""
    lib = MagicMock(spec=SkillLibrary)
    lib.match.return_value = entries
    lib.resolve_cascades.side_effect = lambda e: e  # type: ignore[reportUnknownLambdaType]

    def _load(entry: SkillEntry) -> SkillContent:
        return SkillContent(entry=entry, content=f"Content for {entry.name}")

    lib.load.side_effect = _load
    return lib


class TestResolveSkillsForAgent:
    """Unit tests for _resolve_skills_for_agent."""

    def test_returns_base_ctx_when_no_library(self) -> None:
        ctx = InstructionContext(agent_name="director")
        result = _resolve_skills_for_agent(None, "director", "director", ctx)
        assert result is ctx

    def test_resolves_skills_into_new_context(self) -> None:
        entry = _make_skill_entry("governance", applies_to=["director"])
        lib = _make_mock_skill_library([entry])
        base_ctx = InstructionContext(project_config="test project")

        result = _resolve_skills_for_agent(lib, "director", "director", base_ctx)

        assert result is not base_ctx
        assert "governance" in result.loaded_skills
        assert result.loaded_skills["governance"]["content"] == "Content for governance"
        assert result.loaded_skills["governance"]["applies_to"] == ["director"]
        assert result.project_config == "test project"
        assert result.agent_name == "director"

    def test_merges_with_existing_skills(self) -> None:
        existing_skill = LoadedSkillData(
            content="Existing content",
            applies_to=[],
            matched_triggers=["always"],
        )
        base_ctx = InstructionContext(
            loaded_skills={"existing": existing_skill},
        )
        entry = _make_skill_entry("new-skill")
        lib = _make_mock_skill_library([entry])

        result = _resolve_skills_for_agent(lib, "director", "director", base_ctx)

        assert "existing" in result.loaded_skills
        assert "new-skill" in result.loaded_skills

    def test_calls_match_with_role_context(self) -> None:
        lib = _make_mock_skill_library([])
        base_ctx = InstructionContext()

        _resolve_skills_for_agent(lib, "pm", "PM_123", base_ctx)

        lib.match.assert_called_once()
        call_ctx = lib.match.call_args[0][0]
        assert isinstance(call_ctx, SkillMatchContext)
        assert call_ctx.agent_role == "pm"

    def test_calls_resolve_cascades(self) -> None:
        entry = _make_skill_entry("cascading")
        lib = _make_mock_skill_library([entry])
        base_ctx = InstructionContext()

        _resolve_skills_for_agent(lib, "director", "director", base_ctx)

        lib.resolve_cascades.assert_called_once()


class TestBuildChatSessionAgentSkills:
    """Test that build_chat_session_agent resolves Director skills."""

    def test_accepts_skill_library_kwarg(self) -> None:
        """build_chat_session_agent passes skill_library through."""
        mock_registry = MagicMock()
        mock_registry.build.return_value = MagicMock()
        ctx = InstructionContext(agent_name="director")

        entry = _make_skill_entry("director-governance", applies_to=["director"])
        lib = _make_mock_skill_library([entry])

        build_chat_session_agent(mock_registry, ctx, skill_library=lib)

        # Verify registry.build was called with an InstructionContext containing skills
        call_args = mock_registry.build.call_args
        built_ctx = call_args[0][1]
        assert isinstance(built_ctx, InstructionContext)
        assert "director-governance" in built_ctx.loaded_skills

    def test_works_without_skill_library(self) -> None:
        """build_chat_session_agent works with no skill_library (backward compat)."""
        mock_registry = MagicMock()
        mock_registry.build.return_value = MagicMock()
        ctx = InstructionContext(agent_name="director")

        build_chat_session_agent(mock_registry, ctx)

        call_args = mock_registry.build.call_args
        built_ctx = call_args[0][1]
        assert isinstance(built_ctx, InstructionContext)
        assert len(built_ctx.loaded_skills) == 0


class TestBuildWorkSessionAgentsSkills:
    """Test Director/PM independent skill resolution in build_work_session_agents."""

    @pytest.mark.asyncio
    async def test_director_and_pm_get_independent_skills(self) -> None:
        """Director and PM each get their own InstructionContext with resolved skills."""
        from app.workers.adk import build_work_session_agents

        director_skill = _make_skill_entry("director-gov", applies_to=["director"])
        pm_skill = _make_skill_entry("pm-management", applies_to=["pm"])
        universal_skill = _make_skill_entry("universal-conventions")

        # Library returns different entries based on agent_role context
        lib = MagicMock(spec=SkillLibrary)
        lib.resolve_cascades.side_effect = lambda e: e  # type: ignore[reportUnknownLambdaType]

        def _match(context: SkillMatchContext) -> list[SkillEntry]:
            if context.agent_role == "director":
                return [director_skill, universal_skill]
            if context.agent_role == "pm":
                return [pm_skill, universal_skill]
            return []

        def _load_skill_a(entry: SkillEntry) -> SkillContent:
            return SkillContent(entry=entry, content=f"Content for {entry.name}")

        lib.match.side_effect = _match
        lib.load.side_effect = _load_skill_a

        mock_registry = MagicMock()
        mock_agent = MagicMock()
        mock_registry.build.return_value = mock_agent

        mock_publisher = MagicMock()
        base_ctx = InstructionContext()

        mock_wf_registry = MagicMock()
        mock_wf_registry.get_manifest.return_value = MagicMock()
        mock_wf_registry.create_pipeline = AsyncMock(return_value=MagicMock())

        await build_work_session_agents(
            registry=mock_registry,
            ctx=base_ctx,
            project_id="test-project",
            publisher=mock_publisher,
            skill_library=lib,
            workflow_registry=mock_wf_registry,
        )

        # registry.build called twice: once for director, once for PM
        assert mock_registry.build.call_count == 2

        # First call: director
        director_call = mock_registry.build.call_args_list[0]
        director_built_ctx = director_call[0][1]
        assert isinstance(director_built_ctx, InstructionContext)
        assert "director-gov" in director_built_ctx.loaded_skills
        assert "universal-conventions" in director_built_ctx.loaded_skills

        # Second call: PM
        pm_call = mock_registry.build.call_args_list[1]
        pm_built_ctx = pm_call[0][1]
        assert isinstance(pm_built_ctx, InstructionContext)
        assert "pm-management" in pm_built_ctx.loaded_skills
        assert "universal-conventions" in pm_built_ctx.loaded_skills

        # Director should NOT have PM skills and vice versa
        assert "pm-management" not in director_built_ctx.loaded_skills
        assert "director-gov" not in pm_built_ctx.loaded_skills

    @pytest.mark.asyncio
    async def test_always_trigger_director_only_loads_for_director(self) -> None:
        """Skills with always+applies_to:[director] load only for Director."""
        from app.workers.adk import build_work_session_agents

        director_only = _make_skill_entry(
            "director-always", applies_to=["director"], trigger_type=TriggerType.ALWAYS
        )

        lib = MagicMock(spec=SkillLibrary)
        lib.resolve_cascades.side_effect = lambda e: e  # type: ignore[reportUnknownLambdaType]

        def _match(context: SkillMatchContext) -> list[SkillEntry]:
            # always trigger matches for all roles, but applies_to filters later
            if context.agent_role == "director":
                return [director_only]
            return []

        def _load_skill_b(entry: SkillEntry) -> SkillContent:
            return SkillContent(entry=entry, content=f"Content for {entry.name}")

        lib.match.side_effect = _match
        lib.load.side_effect = _load_skill_b

        mock_registry = MagicMock()
        mock_registry.build.return_value = MagicMock()
        mock_publisher = MagicMock()

        mock_wf_registry = MagicMock()
        mock_wf_registry.get_manifest.return_value = MagicMock()
        mock_wf_registry.create_pipeline = AsyncMock(return_value=MagicMock())

        await build_work_session_agents(
            registry=mock_registry,
            ctx=InstructionContext(),
            project_id="proj",
            publisher=mock_publisher,
            skill_library=lib,
            workflow_registry=mock_wf_registry,
        )

        # Director build has the skill
        director_ctx = mock_registry.build.call_args_list[0][0][1]
        assert "director-always" in director_ctx.loaded_skills

        # PM build does not
        pm_ctx = mock_registry.build.call_args_list[1][0][1]
        assert "director-always" not in pm_ctx.loaded_skills

    @pytest.mark.asyncio
    async def test_always_no_applies_to_loads_for_all(self) -> None:
        """Skills with always trigger and no applies_to load for all agents."""
        from app.workers.adk import build_work_session_agents

        universal = _make_skill_entry("project-wide", applies_to=[])

        def _load_skill_c(entry: SkillEntry) -> SkillContent:
            return SkillContent(entry=entry, content=f"Content for {entry.name}")

        lib = MagicMock(spec=SkillLibrary)
        lib.resolve_cascades.side_effect = lambda e: e  # type: ignore[reportUnknownLambdaType]
        lib.match.return_value = [universal]
        lib.load.side_effect = _load_skill_c

        mock_registry = MagicMock()
        mock_registry.build.return_value = MagicMock()
        mock_publisher = MagicMock()

        mock_wf_registry = MagicMock()
        mock_wf_registry.get_manifest.return_value = MagicMock()
        mock_wf_registry.create_pipeline = AsyncMock(return_value=MagicMock())

        await build_work_session_agents(
            registry=mock_registry,
            ctx=InstructionContext(),
            project_id="proj",
            publisher=mock_publisher,
            skill_library=lib,
            workflow_registry=mock_wf_registry,
        )

        # Both Director and PM should have the universal skill
        director_ctx = mock_registry.build.call_args_list[0][0][1]
        pm_ctx = mock_registry.build.call_args_list[1][0][1]
        assert "project-wide" in director_ctx.loaded_skills
        assert "project-wide" in pm_ctx.loaded_skills
