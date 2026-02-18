"""Redis cache helpers — get, set, delete with TTL."""

from redis.asyncio import Redis


async def cache_get(redis: Redis, key: str) -> str | None:  # type: ignore[type-arg]
    """Retrieve a cached value. Returns None on miss."""
    result: bytes | None = await redis.get(key)  # type: ignore[reportUnknownMemberType]
    if result is None:
        return None
    return result.decode()


async def cache_set(
    redis: Redis,  # type: ignore[type-arg]
    key: str,
    value: str,
    ttl: int = 3600,
) -> None:
    """Store a value with TTL in seconds."""
    await redis.set(key, value, ex=ttl)  # type: ignore[reportUnknownMemberType]


async def cache_delete(redis: Redis, key: str) -> None:  # type: ignore[type-arg]
    """Remove a cached value."""
    await redis.delete(key)  # type: ignore[reportUnknownMemberType]
