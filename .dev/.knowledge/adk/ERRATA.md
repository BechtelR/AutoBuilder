# ADK Errata & Gotchas

Empirically discovered behaviors in Google ADK that differ from documentation expectations or have non-obvious implications. Verified against ADK v1.25.0 with `InMemoryRunner` and live Claude API calls via LiteLLM.

---

## 1. Direct State Writes in CustomAgent Do NOT Persist (CRITICAL)

**Severity:** Critical — affects all CustomAgent implementations.

**Behavior:** Inside `BaseAgent._run_async_impl(ctx)`, writing directly to `ctx.session.state["key"] = value` modifies the in-memory dict but does NOT persist to the session service. When the session is later retrieved via `session_service.get_session()`, direct writes are absent.

**Only `state_delta` persists:**
```python
# ❌ DOES NOT PERSIST — value lost after run completes
ctx.session.state["lint_passed"] = True

# ✅ PERSISTS — applied to session service via event processing
yield Event(
    author=self.name,
    actions=EventActions(state_delta={"lint_passed": True}),
)
```

**Direct reads still work:** After a sub-agent yields events with `state_delta` or `output_key`, `ctx.session.state.get("key")` returns the updated value within the same execution. This is because ADK applies incoming `state_delta` from sub-agent events to `ctx.session.state`.

**Pattern for CustomAgent state writes:**
```python
async def _run_async_impl(self, ctx):
    # ✅ Read from state (works — ADK applies sub-agent state_delta)
    plan = ctx.session.state.get("plan_output", "")

    # ✅ Write via state_delta (persists to session service)
    delta = {"lint_passed": True, "lint_results": "..."}
    yield Event(
        author=self.name,
        actions=EventActions(state_delta=delta),
    )
```

**Discovered:** Phase 1 prototype validation. All 4 prototypes initially used direct writes per spec Decision D9; all CustomAgent state was invisible after execution. Switching to `state_delta` resolved immediately.

**ADK docs reference:** `adk/components/sessions-state.md` warns about direct modification on retrieved sessions. This errata extends that warning: it also applies to `ctx.session.state` inside `_run_async_impl`.

---

## 2. InMemoryRunner Defaults `auto_create_session=False`

**Severity:** Medium — affects all test harness code.

**Behavior:** `InMemoryRunner.__init__()` does not expose or pass `auto_create_session` to the parent `Runner.__init__()`, so it defaults to `False`. Passing a `session_id` to `run_async()` raises `ValueError: Session not found` unless the session already exists.

**Workaround:**
```python
runner = InMemoryRunner(agent=agent, app_name="test")
runner.auto_create_session = True  # Must set after construction
```

**Alternative:** Pre-create sessions via `runner.session_service.create_session()` before calling `run_async()`.

**Discovered:** Phase 1 — all 11 tests failed with `ValueError: Session not found` before adding this workaround.

---

## 3. FunctionTool Import Path (pyright strict)

**Severity:** Low — cosmetic type-checker issue.

**Behavior:** `from google.adk.tools import FunctionTool` triggers pyright `reportPrivateImportUsage` because `FunctionTool` is re-exported from a private module.

**Workaround:** Import directly:
```python
from google.adk.tools.function_tool import FunctionTool  # ✅ No pyright warning
```

---

## 4. BaseAgent._run_async_impl Override Signature (pyright strict)

**Severity:** Low — framework typing limitation.

**Behavior:** Custom `BaseAgent` subclasses require `# type: ignore[override]` on `_run_async_impl` due to return type mismatch between the base class signature and the async generator implementation.

**Workaround:**
```python
class MyAgent(BaseAgent):
    async def _run_async_impl(  # type: ignore[override]
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        ...
```

---

## 5. Pydantic Field(default_factory=list) Type Inference (pyright strict)

**Severity:** Low — Pydantic + pyright strict interaction.

**Behavior:** `features: list[Feature] = Field(default_factory=list)` infers as `list[Unknown]` in pyright strict mode.

**Workaround:**
```python
features: list[Feature] = Field(default_factory=lambda: list[Feature]())
```

---

## 6. ParallelAgent sub_agents Type Variance (pyright strict)

**Severity:** Low — standard Python variance issue.

**Behavior:** `ParallelAgent(sub_agents=[LlmAgent(...)])` fails pyright strict because `list[LlmAgent]` is not assignable to `list[BaseAgent]` (list is invariant in Python).

**Workaround:**
```python
sub_agents: list[BaseAgent] = [LlmAgent(...), LlmAgent(...)]
```

---

## 7. Token Usage via LiteLLM — VERIFIED WORKING

**Previous concern:** `event.usage_metadata` might not propagate token counts through LiteLLM.

**Result:** Both `prompt_token_count` and `candidates_token_count` are populated and accurate when using `LiteLlm(model="anthropic/claude-sonnet-4-5-20250929")`.

---

*Verified: 2026-02-13 | ADK Version: 1.25.0 | LiteLLM Provider: Anthropic Claude*
