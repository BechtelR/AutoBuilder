"""Redis Stream helpers — publish and read with enforced naming convention."""

from redis.asyncio import Redis


def stream_key(workflow_id: str) -> str:
    """Return the Redis Stream key for a workflow's event stream."""
    return f"workflow:{workflow_id}:events"


async def stream_publish(
    redis: Redis,  # type: ignore[type-arg]
    workflow_id: str,
    data: str,
) -> str:
    """Publish data to a workflow's event stream via XADD. Returns the entry ID."""
    entry_id: bytes = await redis.xadd(  # type: ignore[reportUnknownMemberType]
        stream_key(workflow_id), {"data": data}
    )
    return entry_id.decode()


async def stream_read_range(
    redis: Redis,  # type: ignore[type-arg]
    workflow_id: str,
    start: str = "-",
    end: str = "+",
    count: int | None = None,
) -> list[tuple[str, dict[str, str]]]:
    """Read events from a workflow stream via XRANGE."""
    raw: list[  # type: ignore[reportUnknownMemberType]
        tuple[bytes, dict[bytes, bytes]]
    ] = await redis.xrange(stream_key(workflow_id), min=start, max=end, count=count)
    result: list[tuple[str, dict[str, str]]] = []
    for entry_id_raw, fields_raw in raw:
        entry_id = entry_id_raw.decode()
        fields: dict[str, str] = {k.decode(): v.decode() for k, v in fields_raw.items()}
        result.append((entry_id, fields))
    return result
