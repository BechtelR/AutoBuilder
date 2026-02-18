"""Tests for Redis cache helpers."""

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.lib.cache import cache_delete, cache_get, cache_set
from tests.conftest import require_redis


@require_redis
class TestCacheHelpers:
    @pytest.mark.asyncio
    async def test_set_and_get_roundtrip(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        await cache_set(redis_client, "test:key", "hello")
        result = await cache_get(redis_client, "test:key")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_get_returns_none_on_miss(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        result = await cache_get(redis_client, "nonexistent:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_value(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        await cache_set(redis_client, "test:del", "value")
        await cache_delete(redis_client, "test:del")
        result = await cache_get(redis_client, "test:del")
        assert result is None

    @pytest.mark.asyncio
    async def test_ttl_is_set(
        self,
        redis_client: Redis,  # type: ignore[type-arg]
    ) -> None:
        await cache_set(redis_client, "test:ttl", "temp", ttl=10)
        ttl = await redis_client.ttl("test:ttl")
        assert 0 < ttl <= 10


class TestCacheDegradedPath:
    """Degraded-path tests using broken connection URL, not mocks."""

    @pytest.mark.asyncio
    async def test_cache_set_raises_on_broken_redis(self) -> None:
        broken: Redis = Redis.from_url("redis://localhost:19999")  # type: ignore[type-arg]
        with pytest.raises(RedisConnectionError):
            await cache_set(broken, "test:key", "value")
        await broken.aclose()

    @pytest.mark.asyncio
    async def test_cache_get_raises_on_broken_redis(self) -> None:
        broken: Redis = Redis.from_url("redis://localhost:19999")  # type: ignore[type-arg]
        with pytest.raises(RedisConnectionError):
            await cache_get(broken, "test:key")
        await broken.aclose()
