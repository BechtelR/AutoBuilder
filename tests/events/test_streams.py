"""Tests for Redis Stream helpers."""

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.events.streams import stream_key, stream_publish, stream_read_range
from tests.conftest import require_redis


class TestStreamKey:
    def test_stream_key_format(self) -> None:
        assert stream_key("abc") == "workflow:abc:events"

    def test_stream_key_with_uuid(self) -> None:
        assert stream_key("550e8400-e29b-41d4-a716-446655440000") == (
            "workflow:550e8400-e29b-41d4-a716-446655440000:events"
        )


@require_redis
class TestStreamPublish:
    @pytest.mark.asyncio
    async def test_publish_returns_entry_id(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        entry_id = await stream_publish(redis_client, "test-wf-1", '{"event": "test"}')
        assert isinstance(entry_id, str)
        assert "-" in entry_id  # Redis stream IDs have format "timestamp-sequence"

    @pytest.mark.asyncio
    async def test_publish_and_read_roundtrip(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        await stream_publish(redis_client, "test-wf-2", '{"event": "first"}')
        await stream_publish(redis_client, "test-wf-2", '{"event": "second"}')

        events = await stream_read_range(redis_client, "test-wf-2")
        assert len(events) == 2
        assert events[0][1]["data"] == '{"event": "first"}'
        assert events[1][1]["data"] == '{"event": "second"}'

    @pytest.mark.asyncio
    async def test_read_empty_stream(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        events = await stream_read_range(redis_client, "nonexistent-wf")
        assert events == []

    @pytest.mark.asyncio
    async def test_read_with_count_limit(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        for i in range(5):
            await stream_publish(redis_client, "test-wf-3", f'{{"n": {i}}}')
        events = await stream_read_range(redis_client, "test-wf-3", count=2)
        assert len(events) == 2


class TestStreamDegradedPath:
    """Degraded-path tests using broken connection URL, not mocks."""

    @pytest.mark.asyncio
    async def test_publish_raises_on_broken_redis(self) -> None:
        broken: Redis = Redis.from_url("redis://localhost:19999")  # type: ignore[type-arg]
        with pytest.raises(RedisConnectionError):
            await stream_publish(broken, "test-wf", '{"event": "test"}')
        await broken.aclose()
