# Phase 1: ADK Prototype Validation — Go/No-Go Decision

## Decision Table

| # | Prototype | Description | Status | Notes |
|---|-----------|-------------|--------|-------|
| P1 | Basic Agent Loop | Claude via LiteLLM + FunctionTool + token counting | PASS | Claude responds reliably (4s latency), tools execute correctly, token usage reported in `event.usage_metadata`. |
| P2 | Mixed Agent Coordination | SequentialAgent with LlmAgent + CustomAgent | PASS | `output_key` state passing works. CustomAgent events appear in unified stream alongside LLM events. |
| P3 | Parallel Execution | ParallelAgent with 3 concurrent LlmAgents | PASS | 3 agents complete in ~6s (vs ~18s sequential). No state collision. Topical output verified. |
| P4 | Dynamic Outer Loop | CustomAgent orchestrator with dependency-ordered ParallelAgent batches | PASS | 5-feature DAG executes in 3 correct batches (A,B → C,D → E). Loop terminates on completion. |
| P5 | Alternate Provider Validation | OpenAI + Gemini via LiteLLM with FunctionTools | PASS | OpenAI `gpt-5-nano` and Gemini `gemini-2.5-flash-lite` both respond, call FunctionTools, report token usage. LiteLLM provider-agnostic routing confirmed. |

## Live Test Results

All tests executed with live Claude API calls (`ANTHROPIC_API_KEY` set).

| Check | Result |
|-------|--------|
| `ruff check .` | 0 errors |
| `ruff format --check .` | All formatted |
| `pyright` (strict) | 0 errors |
| `pytest tests/phase1/ -v` | **13 passed** in 38.2s |

## Quirks and Workarounds

### 1. Direct State Writes Do Not Persist (CRITICAL)
- **Issue**: `ctx.session.state["key"] = value` inside `_run_async_impl` does NOT persist to the session service. Only `Event(actions=EventActions(state_delta={...}))` persists state.
- **Root cause**: ADK's session service only processes state changes delivered via `state_delta` on yielded Events. Direct dict mutations on the in-memory session object are local to the execution context and lost when the session is retrieved via `get_session()`.
- **Impact**: Spec Decision D9 ("direct writes for prototypes") is invalid. All CustomAgent state writes MUST use `state_delta`.
- **Resolution**: Updated all CustomAgents to use populated `state_delta` instead of direct writes. Direct reads from `ctx.session.state` still work (ADK applies incoming `state_delta` from sub-agents).
- **Severity**: **High** — affects all future CustomAgent implementations. This is the most important finding from Phase 1.

### 2. InMemoryRunner Requires `auto_create_session = True`
- **Issue**: `InMemoryRunner` defaults `auto_create_session=False`. Passing `session_id` to `run_async()` raises `ValueError: Session not found` unless the session is pre-created.
- **Root cause**: `InMemoryRunner.__init__` doesn't expose `auto_create_session` and doesn't pass it to the parent `Runner.__init__`, so it defaults to `False`.
- **Workaround**: Set `runner.auto_create_session = True` after construction.
- **Severity**: Medium — affects all test harness code using `InMemoryRunner`.

### 3. FunctionTool Import Path
- **Issue**: `from google.adk.tools import FunctionTool` triggers pyright `reportPrivateImportUsage`
- **Workaround**: Import from `google.adk.tools.function_tool` directly
- **Severity**: Low — cosmetic type-checker issue

### 4. ParallelAgent sub_agents Type Variance
- **Issue**: `ParallelAgent(sub_agents=[LlmAgent(...)])` fails pyright strict because `list[LlmAgent]` is not assignable to `list[BaseAgent]` (invariant list)
- **Workaround**: Explicitly annotate as `list[BaseAgent]`
- **Severity**: Low — standard Python variance issue, not ADK-specific

### 5. BaseAgent._run_async_impl Override Signature
- **Issue**: Custom BaseAgent subclasses require `# type: ignore[override]` on `_run_async_impl` due to return type mismatch in pyright strict
- **Workaround**: `# type: ignore[override]` comment
- **Severity**: Low — framework typing limitation

### 6. Field(default_factory=list) Type Inference
- **Issue**: `features: list[Feature] = Field(default_factory=list)` infers as `list[Unknown]` in pyright strict
- **Workaround**: Use `Field(default_factory=lambda: list[Feature]())`
- **Severity**: Low — Pydantic + pyright strict interaction

### 7. Token Usage via LiteLLM — VERIFIED WORKING
- **Previous concern**: Token counts might not propagate through LiteLLM to ADK events.
- **Result**: `event.usage_metadata.prompt_token_count` and `candidates_token_count` are both populated and accurate.
- **Severity**: Resolved — no longer a concern.

### 8. ADK Gemini via LiteLLM Warning
- **Issue**: ADK emits `UserWarning` when using Gemini via LiteLLM: "You are using Gemini via LiteLLM. For better performance, reliability, and access to latest features, consider using Gemini directly through ADK's native Gemini integration."
- **Root cause**: ADK detects `gemini/` model prefix and suggests native integration for optimization.
- **Impact**: AutoBuilder deliberately uses LiteLLM for all providers to maintain provider-agnostic routing architecture. Warning is cosmetic and does not affect functionality.
- **Workaround**: Suppress with `ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS=true` environment variable if needed.
- **Severity**: Low — cosmetic warning, no functional impact.

### 9. LiteLLM Async Success Handler Warning
- **Issue**: RuntimeWarning from `litellm_core_utils/logging_worker.py`: `Logging.async_success_handler` coroutine was never awaited.
- **Root cause**: LiteLLM internal logging worker may not properly await async handlers in some code paths.
- **Impact**: Cosmetic warning only — no functional impact on token counting, response handling, or event streaming.
- **Severity**: Low — cosmetic warning, no functional impact.

## Go/No-Go Recommendation

### **GO** — Proceed with ADK as orchestration engine

**Rationale:**
1. **All 5 prototypes pass with live LLM calls** — 13/13 tests pass in 38.2s
2. **Multi-provider validation complete** — Claude, OpenAI, and Gemini all work reliably via LiteLLM with consistent tool execution and accurate token counting
3. **Core patterns validated**:
   - LLM agents with FunctionTools (Phase 4 production tools)
   - Mixed LLM + deterministic pipelines (Phase 5 agent composition)
   - Parallel execution with state isolation (Phase 5 batch processing)
   - Dynamic orchestration loops (Phase 5 PM outer loop)
4. **Critical finding**: Direct state writes don't persist — all future CustomAgents MUST use `state_delta` (quirk #1)
5. **No blockers**: All quirks have clean workarounds

**Implications for Future Phases:**
- Spec Decision D9 is invalidated — production AND prototype agents must use `state_delta` for all state writes
- `common-errors.md` already documents the correct `state_delta` pattern (ADK CustomAgent section)
- `InMemoryRunner` test fixtures must set `auto_create_session = True`

**Next Steps:**
- Proceed to Phase 2 (Gateway + Infrastructure)

---

## Decision Finalized: 2026-02-14

**ADK is the committed orchestration engine for AutoBuilder.** This decision is final — no further re-evaluation of alternatives (Pydantic AI, LangGraph, etc.) unless ADK introduces a breaking regression that cannot be worked around.

Phase 1 prototype tests (`tests/phase1/`) are excluded from normal `pytest` runs (via `pyproject.toml` `--ignore`). They remain runnable on demand: `uv run pytest tests/phase1/ -v`.
