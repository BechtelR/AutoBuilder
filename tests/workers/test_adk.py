"""Tests for ADK engine factory functions."""

import uuid

import pytest
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.genai.types import Content, Part

from app.models.constants import APP_NAME
from app.workers.adk import (
    LoggingPlugin,
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
