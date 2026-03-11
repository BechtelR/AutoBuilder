"""Event publisher — translates ADK events to gateway events and publishes to Redis Streams.

This module has ZERO google.adk imports. ADK event inspection uses getattr() only.
This is the outbound anti-corruption layer boundary.
"""

from datetime import UTC, datetime

from redis.asyncio import Redis

from app.events.streams import stream_publish
from app.gateway.models.events import PipelineEvent
from app.lib.logging import get_logger
from app.models.constants import TIER_PREFIX_WRITE_ACCESS
from app.models.enums import AgentTier, PipelineEventType, SupervisionEventType

logger = get_logger("events.publisher")

# Tier hierarchy: higher index = more privilege
_TIER_RANK: dict[AgentTier, int] = {
    AgentTier.WORKER: 0,
    AgentTier.PM: 1,
    AgentTier.DIRECTOR: 2,
}


def determine_agent_tier(agent_name: str) -> AgentTier:
    """Map an agent name to its authorization tier."""
    lower = agent_name.lower()
    if lower == "director":
        return AgentTier.DIRECTOR
    if lower.startswith("pm"):
        return AgentTier.PM
    return AgentTier.WORKER


def validate_state_delta(
    state_delta: dict[str, object],
    author_tier: AgentTier,
) -> list[str]:
    """Return list of keys the author_tier is not authorized to write.

    Empty list means all keys are authorized.
    """
    unauthorized: list[str] = []
    author_rank = _TIER_RANK[author_tier]

    for key in state_delta:
        required_tier: AgentTier | None = None
        for prefix, tier in TIER_PREFIX_WRITE_ACCESS.items():
            if key.startswith(prefix):
                required_tier = tier
                break

        if required_tier is None:
            # No recognized prefix — writable by all tiers
            continue

        if author_rank < _TIER_RANK[required_tier]:
            unauthorized.append(key)

    return unauthorized


def _get_parts(content_obj: object) -> list[object] | None:
    """Extract parts list from a content object via getattr. Returns None if absent."""
    parts: object = getattr(content_obj, "parts", None)
    if parts is not None and isinstance(parts, list):
        result: list[object] = parts  # type: ignore[reportUnknownVariableType]
        return result
    return None


class EventPublisher:
    """Translates ADK events to PipelineEvent and publishes to Redis Streams."""

    def __init__(self, redis: Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis
        self._seen_agents: set[str] = set()
        self._pending_violations: list[dict[str, object]] = []

    def translate(self, adk_event: object, workflow_id: str) -> PipelineEvent | None:
        """Convert an ADK Event to a gateway PipelineEvent. Returns None for unclassified."""
        author: str | None = getattr(adk_event, "author", None)
        content_obj: object = getattr(adk_event, "content", None)
        actions: object = getattr(adk_event, "actions", None)
        error_code: object = getattr(adk_event, "error_code", None)

        now = datetime.now(UTC)

        # Error events
        if error_code is not None:
            error_msg = str(getattr(adk_event, "error_message", "")) or str(error_code)
            return PipelineEvent(
                event_type=PipelineEventType.ERROR,
                workflow_id=workflow_id,
                timestamp=now,
                agent_name=author,
                content=error_msg,
            )

        # Content-based classification
        if content_obj is not None:
            parts = _get_parts(content_obj)
            if parts:
                part: object = parts[0]

                # Tool call
                fn_call: object = getattr(part, "function_call", None)
                if fn_call is not None:
                    fn_name = str(getattr(fn_call, "name", ""))
                    return PipelineEvent(
                        event_type=PipelineEventType.TOOL_CALLED,
                        workflow_id=workflow_id,
                        timestamp=now,
                        agent_name=author,
                        content=fn_name,
                        metadata={"function_name": fn_name},
                    )

                # Tool result
                fn_resp: object = getattr(part, "function_response", None)
                if fn_resp is not None:
                    return PipelineEvent(
                        event_type=PipelineEventType.TOOL_RESULT,
                        workflow_id=workflow_id,
                        timestamp=now,
                        agent_name=author,
                    )

        # State delta
        if actions is not None:
            raw_delta: object = getattr(actions, "state_delta", None)
            if raw_delta and isinstance(raw_delta, dict):
                # State key authorization check
                if author:
                    tier = determine_agent_tier(author)
                    violations = validate_state_delta(
                        raw_delta,  # type: ignore[arg-type]
                        tier,
                    )
                    if violations:
                        self._queue_state_auth_violation(
                            workflow_id=workflow_id,
                            author_name=author,
                            author_tier=tier,
                            unauthorized_keys=violations,
                            all_keys=list(raw_delta.keys()),  # type: ignore[reportUnknownArgumentType]
                        )

                return PipelineEvent(
                    event_type=PipelineEventType.STATE_UPDATED,
                    workflow_id=workflow_id,
                    timestamp=now,
                    agent_name=author,
                )

        # Final response check
        is_final: bool = False
        is_final_fn: object = getattr(adk_event, "is_final_response", None)
        if callable(is_final_fn):
            is_final = bool(is_final_fn())

        if is_final and author:
            self._seen_agents.discard(author)
            text_content: str | None = None
            if content_obj is not None:
                final_parts = _get_parts(content_obj)
                if final_parts:
                    text_val: object = getattr(final_parts[0], "text", None)
                    if text_val is not None:
                        text_content = str(text_val)
            return PipelineEvent(
                event_type=PipelineEventType.AGENT_COMPLETED,
                workflow_id=workflow_id,
                timestamp=now,
                agent_name=author,
                content=text_content,
            )

        # Agent started (first event from this author)
        if author and author not in self._seen_agents:
            self._seen_agents.add(author)
            return PipelineEvent(
                event_type=PipelineEventType.AGENT_STARTED,
                workflow_id=workflow_id,
                timestamp=now,
                agent_name=author,
            )

        # Unclassified — skip
        return None

    async def publish(self, event: PipelineEvent) -> None:
        """Publish a PipelineEvent to the workflow's Redis Stream."""
        data = event.model_dump_json()
        await stream_publish(self._redis, event.workflow_id, data)

    async def publish_lifecycle(
        self,
        workflow_id: str,
        event_type: PipelineEventType,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Publish a synthetic lifecycle event (STARTED, COMPLETED, FAILED)."""
        event = PipelineEvent(
            event_type=event_type,
            workflow_id=workflow_id,
            timestamp=datetime.now(UTC),
            metadata=metadata or {},
        )
        await self.publish(event)

    def _queue_state_auth_violation(
        self,
        workflow_id: str,
        author_name: str,
        author_tier: AgentTier,
        unauthorized_keys: list[str],
        all_keys: list[str],
    ) -> None:
        """Log and queue a state auth violation for async publishing."""
        logger.warning(
            "State auth violation: agent=%s tier=%s unauthorized_keys=%s",
            author_name,
            author_tier,
            unauthorized_keys,
        )
        self._pending_violations.append(
            {
                "workflow_id": workflow_id,
                "author_name": author_name,
                "author_tier": str(author_tier),
                "unauthorized_keys": unauthorized_keys,
                "all_keys": all_keys,
            }
        )

    async def publish_state_auth_violation(
        self,
        workflow_id: str,
        author_name: str,
        author_tier: AgentTier,
        unauthorized_keys: list[str],
        all_keys: list[str],
    ) -> None:
        """Publish a state authorization violation as an ERROR event."""
        await self.publish_lifecycle(
            workflow_id=workflow_id,
            event_type=PipelineEventType.ERROR,
            metadata={
                "violation": SupervisionEventType.STATE_AUTH_VIOLATION,
                "author_name": author_name,
                "author_tier": str(author_tier),
                "unauthorized_keys": unauthorized_keys,
                "all_keys": all_keys,
            },
        )

    async def flush_violations(self) -> None:
        """Publish all queued state auth violations."""
        violations = self._pending_violations.copy()
        self._pending_violations.clear()
        for v in violations:
            await self.publish_state_auth_violation(
                workflow_id=v["workflow_id"],  # type: ignore[arg-type]
                author_name=v["author_name"],  # type: ignore[arg-type]
                author_tier=AgentTier(v["author_tier"]),
                unauthorized_keys=v["unauthorized_keys"],  # type: ignore[arg-type]
                all_keys=v["all_keys"],  # type: ignore[arg-type]
            )
