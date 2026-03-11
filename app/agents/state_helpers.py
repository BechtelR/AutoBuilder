"""State extraction helpers and callback composition utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse

T = TypeVar("T")


def context_from_state(
    state: dict[str, object],
    key: str,
    expected_type: type[T],
    *,
    required: bool = True,
    default: T | None = None,
) -> T | None:
    """Extract typed value from session state.

    Raises:
        ValueError: For missing required keys or type mismatches.
    """
    value = state.get(key)
    if value is None:
        if required:
            raise ValueError(f"Required state key '{key}' not found in session state")
        return default
    if not isinstance(value, expected_type):
        raise ValueError(
            f"State key '{key}' expected type {expected_type.__name__}, got {type(value).__name__}"
        )
    return value


async def load_project_config(
    db_session_factory: Callable[..., object],
    project_name: str | None,
) -> dict[str, object] | None:
    """Load project config from project_configs table.

    Args:
        db_session_factory: Async context manager that yields an AsyncSession.
        project_name: Project name to look up in project_configs.

    Returns:
        Config dict or None if not found or project_name is None.
    """
    if project_name is None:
        return None
    # Import here to avoid circular imports
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models import ProjectConfig

    async with db_session_factory() as session:  # type: ignore[operator]
        assert isinstance(session, AsyncSession)
        result = await session.execute(
            select(ProjectConfig).where(ProjectConfig.project_name == project_name)
        )
        config_row = result.scalar_one_or_none()
        if config_row is None:
            return None
        return config_row.config  # type: ignore[return-value]


def compose_callbacks(
    *callbacks: Callable[[CallbackContext, LlmRequest], LlmResponse | None],
) -> Callable[[CallbackContext, LlmRequest], LlmResponse | None]:
    """Chain multiple before_model_callbacks. First non-None return wins."""

    def composed(ctx: CallbackContext, req: LlmRequest) -> LlmResponse | None:
        for cb in callbacks:
            result = cb(ctx, req)
            if result is not None:
                return result
        return None

    return composed


def create_system_reminder_callback() -> Callable[
    [CallbackContext, LlmRequest], LlmResponse | None
]:
    """Create a before_model_callback that injects ephemeral system reminders.

    Writes transient reminders to ``_system_reminders`` state key.
    Agent definitions can reference ``{_system_reminders?}`` for injection.
    Returns None always — never blocks the request.
    """

    def _system_reminder(
        ctx: CallbackContext,
        req: LlmRequest,  # noqa: ARG001
    ) -> LlmResponse | None:
        reminders: list[str] = []

        budget_pct = ctx.state.get("context_budget_used_pct")
        if isinstance(budget_pct, (int, float)) and budget_pct > 50:
            reminders.append(f"Context budget: {budget_pct:.0f}% used")

        if reminders:
            ctx.state["_system_reminders"] = "\n".join(reminders)
        else:
            ctx.state["_system_reminders"] = ""

        return None

    return _system_reminder


def create_context_injection_callback() -> Callable[
    [CallbackContext, LlmRequest], LlmResponse | None
]:
    """Context injection callback. No-op placeholder; wired in Phase 9 (memory service)."""

    def _inject_context(ctx: CallbackContext, req: LlmRequest) -> LlmResponse | None:  # noqa: ARG001
        return None

    return _inject_context
