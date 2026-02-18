"""Tests for EventPublisher."""

import json

import pytest
from redis.asyncio import Redis

from app.events.publisher import EventPublisher
from app.events.streams import stream_read_range
from app.models.enums import PipelineEventType
from tests.conftest import require_redis


class FakeContent:
    """Mimics ADK Content with parts."""

    def __init__(self, parts: list[object] | None = None) -> None:
        self.parts = parts


class FakeFunctionCall:
    """Mimics a function call part."""

    def __init__(self, name: str) -> None:
        self.name = name


class FakeFunctionResponse:
    """Mimics a function response part."""

    def __init__(self) -> None:
        pass


class FakePart:
    """Mimics an ADK Part."""

    def __init__(
        self,
        text: str | None = None,
        function_call: FakeFunctionCall | None = None,
        function_response: FakeFunctionResponse | None = None,
    ) -> None:
        self.text = text
        self.function_call = function_call
        self.function_response = function_response


class FakeActions:
    """Mimics EventActions."""

    def __init__(self, state_delta: dict[str, object] | None = None) -> None:
        self.state_delta = state_delta


class FakeEvent:
    """Mimics an ADK Event for translation testing."""

    def __init__(
        self,
        author: str | None = None,
        content: FakeContent | None = None,
        actions: FakeActions | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        final: bool = False,
    ) -> None:
        self.author = author
        self.content = content
        self.actions = actions
        self.error_code = error_code
        self.error_message = error_message
        self._final = final

    def is_final_response(self) -> bool:
        return self._final


class TestTranslate:
    def _make_publisher(self) -> EventPublisher:
        # Publisher needs redis for publish(), but translate() doesn't use it
        return EventPublisher(None)  # type: ignore[arg-type]

    def test_tool_called(self) -> None:
        publisher = self._make_publisher()
        event = FakeEvent(
            author="echo_agent",
            content=FakeContent(parts=[FakePart(function_call=FakeFunctionCall("my_tool"))]),
        )
        result = publisher.translate(event, "wf-1")
        assert result is not None
        assert result.event_type == PipelineEventType.TOOL_CALLED
        assert result.content == "my_tool"
        assert result.metadata["function_name"] == "my_tool"

    def test_tool_result(self) -> None:
        publisher = self._make_publisher()
        event = FakeEvent(
            author="echo_agent",
            content=FakeContent(parts=[FakePart(function_response=FakeFunctionResponse())]),
        )
        result = publisher.translate(event, "wf-1")
        assert result is not None
        assert result.event_type == PipelineEventType.TOOL_RESULT

    def test_state_updated(self) -> None:
        publisher = self._make_publisher()
        event = FakeEvent(
            author="echo_agent",
            actions=FakeActions(state_delta={"key": "value"}),
        )
        result = publisher.translate(event, "wf-1")
        assert result is not None
        assert result.event_type == PipelineEventType.STATE_UPDATED

    def test_error(self) -> None:
        publisher = self._make_publisher()
        event = FakeEvent(
            author="echo_agent",
            error_code="SOME_ERROR",
            error_message="something broke",
        )
        result = publisher.translate(event, "wf-1")
        assert result is not None
        assert result.event_type == PipelineEventType.ERROR
        assert result.content == "something broke"

    def test_agent_started(self) -> None:
        publisher = self._make_publisher()
        event = FakeEvent(author="echo_agent")
        result = publisher.translate(event, "wf-1")
        assert result is not None
        assert result.event_type == PipelineEventType.AGENT_STARTED
        assert result.agent_name == "echo_agent"

    def test_agent_completed(self) -> None:
        publisher = self._make_publisher()
        # First event to register the agent
        publisher.translate(FakeEvent(author="echo_agent"), "wf-1")
        # Final response
        event = FakeEvent(
            author="echo_agent",
            content=FakeContent(parts=[FakePart(text="done")]),
            final=True,
        )
        result = publisher.translate(event, "wf-1")
        assert result is not None
        assert result.event_type == PipelineEventType.AGENT_COMPLETED
        assert result.content == "done"

    def test_unclassified_returns_none(self) -> None:
        publisher = self._make_publisher()
        # First event registers agent, second is unclassified
        publisher.translate(FakeEvent(author="echo_agent"), "wf-1")
        event = FakeEvent(author="echo_agent")
        result = publisher.translate(event, "wf-1")
        assert result is None


@require_redis
class TestPublish:
    @pytest.mark.asyncio
    async def test_publish_writes_to_stream(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        publisher = EventPublisher(redis_client)
        await publisher.publish_lifecycle("wf-pub-1", PipelineEventType.WORKFLOW_STARTED)
        events = await stream_read_range(redis_client, "wf-pub-1")
        assert len(events) == 1
        data = json.loads(events[0][1]["data"])
        assert data["event_type"] == "WORKFLOW_STARTED"
        assert data["workflow_id"] == "wf-pub-1"

    @pytest.mark.asyncio
    async def test_publish_lifecycle_completed(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        publisher = EventPublisher(redis_client)
        await publisher.publish_lifecycle("wf-pub-2", PipelineEventType.WORKFLOW_COMPLETED)
        events = await stream_read_range(redis_client, "wf-pub-2")
        assert len(events) == 1
        data = json.loads(events[0][1]["data"])
        assert data["event_type"] == "WORKFLOW_COMPLETED"

    @pytest.mark.asyncio
    async def test_publish_lifecycle_failed_with_metadata(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        publisher = EventPublisher(redis_client)
        await publisher.publish_lifecycle(
            "wf-pub-3",
            PipelineEventType.WORKFLOW_FAILED,
            metadata={"error": "something broke"},
        )
        events = await stream_read_range(redis_client, "wf-pub-3")
        assert len(events) == 1
        data = json.loads(events[0][1]["data"])
        assert data["event_type"] == "WORKFLOW_FAILED"
        assert data["metadata"]["error"] == "something broke"
