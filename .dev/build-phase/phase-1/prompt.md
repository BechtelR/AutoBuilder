# Phase 1: ADK Prototype Validation

## 1. Context

Read before starting:
- `CLAUDE.md` — project rules (loaded automatically)
- `.dev/03-STRUCTURE.md` — file placement truth
- `.dev/build-phase/phase-1/spec.md` — full spec (Overview, Design Decisions, Research Notes, ALL Deliverables)
- `.dev/05-AGENTS.md` — agent architecture patterns (CustomAgent, state communication, composition)
- `.dev/04-TECH_STACK.md` — technology choices (ADK, LiteLLM, model routing)
- `.dev/.knowledge/adk/models/litellm.md` — LiteLLM integration reference
- `.dev/.knowledge/adk/agents/custom-agents.md` — CustomAgent implementation pattern
- `.dev/.knowledge/adk/agents/sequential-agents.md` — SequentialAgent + output_key state passing
- `.dev/.knowledge/python-adk/google-adk-agents-ParallelAgent.md` — ParallelAgent state isolation
- `.dev/.knowledge/python-adk/google-adk-tools-function-tool.md` — FunctionTool auto-schema from type hints
- `.dev/.knowledge/python-adk/google-adk-runners.md` — InMemoryRunner API reference
- `.dev/.knowledge/python-adk/google-adk-events.md` — Event and EventActions reference

## 2. Objective

Implement Phase 1: ADK Prototype Validation. Four pytest integration tests validate critical ADK assumptions before committing to ADK as AutoBuilder's orchestration engine: (1) Claude reliability via LiteLLM, (2) mixed LLM + deterministic agent coordination, (3) parallel agent execution, and (4) dynamic outer-loop orchestration via CustomAgent. All prototypes use `InMemoryRunner` (zero infrastructure). Tests auto-skip when `ANTHROPIC_API_KEY` is absent. After all prototypes pass, document the go/no-go decision.

## 3. Success Criteria

From the roadmap's completion contract. ALL must pass.

- [ ] All 4 prototypes pass their acceptance criteria → verify: `uv run pytest tests/phase1/ -v`
- [ ] Go/no-go decision documented in `.dev/.discussion/` → verify: file exists at `.dev/.discussion/phase1-decision.md` with completed decision table
- [ ] Any ADK quirks or workarounds documented → verify: quirks section present and populated in `.dev/.discussion/phase1-decision.md`
- [ ] Quality gates pass → verify: `uv run ruff check . && uv run pyright && uv run pytest`

## 4. Scope

### Files to Create
- `tests/phase1/__init__.py` — package marker
- `tests/phase1/conftest.py` — shared fixtures (runner factory, API key skip, temp dir, event collector)
- `tests/phase1/test_p1_basic_agent.py` — Prototype 1: LlmAgent + LiteLlm + FunctionTool + token counting
- `tests/phase1/test_p2_mixed_agents.py` — Prototype 2: SequentialAgent with LlmAgent + CustomAgent
- `tests/phase1/test_p3_parallel.py` — Prototype 3: ParallelAgent with 3 concurrent LlmAgents
- `tests/phase1/test_p4_outer_loop.py` — Prototype 4: CustomAgent orchestrator with dynamic ParallelAgent batches
- `.dev/.discussion/phase1-decision.md` — Go/no-go decision document (fill after running tests)

### Out of Scope
- Production tool implementations (`app/tools/`) — Phase 4
- Gateway, workers, Redis, database — Phase 2
- Agent definitions in `app/agents/` — Phase 5
- Any changes to `app/` source code — prototypes are self-contained in `tests/phase1/`

## 5. Work Breakdown

Follow Build Order from spec.md. Implement each batch, verify, then proceed.

### Batch 1 — Test Infrastructure (P1.D1)
**Files:** `tests/phase1/__init__.py`, `tests/phase1/conftest.py`

Create shared fixtures:
- `requires_api_key` — `pytest.mark.skipif` when `ANTHROPIC_API_KEY` not in `os.environ`; apply to every test via `pytestmark` module-level variable or auto-use fixture
- `runner_factory` fixture — function that accepts a root `BaseAgent`, returns `InMemoryRunner(agent=agent, app_name="phase1_test")`
- `tmp_workspace` fixture — temp directory for file tool tests (use `tmp_path` from pytest)
- `collect_events` — async helper that takes runner + user_id + session_id + message string, constructs `types.Content(parts=[types.Part(text=message)])`, iterates `runner.run_async()`, returns `(list[Event], session)` where session is retrieved via `runner.session_service.get_session()`

Register custom marker `integration` in conftest to avoid warnings.

**Verify:** `uv run pytest tests/phase1/ --co` discovers modules.

### Batch 2 — Prototype 1: Basic Agent Loop (P1.D2)
**Files:** `tests/phase1/test_p1_basic_agent.py`

**Test: `test_claude_responds_via_litellm`**
- Create `LlmAgent` with `LiteLlm(model="anthropic/claude-sonnet-4-5-20250929")`
- Instruction: "You are a helpful assistant. Respond concisely."
- Send "What is 2+2?" — assert response contains "4"
- Assert events list is non-empty

**Test: `test_function_tools_execute`**
- Define 3 prototype `FunctionTool`s inline (functions with full type hints + docstrings):
  - `file_read(path: str) -> dict[str, str]` — `Path(path).read_text()` wrapped
  - `file_write(path: str, content: str) -> dict[str, str]` — `Path(path).write_text(content)` wrapped
  - `bash_exec(command: str) -> dict[str, str]` — `subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)` wrapped
- Create LlmAgent with these tools
- Instruct: "Write 'hello world' to {tmp_workspace}/test.txt, then read it back and confirm the contents"
- Assert file exists on disk with correct content
- Assert agent response references the content

**Test: `test_token_usage_reported`**
- Run a simple agent interaction
- Iterate events, find one with `event.usage_metadata` not None
- Assert `usage_metadata.prompt_token_count > 0` and `usage_metadata.candidates_token_count > 0`
- If token info is not on events, check alternative mechanisms and document as a quirk

**Verify:** `uv run pytest tests/phase1/test_p1_basic_agent.py -v`

### Batch 3 — Prototypes 2 & 3 (P1.D3, P1.D4) — implement in parallel

#### Prototype 2: Mixed Agent Coordination (P1.D3)
**Files:** `tests/phase1/test_p2_mixed_agents.py`

**Test: `test_sequential_llm_plus_custom_agent`**
- Create `plan_agent` (LlmAgent):
  - instruction: "Write a brief 3-step plan for making a sandwich. Be concise."
  - output_key: `"plan_output"`
  - model: `LiteLlm(model="anthropic/claude-sonnet-4-5-20250929")`
- Create `LinterAgent(BaseAgent)` — no extra Pydantic fields needed:
  ```python
  class LinterAgent(BaseAgent):
      async def _run_async_impl(self, ctx):
          plan = ctx.session.state.get("plan_output", "")
          has_steps = len(plan.strip()) > 0
          ctx.session.state["lint_results"] = f"Plan length: {len(plan)} chars, has content: {has_steps}"
          ctx.session.state["lint_passed"] = has_steps
          yield Event(author=self.name, actions=EventActions(state_delta={}))
  ```
- Wire: `SequentialAgent(name="pipeline", sub_agents=[plan_agent, linter_agent])`
- Assert: `plan_output` in session state and non-empty
- Assert: `lint_results` in session state and `lint_passed` is True
- Assert: Events contain entries authored by both `"plan_agent"` and `"linter_agent"`

**Test: `test_custom_agent_events_in_unified_stream`**
- Same setup — verify event ordering: LLM events before deterministic events
- Assert at least one event from each agent type

**Verify:** `uv run pytest tests/phase1/test_p2_mixed_agents.py -v`

#### Prototype 3: Parallel Execution (P1.D4)
**Files:** `tests/phase1/test_p3_parallel.py`

**Test: `test_parallel_agents_no_state_collision`**
- Create 3 LlmAgents with `LiteLlm(model="anthropic/claude-haiku-4-5-20251001")`:
  - agent_1: "Write one sentence about the ocean." output_key=`"agent_1_output"`
  - agent_2: "Write one sentence about mountains." output_key=`"agent_2_output"`
  - agent_3: "Write one sentence about forests." output_key=`"agent_3_output"`
- Wrap in `ParallelAgent(name="parallel_test", sub_agents=[...])`
- Assert all 3 output keys populated and non-empty
- Assert topical relevance (ocean output mentions water/sea/ocean, etc.)

**Test: `test_parallel_faster_than_sequential`**
- Time the parallel run
- Assert total time < 3x longest expected single-agent time (rough concurrency check)
- Use `time.monotonic()` around the run

**Test: `test_parallel_events_from_all_agents`**
- Verify events from all 3 agents appear in stream
- Collect distinct `event.author` values — should include all 3 agent names

**Verify:** `uv run pytest tests/phase1/test_p3_parallel.py -v`

### Batch 4 — Prototype 4: Dynamic Outer Loop (P1.D5)
**Files:** `tests/phase1/test_p4_outer_loop.py`

**Feature DAG:**
```
A (no deps)  ─┐
              ├─→ C (depends: A) ─┐
B (no deps)  ─┘                   ├─→ E (depends: C, D)
              ┌─→ D (depends: A) ─┘
```
Batch 1: [A, B], Batch 2: [C, D], Batch 3: [E]

**Implement inline:**
- `Feature` dataclass/model: `name: str, depends_on: list[str], prompt: str`
- `create_feature_agent(feature)` → returns `LlmAgent` with haiku model, output_key=`f"feature_{feature.name}_output"`
- `BatchOrchestrator(BaseAgent)` with `features: list[Feature]` as Pydantic model field:
  - `_run_async_impl(self, ctx)` implements the while-loop: select ready features → construct `ParallelAgent` → run → track completed
  - Writes `batch_{n}_features`, `all_completed`, `completed_features`, `total_batches` to state

**Test: `test_features_execute_in_dependency_order`**
- Run BatchOrchestrator with 5 features
- Assert `batch_1_features` contains A and B
- Assert `batch_2_features` contains C and D
- Assert batch 3 contains E
- Assert all 5 feature outputs are in state

**Test: `test_loop_terminates_on_completion`**
- Assert `all_completed` is True
- Assert `total_batches` == 3
- Assert `completed_features` has all 5

**Test: `test_failed_feature_doesnt_block_independent`**
- Modify one feature agent to produce empty output (simulating failure)
- e.g., feature B fails → C and D (which depend on A, not B) should still run
- Assert independent features completed despite B's failure

**Verify:** `uv run pytest tests/phase1/test_p4_outer_loop.py -v`

### Batch 5 — Quality Gates + Decision Document (P1.D6)

1. Run `uv run ruff check .` — fix all lint errors
2. Run `uv run ruff format --check .` — fix formatting
3. Run `uv run pyright` — fix all type errors
4. Run `uv run pytest` — all existing + new tests pass
5. Run `uv run pytest tests/phase1/ -v` — all prototype tests pass
6. Create `.dev/.discussion/phase1-decision.md` with:
   - Decision table (pass/fail per prototype, matching roadmap format)
   - Quirks/workarounds section
   - Go/no-go recommendation with rationale
   - If any prototype fails, alternative approach documented

## 6. Constraints

- **No changes to `app/` source code** — prototypes are isolated in `tests/phase1/`
- **Use `InMemoryRunner`** — no infrastructure dependencies (no Redis, PostgreSQL, Docker)
- **Real API calls** — integration tests, not mocks. Tests auto-skip without `ANTHROPIC_API_KEY`
- **Follow existing patterns**: see `tests/conftest.py` and `tests/test_scaffold.py`
- **Strict typing**: all test code must pass pyright strict (inherited from project config)
- **ADK import paths**: Use verified paths from spec.md Research Notes section
- **BaseAgent is Pydantic v2**: custom fields must be model fields, not `__init__` params
- **Message construction**: `run_async` needs `types.Content(parts=[types.Part(text="...")])`, not plain strings
- **Model strings**: `"anthropic/claude-sonnet-4-5-20250929"` for P1/P2, `"anthropic/claude-haiku-4-5-20251001"` for P3/P4
- **No backwards-compat shims**: early development, delete unused code

## 7. Quality Gate

ALL must pass before proceeding:
1. `uv run ruff check .` — zero errors
2. `uv run ruff format --check .` — formatted
3. `uv run pyright` — zero errors (strict)
4. `uv run pytest` — all pass (scaffold tests + phase1 tests)

## 8. Review Gate

After quality gate passes, launch parallel `reviewer` subagents scaled to spec size:

| Deliverables | Reviewers |
|--------------|-----------|
| 1–4          | 2         |
| 5–8          | 3         |
| 9+           | 4         |

**Phase 1 has 6 deliverables → 3 reviewers.**

| Reviewer | Scope |
|----------|-------|
| Reviewer 1 | `tests/phase1/conftest.py`, `tests/phase1/test_p1_basic_agent.py` |
| Reviewer 2 | `tests/phase1/test_p2_mixed_agents.py`, `tests/phase1/test_p3_parallel.py` |
| Reviewer 3 | `tests/phase1/test_p4_outer_loop.py`, `.dev/.discussion/phase1-decision.md` |

Each reviewer checks:
- Correctness against spec.md acceptance criteria
- CLAUDE.md and `.claude/rules/` adherence
- Type safety (no `Any`, proper type hints on all functions)
- Security (no hardcoded secrets, subprocess safety in bash_exec)
- Code quality (no dead code, no debug logging, no over-engineering)
- ADK API correctness (correct import paths, proper Content construction, BaseAgent as Pydantic model)

### Fix Loop
1. Fix all findings (disputed items → get user confirmation)
2. Re-run quality gate (section 7)
3. HIGH severity items → re-launch one reviewer on affected files
4. Repeat until clean or all remaining confirmed false positives

Do NOT proceed to section 9 until resolved.

## 9. Completion Protocol

CRITICAL — Every checkbox requires EVIDENCE (command output or observable result). Never mark without proof.

### 9a. Verify Success Criteria
Per item in section 3: run verification command → read output → only mark `[x]` on proven success. Failures → fix and re-verify.

### 9b. Mark Spec Complete
Open `.dev/build-phase/phase-1/spec.md`. Per deliverable: run validation command → check off (`[x]`) only passing acceptance criteria. Unverifiable → leave unchecked, report to user.

### 9c. Mark Roadmap Complete
Open `.dev/01-ROADMAP.md`:
1. `[x]` each deliverable checkbox under Phase 1 — only if ALL corresponding spec criteria passed in 9b
2. `[x]` each completion contract checkbox — only if verification passed in 9a
3. Status: `IN PROGRESS` → `DONE` (Phase 1 section)
4. Update top-level status line to: `Status — Phase 2: PLANNED` (or next phase)

### 9d. Final Quality Gate
```
uv run ruff check . && uv run pyright && uv run pytest
```
Fix and re-run until clean.

### 9e. Completion Summary
Print evidence table:

| # | Contract Item | Status | Evidence |
|---|---------------|--------|----------|
| 1 | All 4 prototypes pass | PASS/FAIL | `pytest tests/phase1/ -v` output summary |
| 2 | Go/no-go decision documented | PASS/FAIL | File path + decision value |
| 3 | ADK quirks documented | PASS/FAIL | Section present with content |
| 4 | Quality gates pass | PASS/FAIL | `ruff check . && pyright && pytest` exit codes |

NOT done until 9a-9e complete and every row shows PASS.
