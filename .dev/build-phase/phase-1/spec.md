# Phase 1 Spec: ADK Prototype Validation
*Generated: 2026-02-12*

## Overview

Five focused prototypes validate that Google ADK can serve as AutoBuilder's orchestration engine. P1–P4 validate core ADK patterns with Claude via LiteLLM. P5 validates that alternate providers (OpenAI, Gemini) work through the same LiteLLM+ADK pipeline — critical since these are production fallback providers. If P1 or P4 fail, re-evaluate Pydantic AI. If P5 fails for a provider, that provider cannot serve as a fallback.

Prototypes are structured as pytest integration tests in `tests/phase1/`. They use `InMemoryRunner` (no infrastructure dependencies — no Redis, PostgreSQL, or Docker required). Tests auto-skip per provider when the corresponding API key is not set (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`).

**ADK version**: 1.25.0 (installed, all import paths verified)

## Prerequisites

**Phase 0 — MET**

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Project scaffold exists | MET | All directories per `03-STRUCTURE.md` present with `__init__.py` |
| Dependencies installable | MET | `uv sync` succeeds; google-adk 1.25.0 installed |
| `ruff check .` passes | MET | 0 errors |
| `pyright` passes (strict) | MET | 0 errors |
| `pytest` runs | MET | 3 tests collected, 3 passed |
| Configuration loads | MET | `app.config.settings.Settings` loads from env |
| Shared models importable | MET | `app.models.enums`, `app.models.base`, `app.models.constants` |
| Docker (PostgreSQL + Redis) | N/A | Not required — all prototypes use `InMemoryRunner` |

## Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Test location | `tests/phase1/` | Prototypes are validation tests — pytest-runnable, structured, repeatable |
| 2 | Runner | `InMemoryRunner` | Zero infrastructure deps; validates ADK logic without Redis/PostgreSQL |
| 3 | API key handling | Auto-skip via `pytest.mark.skipif` | Prototypes make real API calls; CI can skip; local dev requires key |
| 4 | Tool implementations | Minimal wrappers in temp dirs | Validate the FunctionTool pattern, not production tools (Phase 4) |
| 5 | Models for parallel tests | Haiku for P3/P4, Sonnet for P1/P2 | Minimize API cost; P3 runs 3 concurrent LLM calls, P4 runs 5 |
| 6 | P4 test features | Synthetic text-generation tasks | Validates orchestration without real code generation |
| 7 | Event collection | List accumulation from `run_async()` | Collect all events into list for assertions |
| 8 | BaseAgent subclasses | Pydantic v2 model fields | ADK BaseAgent is a Pydantic model — custom attrs must be model fields, not `__init__` params |
| 9 | State writes in CustomAgent | `Event(actions=EventActions(state_delta={...}))` | **REVISED**: Direct `ctx.session.state` writes do NOT persist. All CustomAgent state writes must use `state_delta`. |
| 10 | Alternate provider testing | Cheapest models per provider, per-provider skip markers | Validates LiteLLM translation layer works for tool calling + response parsing across all 3 providers. Uses cheapest tier to minimize cost. |
| 11 | Gemini via LiteLlm (not native) | `LiteLlm(model="gemini/...")` | AutoBuilder routes everything through LiteLLM for consistency. Must validate Gemini through LiteLlm wrapper, not native ADK Gemini support. |

## Deliverables

### P1.D1: Test Infrastructure for Phase 1

**Files:** `tests/phase1/__init__.py`, `tests/phase1/conftest.py`
**Depends on:** —

**Description:** Create the test infrastructure for all Phase 1 prototypes. Shared pytest fixtures for `InMemoryRunner` instantiation, temporary directory management, API key skip logic, and event collection helpers. The conftest establishes the pattern all prototype tests follow.

**Acceptance criteria:**
- [x] `pytest tests/phase1/ --co` discovers test modules without error
- [x] Per-provider skip markers auto-skip tests when the corresponding API key is not set (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`)
- [x] Fixture provides `InMemoryRunner` factory accepting a root agent, returning runner instance
- [x] Fixture provides temporary directory for file tool tests (auto-cleaned via `tmp_path`)
- [x] `collect_events` async helper runs `runner.run_async()` and returns `(list[Event], Session)`

**Validation:** `uv run pytest tests/phase1/ --co`

---

### P1.D2: Prototype 1 — Basic Agent Loop + Claude via LiteLLM

**Files:** `tests/phase1/test_p1_basic_agent.py`
**Depends on:** P1.D1

**Description:** Validate three things: (1) Claude responds reliably through the `LiteLlm` wrapper in ADK's `LlmAgent`, (2) `FunctionTool` wrappers execute correctly when called by the agent, and (3) token usage is reported accurately. This is the foundational prototype — if Claude doesn't work through LiteLLM+ADK, nothing else matters.

**FunctionTool prototypes** (minimal — production tools come in Phase 4):
- `file_read(path: str) -> dict[str, str]` — read file contents from temp dir
- `file_write(path: str, content: str) -> dict[str, str]` — write file to temp dir
- `bash_exec(command: str) -> dict[str, str]` — subprocess with timeout

**Key API patterns:**
```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai import types

agent = LlmAgent(
    model=LiteLlm(model="anthropic/claude-sonnet-4-5-20250929"),
    name="test_agent",
    instruction="You are a helpful assistant.",
    tools=[FunctionTool(file_read), FunctionTool(file_write)],
)

runner = InMemoryRunner(agent=agent, app_name="test")
async for event in runner.run_async(
    user_id="test_user",
    session_id="test_session",
    new_message=types.Content(parts=[types.Part(text="Hello")])
):
    events.append(event)
```

**Acceptance criteria:**
- [x] `LlmAgent` with `LiteLlm(model="anthropic/claude-sonnet-4-5-20250929")` produces a non-empty text response
- [x] Agent successfully calls `file_read` tool and receives file contents
- [x] Agent successfully calls `file_write` tool and file is created on disk
- [x] Agent successfully calls `bash_exec` tool and receives command output
- [x] Token usage reported in events (`event.usage_metadata`) with `prompt_token_count > 0` and `candidates_token_count > 0`
- [x] Single request latency < 60s (generous bound; typical < 10s)

**Validation:** `uv run pytest tests/phase1/test_p1_basic_agent.py -v`

---

### P1.D3: Prototype 2 — Mixed Agent Coordination (LLM + Custom)

**Files:** `tests/phase1/test_p2_mixed_agents.py`
**Depends on:** P1.D2

**Description:** Validate that an `LlmAgent` and a `CustomAgent` (deterministic) compose in a `SequentialAgent` pipeline with shared state. The plan_agent (LLM) writes a plan to state via `output_key`; the linter_agent (CustomAgent, inheriting BaseAgent) reads it, runs a deterministic check, and writes results to state. Key validations: unified event stream contains events from both agent types, state persists across agents in the sequence.

**Key API patterns:**
```python
from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent

class LinterAgent(BaseAgent):
    """Deterministic agent — Pydantic v2 model, no extra fields needed."""
    async def _run_async_impl(self, ctx):
        plan = ctx.session.state.get("plan_output", "")
        has_steps = len(plan.strip()) > 0
        ctx.session.state["lint_results"] = f"Plan length: {len(plan)} chars"
        ctx.session.state["lint_passed"] = has_steps
        yield Event(author=self.name, actions=EventActions(state_delta={}))

pipeline = SequentialAgent(
    name="pipeline",
    sub_agents=[plan_agent, linter_agent]
)
```

**Acceptance criteria:**
- [x] `plan_agent` writes structured output to state via `output_key="plan_output"`
- [x] `linter_agent` (CustomAgent) reads `plan_output` from `ctx.session.state`
- [x] `linter_agent` emits Event objects visible in the event stream alongside LLM events
- [x] `lint_results` and `lint_passed` state keys are set after pipeline completes
- [x] Event stream contains events from both agent types (verified by `event.author`)

**Validation:** `uv run pytest tests/phase1/test_p2_mixed_agents.py -v`

---

### P1.D4: Prototype 3 — Parallel Execution

**Files:** `tests/phase1/test_p3_parallel.py`
**Depends on:** P1.D2

**Description:** Validate `ParallelAgent` with 3 `LlmAgent` instances executing concurrently. Each agent writes to a distinct state key via `output_key`. Key validations: no state collision between parallel agents, each produces topically relevant output, all events appear in the unified stream, and execution demonstrates concurrency.

**Key API patterns:**
```python
from google.adk.agents import LlmAgent, ParallelAgent

agents = [
    LlmAgent(name="ocean_agent", model=LiteLlm(model="anthropic/claude-haiku-4-5-20251001"),
             instruction="Write one sentence about the ocean.", output_key="agent_1_output"),
    LlmAgent(name="mountain_agent", model=LiteLlm(model="anthropic/claude-haiku-4-5-20251001"),
             instruction="Write one sentence about mountains.", output_key="agent_2_output"),
    LlmAgent(name="forest_agent", model=LiteLlm(model="anthropic/claude-haiku-4-5-20251001"),
             instruction="Write one sentence about forests.", output_key="agent_3_output"),
]
parallel = ParallelAgent(name="parallel_test", sub_agents=agents)
```

**Acceptance criteria:**
- [x] All 3 agents produce non-empty output in their respective state keys
- [x] No cross-contamination — each output relates to its assigned topic
- [x] Events from all 3 agents appear in the collected event stream
- [x] Total execution time < 3x the slowest single agent (demonstrates concurrency)
- [x] State keys `agent_1_output`, `agent_2_output`, `agent_3_output` all populated

**Validation:** `uv run pytest tests/phase1/test_p3_parallel.py -v`

---

### P1.D5: Prototype 4 — Dynamic Outer Loop (CustomAgent Orchestrator)

**Files:** `tests/phase1/test_p4_outer_loop.py`
**Depends on:** P1.D2, P1.D3, P1.D4

**Description:** Validate the core orchestration pattern: a `CustomAgent` (BaseAgent subclass) that dynamically constructs `ParallelAgent` batches based on feature dependencies, runs them in a "while incomplete features exist" loop. Tests with 5 synthetic features forming a dependency DAG. This is the most complex prototype and validates the dynamic batch composition pattern. In production, PM (LlmAgent) absorbs this orchestration role with mechanical batch parts as PM tools.

**Feature DAG:**
```
Feature A (no deps)     → Batch 1
Feature B (no deps)     → Batch 1
Feature C (depends: A)  → Batch 2
Feature D (depends: A)  → Batch 2
Feature E (depends: C, D) → Batch 3
```

**Key API patterns:**
```python
from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent
from pydantic import Field

class Feature(BaseModel):
    name: str
    depends_on: list[str] = Field(default_factory=list)
    prompt: str

class OuterLoopAgent(BaseAgent):
    """Pydantic v2 model — features stored as model field."""
    features: list[Feature] = Field(default_factory=list)

    async def _run_async_impl(self, ctx):
        completed: set[str] = set()
        batch_num = 0

        while len(completed) < len(self.features):
            ready = [f for f in self.features
                     if f.name not in completed
                     and all(d in completed for d in f.depends_on)]
            if not ready:
                break

            batch_num += 1
            sub_agents = [create_feature_agent(f) for f in ready]
            parallel = ParallelAgent(name=f"batch_{batch_num}", sub_agents=sub_agents)

            async for event in parallel.run_async(ctx):
                yield event

            for f in ready:
                if ctx.session.state.get(f"feature_{f.name}_output"):
                    completed.add(f.name)

        ctx.session.state["all_completed"] = len(completed) == len(self.features)
        ctx.session.state["completed_features"] = sorted(completed)
        ctx.session.state["total_batches"] = batch_num
```

**Acceptance criteria:**
- [x] Features execute in dependency order (A,B before C,D before E)
- [x] At least 2 parallel batches observed (batch 1: A+B, batch 2: C+D)
- [x] Loop terminates when all 5 features have completed
- [x] Each feature's output is written to state under `feature_{name}_output`
- [x] If a feature is simulated as "failed", independent features still execute (e.g., B fails → C,D still run since they depend on A, not B)
- [x] Outer loop agent state contains `all_completed`, `completed_features`, `total_batches`

**Validation:** `uv run pytest tests/phase1/test_p4_outer_loop.py -v`

---

### P1.D6: Document Go/No-Go Decision

**Files:** `.dev/.discussion/phase1-decision.md`
**Depends on:** P1.D2, P1.D3, P1.D4, P1.D5

**Description:** After running all prototypes, capture results in the decision table format from the roadmap. Document any ADK quirks, workarounds, or unexpected behaviors found during implementation. Record the go/no-go decision with rationale.

**Acceptance criteria:**
- [x] Decision table filled out with pass/fail for each prototype (P1–P4)
- [x] Quirks/workarounds section documents any issues encountered during implementation
- [x] Clear go/no-go recommendation with rationale
- [x] If any prototype fails, alternative approach documented

**Validation:** `cat .dev/.discussion/phase1-decision.md` (manual review)

---

### P1.D7: Prototype 5 — Alternate Provider Validation (OpenAI + Gemini)

**Files:** `tests/phase1/test_p5_alternate_providers.py`, `tests/phase1/conftest.py` (update)
**Depends on:** P1.D1, P1.D2

**Description:** Validate that OpenAI and Gemini models work through the same LiteLLM+ADK pipeline used for Claude. This is critical because these providers serve as production fallbacks (see `11-PROVIDERS.md`). Each provider's function calling format is different — LiteLLM must translate correctly for ADK's FunctionTool mechanism to work. Tests use the cheapest model per provider to minimize cost.

Each provider is tested independently with its own skip marker. A missing API key skips that provider's tests without failing the suite.

**conftest.py updates:**
```python
requires_openai_key = pytest.mark.skipif(
    "OPENAI_API_KEY" not in os.environ,
    reason="OPENAI_API_KEY not set — skipping OpenAI integration test",
)
requires_google_key = pytest.mark.skipif(
    "GOOGLE_API_KEY" not in os.environ,
    reason="GOOGLE_API_KEY not set — skipping Gemini integration test",
)
```

**Models under test** (cheapest per provider — see `11-PROVIDERS.md`):
- OpenAI: `LiteLlm(model="openai/gpt-5-nano")` — $0.05/$0.40 per 1M tokens
- Gemini: `LiteLlm(model="gemini/gemini-2.5-flash-lite")` — $0.10/$0.40 per 1M tokens

**Per-provider test cases:**
1. **Basic response** — `LlmAgent` produces non-empty text answer to a simple question
2. **Tool calling** — Agent successfully calls a `FunctionTool` (`file_write` + `file_read`) and uses the result in its response. This is the critical validation — each provider formats function calls differently, and LiteLLM must translate them correctly for ADK.
3. **Token usage** — `event.usage_metadata` reports non-zero token counts (soft assertion — log warning if absent, don't fail)

**Acceptance criteria:**
- [x] OpenAI: `LlmAgent` with `LiteLlm(model="openai/gpt-5-nano")` produces a non-empty text response
- [x] OpenAI: Agent successfully calls `FunctionTool` and receives tool result
- [x] Gemini: `LlmAgent` with `LiteLlm(model="gemini/gemini-2.5-flash-lite")` produces a non-empty text response
- [x] Gemini: Agent successfully calls `FunctionTool` and receives tool result
- [x] Each provider's tests skip cleanly when its API key is absent
- [x] Token usage logged per provider (warning if absent, not failure)

**Validation:** `uv run pytest tests/phase1/test_p5_alternate_providers.py -v`

---

## Build Order

```
Batch 1:              P1.D1                    # Test infrastructure (no deps)
Batch 2:              P1.D2                    # Basic agent (foundational)
Batch 3 (parallel):   P1.D3, P1.D4            # Mixed agents + Parallel (independent, both need D2)
Batch 4:              P1.D5                    # Outer loop (needs D2+D3+D4 patterns)
Batch 5:              P1.D7                    # Alternate providers (needs D1+D2 patterns)
Batch 6:              P1.D6                    # Document results (after all prototypes, update with P5 results)
```

## Completion Contract Traceability

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|----------------------------------|------------|------------|
| 1 | All 5 prototypes pass their criteria | P1.D2, P1.D3, P1.D4, P1.D5, P1.D7 | `uv run pytest tests/phase1/ -v` — all pass |
| 2 | Go/no-go decision documented in `.dev/.discussion/` | P1.D6 | File exists at `.dev/.discussion/phase1-decision.md` with completed decision table |
| 3 | Any ADK quirks or workarounds documented | P1.D6 | Quirks section present and populated in decision doc |
| 4 | Alternate providers validated as fallback-ready | P1.D7 | OpenAI + Gemini tests pass (basic response + tool calling) |

## Research Notes

### Verified Import Paths (ADK 1.25.0)
```python
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent, BaseAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.adk.events import Event, EventActions
from google.adk.tools import FunctionTool
from google.genai import types  # Content, Part
```

### InMemoryRunner Signatures
```python
# Constructor
InMemoryRunner(
    agent: BaseAgent | None = None,
    *,
    app_name: str | None = None,
    plugins: list[BasePlugin] | None = None,
    app: App | None = None,
    plugin_close_timeout: float = 5.0,
)

# Execution
runner.run_async(
    *,
    user_id: str,
    session_id: str,
    invocation_id: str | None = None,
    new_message: types.Content | None = None,    # NOT plain str
    state_delta: dict[str, Any] | None = None,
    run_config: RunConfig | None = None,
) -> AsyncGenerator[Event, None]

# Convenience (testing only)
runner.run_debug(
    user_messages: str | list[str],  # Accepts plain strings
    user_id: str = "debug_user_id",
    session_id: str = "debug_session_id",
) -> list[Event]
```

### Message Construction
```python
# For run_async — must wrap in Content/Part
new_message = types.Content(parts=[types.Part(text="Hello")])

# For run_debug — plain strings accepted
events = await runner.run_debug(user_messages="Hello")
```

### BaseAgent is a Pydantic v2 Model
Custom fields must be declared as Pydantic model fields:
```python
class MyAgent(BaseAgent):
    features: list[Feature] = Field(default_factory=list)  # Model field
    # NOT: def __init__(self, features, **kwargs): ...
```

### State Access in CustomAgent
```python
async def _run_async_impl(self, ctx):
    # Read
    value = ctx.session.state.get("key")
    # Write (direct)
    ctx.session.state["key"] = "value"
    # Write (event-sourced — visible in event stream)
    yield Event(author=self.name, actions=EventActions(state_delta={"key": "value"}))
```

### Token Usage
```python
# On events that carry LLM responses
if event.usage_metadata:
    event.usage_metadata.prompt_token_count      # Input tokens
    event.usage_metadata.candidates_token_count   # Output tokens
```

### ADK State Scopes
| Prefix | Scope | Persistence |
|--------|-------|-------------|
| *(none)* | Current session | If service persistent |
| `user:` | All sessions for user | If service persistent |
| `app:` | All users/sessions | If service persistent |
| `temp:` | Current invocation only | Never |

### Model Strings

See [.dev/11-PROVIDERS.md](../../11-PROVIDERS.md) for full model reference (all providers, pricing, context windows, fallback chains).
