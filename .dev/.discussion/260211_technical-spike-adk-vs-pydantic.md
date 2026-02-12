# Technical Spike: Google ADK vs Pydantic AI for AutoBuilder

**Date**: 2026-02-11
**Status**: **Revised — Leaning ADK** (updated after deterministic tool execution analysis)
**Purpose**: Head-to-head comparison against AutoBuilder's specific requirements

---

## Executive Summary

Both frameworks are model-agnostic, Python-first, code-first, and actively maintained. However, they represent fundamentally different philosophies:

- **Pydantic AI** = Lightweight agent framework with workflow support bolted on. "Bring your own orchestration, we'll make the agent calls type-safe."
- **Google ADK** = Full orchestration framework with agents as first-class workflow primitives. "We'll handle the workflow structure, you define the agents."

For AutoBuilder's autonomous multi-agent orchestration use case, this distinction matters enormously.

---

## 1. Evaluation Against AutoBuilder Requirements

### Requirement Matrix

| # | AutoBuilder Requirement | Pydantic AI | Google ADK | Notes |
|---|------------------------|-------------|------------|-------|
| 1 | Model agnostic | ✅ Native (20+ providers) | ✅ Via LiteLLM wrapper | PAI's model support is more seamless; ADK requires LiteLLM wrapper for non-Gemini |
| 2 | Multi-agent parallel execution | ✅ Via asyncio.gather | ✅ Native ParallelAgent | ADK's is declarative and deterministic; PAI's is manual async |
| 3 | Sequential workflows | ✅ Via pydantic-graph | ✅ Native SequentialAgent | ADK's is simpler; PAI's is more flexible |
| 4 | Loop/iteration patterns | ✅ Via pydantic-graph | ✅ Native LoopAgent | ADK has exit_loop tool; PAI uses graph node transitions |
| 5 | Plan/Execute separation | ⚠️ Build yourself | ⚠️ Build yourself | Neither provides this out of the box; both support the pattern |
| 6 | Human-in-the-loop | ✅ Tool approval exceptions | ✅ Callbacks + policy engine | Both adequate; different mechanisms |
| 7 | Checkpointing/durability | ✅ Temporal + DBOS integrations | ⚠️ DatabaseSessionService | PAI's durable execution is more mature (Temporal replay) |
| 8 | Agent tool restrictions | ⚠️ Build yourself | ⚠️ Build yourself | Neither provides role-based tool permissions natively |
| 9 | Context management | ⚠️ Manual | ⚠️ Session state + prefixes | ADK has structured state scoping (session/user/app/temp) |
| 10 | Deterministic workflows | ⚠️ Via pydantic-graph | ✅ Workflow agents are non-LLM | ADK explicitly separates deterministic orchestration from LLM reasoning |
| 11 | Custom workflow patterns | ✅ pydantic-graph FSM | ✅ CustomAgent (BaseAgent) | Both allow arbitrary custom logic |
| 12 | Cost/token tracking | ✅ Via Logfire | ⚠️ Via Vertex AI or custom | PAI's Logfire integration is tighter |
| 13 | Type safety | ✅ First-class (Pydantic native) | ⚠️ Present but less emphasized | PAI wins here clearly |
| 14 | Structured outputs | ✅ Native Pydantic models | ✅ Supported | PAI's is more elegant (validate + auto-retry) |
| 15 | MCP support | ✅ Yes | ✅ Yes | Both support Model Context Protocol |
| 16 | A2A protocol | ✅ Yes | ✅ Yes (Google-initiated) | ADK is the origin of A2A |
| 17 | Evals framework | ✅ Built-in | ✅ Built-in | Both adequate |
| 18 | Extensibility | ✅ Python-native | ✅ Python-native | Equivalent |

**Score: Pydantic AI 11, Google ADK 10, Tied 7** (rough, requirements aren't equally weighted)

---

## 2. Deep Dive: Critical Differentiators

### 2a. Workflow Orchestration Philosophy

**This is the single most important difference for AutoBuilder.**

**Google ADK** treats workflows as **compositional primitives**:
```python
# ADK: Declarative workflow composition
workflow = SequentialAgent(
    name="FeaturePipeline",
    sub_agents=[
        ParallelAgent(
            name="Analysis",
            sub_agents=[security_agent, style_agent, perf_agent]
        ),
        code_writer_agent,
        LoopAgent(
            name="ReviewCycle",
            max_iterations=3,
            sub_agents=[reviewer_agent, refiner_agent]
        ),
        merger_agent
    ]
)
```

Workflow agents (Sequential, Parallel, Loop) are **deterministic** — they don't use an LLM for orchestration decisions. Only LlmAgents within them use LLMs. This directly addresses AutoBuilder requirement #8: "balance of deterministic tools + LLM discretionary behavior."

**Pydantic AI** treats workflows as **code you write**:
```python
# PAI: Programmatic workflow orchestration
async def feature_pipeline(feature):
    # You manage the flow
    analyses = await asyncio.gather(
        security_agent.run(feature),
        style_agent.run(feature),
        perf_agent.run(feature)
    )
    code = await code_writer_agent.run(feature, analyses)
    for _ in range(3):
        review = await reviewer_agent.run(code)
        if review.data.passed:
            break
        code = await refiner_agent.run(code, review)
    return await merger_agent.run(code)
```

Or via pydantic-graph for more complex state machines.

**Assessment:** ADK's approach is more aligned with AutoBuilder's needs. The declarative composition makes workflows inspectable, debuggable, and modifiable without touching orchestration code. PAI's approach is more flexible but puts more burden on you to get orchestration right.

### 2b. State Management

**Google ADK** has structured, scoped state management built-in:
```python
# ADK: Four state scopes
session.state["task_status"] = "active"           # Session-scoped (current conversation)
session.state["user:preferences"] = {...}          # User-scoped (persists across sessions)
session.state["app:global_config"] = {...}          # App-scoped (shared across all users)
session.state["temp:intermediate"] = {...}          # Temp (not persisted)
```

State is passed between agents via `output_key` (agent writes to state) and `{key_name}` template injection (agent reads from state). This is AutoBuilder's inter-agent communication channel.

**Pydantic AI** uses dependency injection and explicit data passing:
```python
# PAI: Dependency injection + explicit returns
@dataclass
class FeatureDeps:
    project_path: str
    deliverable_spec: DeliverableSpec
    db: DatabaseConnection

agent = Agent('claude-sonnet-4-5-20250929', deps_type=FeatureDeps)

result = await agent.run("implement this feature", deps=deps)
# result.data is a typed Pydantic model
```

**Assessment:** For AutoBuilder's multi-agent coordination, ADK's shared state with scoping is a better fit. AutoBuilder agents need to read/write shared context (deliverable status, project state, validation results). PAI's dependency injection is cleaner for single-agent scenarios but requires more manual plumbing for multi-agent state sharing.

### 2c. Model Agnosticism (The Google Trust Question)

This is where your instinct matters, and it's worth being honest about the tradeoffs.

**Google ADK's model support reality:**
- Gemini models: First-class, direct string support (`model="gemini-2.5-flash"`)
- Claude/OpenAI/others: Require LiteLLM wrapper (`model=LiteLlm(model="anthropic/claude-sonnet-4-5-20250929")`)
- Google's built-in tools (SearchTool, etc.): **Only work with Gemini models**
- Some documentation/examples assume Gemini by default
- State-of-the-art features (Interactions API, background execution) are Gemini-optimized

**The practical concern:** While ADK is technically model-agnostic, it's clearly designed Gemini-first. You'll hit edge cases where non-Gemini models don't have full feature parity. The LiteLLM wrapper works but adds a translation layer.

**Pydantic AI's model support reality:**
- All providers are equal citizens via built-in model connectors
- No wrapper needed for any major provider
- `Agent('anthropic:claude-sonnet-4-5-20250929')` and `Agent('openai:gpt-4o')` work identically
- No provider-specific built-in tools that create asymmetry

**Assessment:** Pydantic AI is genuinely model-agnostic. Google ADK is model-agnostic in theory but Gemini-first in practice. For AutoBuilder, where Claude will likely be the primary coding model and you want true provider flexibility, this distinction matters.

### 2d. Privacy and Telemetry

**Google ADK:**
- Apache 2.0 licensed — fully open source, you can inspect everything
- Core framework runs locally with no phone-home (InMemorySessionService, DatabaseSessionService)
- **However:** VertexAiSessionService and VertexAIMemoryBankService send data to Google Cloud
- Google's Logfire equivalent would be their cloud observability stack
- No evidence of telemetry in the open-source library itself
- The framework doesn't require a Google account to use locally

**Pydantic AI:**
- MIT licensed — fully open source
- Core framework runs locally with no phone-home
- Logfire integration is optional and explicit (you opt in)
- Pydantic team has no cloud infrastructure play (they sell Logfire as a product, not as lock-in)
- No evidence of telemetry in the library

**Assessment:** Both are fine for local/self-hosted use. The concern isn't the ADK library itself — it's the gravitational pull toward Google Cloud services. If you use ADK, you'll be constantly nudged toward Vertex AI for sessions, memory, deployment, and monitoring. PAI nudges toward Logfire, but Logfire is optional and the nudge is gentler.

Your instinct about Google is valid but nuanced: the code is genuinely open, but the ecosystem is designed to funnel you toward GCP. If you're disciplined about using only the local components, this isn't an issue. But it's a constant tax on decision-making.

### 2e. Durable Execution / Checkpointing

**Pydantic AI** has a clear advantage here:
- Native Temporal integration via `TemporalAgent` wrapper
- Native DBOS integration for lightweight durability
- Native Prefect integration for workflow orchestration
- Replay-based fault tolerance: crashed workflows resume from last completed step
- This is critical for AutoBuilder's "run until done" autonomous loop

**Google ADK:**
- DatabaseSessionService persists session state to SQLite/Postgres
- Session state survives restarts
- **But:** No equivalent to Temporal's replay-based fault tolerance
- If an agent crashes mid-execution, you have state but not automatic resumption
- You'd need to build your own checkpoint/resume logic on top of state

**Assessment:** For AutoBuilder's autonomous execution loop (which may run for hours), Pydantic AI's Temporal integration is significantly more mature and directly addresses the durability requirement. This is a major differentiator.

### 2f. Maturity and Stability

**Google ADK:**
- v1.24 (February 2026)
- Powers Google's production products (Agentspace, CES)
- Available in Python, TypeScript, Go, Java
- Rapid release cadence
- Large team, strong documentation
- 19k+ GitHub stars

**Pydantic AI:**
- v1.57 (February 2026) — technically still pre-1.0 in spirit but very active
- Built by the Pydantic team (Pydantic is used by virtually every LLM SDK)
- Python only
- Extremely rapid release cadence (multiple releases per week)
- Smaller team but high quality
- 16k+ GitHub stars

**Assessment:** ADK has the backing of Google's resources and is production-proven at scale. PAI has the backing of the Pydantic ecosystem and the trust of the Python AI community. Both are actively maintained and evolving fast. Neither is likely to be abandoned.

---

## 3. AutoBuilder-Specific Architecture Mapping

### How AutoBuilder's Core Loop Maps to Each Framework

**The Autonomous Execution Loop** (AutoBuilder's defining feature):

```
1. Load spec → generate deliverables
2. Resolve dependencies (topological sort)
3. While incomplete deliverables exist:
   a. Select next batch (respecting deps + concurrency)
   b. For each deliverable in batch (parallel):
      i.  Plan agent produces implementation plan
      ii. Execute agent implements the plan
      iii. Review agent validates
      iv. Loop if review fails (max N iterations)
   c. Merge completed deliverables
   d. Run regression tests
   e. Optional: pause for human review
4. Report completion
```

**In Google ADK:**
```python
# ADK maps naturally to this — each step is a workflow agent
deliverable_pipeline = SequentialAgent(
    name="DeliverablePipeline",
    sub_agents=[
        plan_agent,           # LlmAgent: produces plan
        execute_agent,        # LlmAgent: implements plan
        LoopAgent(
            name="ReviewLoop",
            max_iterations=3,
            sub_agents=[review_agent, fix_agent]
        ),
        merge_agent,          # LlmAgent or deterministic tool
    ]
)

# Parallel batch execution
batch_runner = ParallelAgent(
    name="BatchRunner",
    sub_agents=[deliverable_pipeline_1, deliverable_pipeline_2, deliverable_pipeline_3]
)

# The outer loop would be a CustomAgent managing the batch lifecycle
```

**Challenge:** The outer "while incomplete deliverables exist" loop with dynamic batch selection doesn't map cleanly to ADK's static agent composition. You'd need a CustomAgent for the top-level orchestrator that dynamically creates ParallelAgent instances per batch. This is doable but not as clean as the declarative sub-workflows.

**In Pydantic AI:**
```python
# PAI maps via code — you own the loop
async def run_until_complete(spec_path: str, max_concurrency: int = 3):
    deliverables = await generate_deliverables(spec_path)
    ordered = topological_sort(deliverables)

    while incomplete := [f for f in ordered if f.status != "complete"]:
        batch = get_next_batch(incomplete, max_concurrency)

        results = await asyncio.gather(*[
            process_deliverable(d) for d in batch
        ])

        for result in results:
            if result.needs_regression:
                await run_regression_tests()

async def process_deliverable(deliverable: Deliverable) -> DeliverableResult:
    plan = await plan_agent.run(f"Plan: {deliverable.spec}", deps=project_deps)

    for attempt in range(3):
        code = await execute_agent.run(plan.data, deps=project_deps)
        review = await review_agent.run(code.data, deps=project_deps)
        if review.data.approved:
            return DeliverableResult(deliverable=deliverable, output=code.data)
        plan = await fix_agent.run(review.data.feedback, deps=project_deps)

    return DeliverableResult(deliverable=deliverable, status="failed_review")
```

**This is more natural for AutoBuilder's dynamic loop.** The outer orchestration is just Python — no framework gymnastics needed for dynamic batch sizing, dependency-aware scheduling, or conditional continuation.

---

## 4. Risk Analysis

### Google ADK Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| Non-Gemini models as second-class citizens | Medium | Test Claude integration thoroughly before committing |
| Google deprecation/pivot (Google has a history) | Low-Medium | Apache 2.0 means you can fork; but losing active development would hurt |
| Gravitational pull toward GCP services | Medium | Discipline: use only local components; document boundaries |
| Built-in tools (SearchTool etc.) Gemini-only | Low | Build your own tools anyway for AutoBuilder |
| Documentation accuracy issues (see GitHub issue #460) | Low | Test everything; don't trust docs blindly |

### Pydantic AI Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| Sub-1.0 maturity; API still evolving | Medium | Pin versions; the team is disciplined about changes |
| Smaller team than Google | Low | Pydantic ecosystem is massive; community support is strong |
| pydantic-graph less battle-tested than ADK workflow agents | Medium | Use it for complex workflows only; simple flows stay as code |
| No built-in deterministic workflow agents | Low | Write them yourself; it's just Python |
| Rapid release cadence could mean breaking changes | Low-Medium | Pin versions; follow changelog |

---

## 5. The Decisive Factor: Deterministic Tool Execution

### Why This Changes Everything

The initial evaluation (Section 5-original below) recommended Pydantic AI. After deeper analysis of how each framework handles **deterministic vs LLM-discretionary tool execution**, the recommendation has shifted toward Google ADK.

AutoBuilder needs two fundamentally different types of tool execution:

1. **LLM-discretionary tools**: "Use search if you need info" — the LLM decides when/how to use these
2. **Deterministic tools**: Run validator, run tests, check constraints, merge branch — these MUST execute at specific workflow points regardless of LLM judgment

### How Each Framework Handles This

**Pydantic AI**: All tools are LLM-discretionary via `@agent.tool`. Deterministic steps must be plain Python functions called *outside* the agent framework:

```python
# PAI: Deterministic steps live in a "shadow world"
code = await execute_agent.run("implement deliverable", deps=deps)
lint_result = run_linter(code.data)        # Outside framework — invisible to tracing/state
test_result = run_tests(code.data)          # Outside framework — invisible to tracing/state
format_result = format_code(code.data)      # Outside framework — invisible to tracing/state
```

Deterministic steps exist outside the framework's awareness. They don't emit agent events, don't participate in state management, and don't show up in Logfire traces the same way agents do.

**Google ADK**: Deterministic tools are first-class workflow participants via `CustomAgent` (inheriting `BaseAgent`):

```python
# ADK: Deterministic steps are equal citizens
class LinterAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        code = ctx.session.state.get("generated_code")
        result = run_linter(code)
        ctx.session.state["lint_result"] = result  # Participates in state system
        yield Event(author=self.name, actions=EventActions(state_delta={"lint_result": result}))

feature_pipeline = SequentialAgent(
    sub_agents=[
        plan_agent,         # LLM — probabilistic
        execute_agent,      # LLM — probabilistic
        LinterAgent(),      # DETERMINISTIC — cannot be skipped by LLM
        TestRunnerAgent(),  # DETERMINISTIC — cannot be skipped by LLM
        LoopAgent(
            sub_agents=[review_agent, fix_agent, LinterAgent(), TestRunnerAgent()]
        )
    ]
)
```

Deterministic tools in ADK:
- **Participate in the same state system** as LLM agents
- **Visible to tracing/observability** (same Event stream)
- **Cannot be skipped** by LLM judgment — they're workflow steps, not tool suggestions
- **Compose naturally** with LLM agents in Sequential/Parallel/Loop workflows
- **Re-run deterministically** in loops without LLM re-invocation

### Why This Maps to AutoBuilder's Core Architecture

AutoBuilder is fundamentally an **orchestration problem** where LLM agents are one component alongside deterministic tooling. The deliverable pipeline isn't "an LLM that sometimes uses tools" — it's a structured workflow where some steps are probabilistic (planning, execution, reviewing) and others are deterministic (validation, testing, formatting, merging).

Requirement #8 states: "balance of deterministic tools + LLM discretionary behavior; not relying solely on LLM probabilistic execution."

ADK's design philosophy treats this as a first-class concern. PAI's does not — in PAI, you'd need to build:
- A unified task/step interface wrapping both PAI agents and deterministic functions
- Your own composition engine to sequence them
- Your own event/tracing bridge for deterministic step observability
- Your own state-passing mechanism between agent and non-agent steps

That's a substantial amount of orchestration infrastructure — exactly the kind of engineering AutoBuilder aims to eliminate.

---

## 6. Revised Recommendation

### For AutoBuilder specifically, Google ADK is the stronger choice.

**Reasoning:**

1. **Deterministic tool execution as first-class citizens.** AutoBuilder's core value proposition depends on structural guarantees that tests run, linters execute, and code gets formatted — regardless of what the LLM "thinks" should happen. ADK provides this architecturally. PAI would require building it from scratch.

2. **Unified composition model.** `BaseAgent` is the common ancestor for both LLM agents and deterministic agents. Workflow agents (Sequential, Parallel, Loop) accept any `BaseAgent` subclass without knowing or caring whether it uses an LLM. This is one composition model, one state system, one event stream, one observability layer.

3. **AutoBuilder's dynamic outer loop is solvable.** The initial concern was that ADK's declarative composition couldn't handle AutoBuilder's dynamic batch selection. This is addressed by using a `CustomAgent` as the top-level orchestrator that programmatically constructs `ParallelAgent` instances per batch. The inner deliverable pipelines remain clean declarative compositions.

4. **State management is better suited.** ADK's four-scope state system (session/user/app/temp) with automatic persistence maps directly to AutoBuilder's needs: deliverable status in session state, user preferences in user state, project config in app state, intermediate results in temp state.

5. **Observability comes for free.** Every agent — LLM or deterministic — emits events into the same stream. No custom bridging needed between "framework world" and "shadow world" of deterministic functions.

### Acknowledged Tradeoffs (ADK Weaknesses to Mitigate)

| Weakness | Severity | Mitigation Strategy |
|----------|----------|---------------------|
| Gemini-first bias | Medium | Use LiteLLM wrapper consistently; test Claude integration thoroughly in prototyping |
| No Temporal-style durability | Medium-High | Build checkpoint/resume into the CustomAgent outer loop; ADK's DatabaseSessionService handles state persistence, we add replay logic |
| Google ecosystem gravity | Medium | Stay disciplined: DatabaseSessionService (local SQLite/Postgres), skip Vertex AI services entirely |
| Documentation accuracy issues | Low | Test everything empirically; don't trust docs blindly |
| Type safety less emphasized than PAI | Low | Use Pydantic models for structured outputs within ADK agents |

### Where PAI Would Have Won

If AutoBuilder were primarily an LLM-centric application where agents were the main abstraction and deterministic tooling was secondary, PAI's lighter weight, true model agnosticism, and superior type safety would make it the clear winner. PAI is also the better choice for applications that need Temporal-grade durability from day one.

### The Pragmatic Path (Revised)

1. **Start with Google ADK** for the core orchestration framework
2. **Use CustomAgent** for the dynamic outer loop (batch management, continuation)
3. **Use SequentialAgent/ParallelAgent/LoopAgent** for inner feature pipelines
4. **Wrap deterministic tools** (linter, test runner, formatter) as CustomAgents
5. **Use LiteLLM** for Claude/multi-model support; test thoroughly in prototyping
6. **Build checkpoint/resume** on DatabaseSessionService + custom logic (Phase 1)
7. **Evaluate Temporal integration** if DatabaseSessionService proves insufficient (Phase 2)
8. **Stay local**: SQLite/Postgres for sessions, skip all Vertex AI services

---

## 5-ORIGINAL. Initial Recommendation (Superseded)

### ~~For AutoBuilder specifically, Pydantic AI is the stronger choice.~~

*This section preserved for decision history. See Section 6 for revised recommendation.*

**Original Reasoning:**

1. **AutoBuilder's core loop is dynamic, not declarative.** The "run until done" pattern with dynamic batch sizing, dependency-aware scheduling, and conditional continuation maps more naturally to Pydantic AI's "it's just Python" approach than ADK's declarative workflow composition.

2. **True model agnosticism matters.** AutoBuilder's vision involves routing different tasks to different models based on capability. Pydantic AI treats all providers equally. ADK's Gemini-first bias creates friction.

3. **Durable execution is critical.** AutoBuilder runs for hours autonomously. Pydantic AI's Temporal integration provides replay-based fault tolerance. ADK has state persistence but not automatic workflow resumption.

4. **Type safety aligns with your values.** Pydantic AI's compile-time type checking catches errors before runtime. This matters for a system that runs autonomously — bugs in production are expensive when there's no human watching.

5. **Lower maintenance burden.** PAI is a lighter framework with less surface area to break. ADK is feature-rich but carries more complexity.

6. **Privacy alignment.** No gravitational pull toward any cloud provider.

### ~~The Pragmatic Path~~

1. ~~Start with Pydantic AI for the core agent framework and multi-model support~~
2. ~~Use pydantic-graph only where you need complex state machine workflows~~
3. ~~Use plain asyncio for the top-level orchestration~~
4. ~~Add Temporal when durability becomes critical (Phase 2)~~
5. ~~Keep ADK as a reference architecture~~

---

## 7. Prototype Plan (Revised for ADK)

To validate the revised recommendation before full commitment:

### Prototype 1: Basic Agent Loop + Claude via LiteLLM
- Create an ADK LlmAgent with Claude via LiteLLM wrapper
- Define file-read, file-write, and bash as FunctionTools
- Run a simple "implement this function" task
- **Critical validation:** Does Claude work reliably through LiteLLM? Latency? Token counting accuracy?

### Prototype 2: Mixed Agent Coordination (LLM + Deterministic)
- Create plan_agent (LlmAgent) and linter_agent (CustomAgent/BaseAgent)
- Wire them in a SequentialAgent pipeline
- Pass data via session state (output_key → state read)
- Validate: unified event stream, state persistence across agent types, observability of deterministic steps

### Prototype 3: Parallel Execution
- Run 3 LlmAgent instances concurrently via ParallelAgent
- Each writes results to distinct state keys
- Validate: no state collision, proper isolation, concurrent LLM calls, event interleaving behavior

### Prototype 4: Dynamic Outer Loop (CustomAgent Orchestrator)
- Build a CustomAgent that dynamically constructs ParallelAgent batches
- Implement "while incomplete features exist" loop with dependency ordering
- Test with 5 simple features
- Validate: dynamic workflow construction, correct execution order, failure handling, continuation

**Success criteria:** If all 4 prototypes work cleanly (especially Claude via LiteLLM in P1 and dynamic orchestration in P4), commit to ADK. If Claude integration proves unreliable or the CustomAgent outer loop is too clunky, re-evaluate PAI.

---

## 8. Skills System Design

### The Problem

AutoBuilder agents need specialized knowledge to do their jobs well: project conventions, framework-specific patterns, testing strategies, migration procedures, deployment configs. This knowledge is:

- **Too large to include in every prompt** — loading all skills into every agent call wastes tokens and degrades focus
- **Task-dependent** — a database migration agent doesn't need API endpoint patterns
- **Project-dependent** — a FastAPI project and a Django project need different implementation skills
- **Evolving** — new skills get added as the project grows; shouldn't require code changes
- **Human-authored** — engineers should be able to write and audit skills without touching Python

ADK provides the *injection hooks* (InstructionProvider, before_model_callback, dynamic Toolsets) but not the *discovery, indexing, and progressive disclosure* system. We build that.

### Design Principles

1. **Skills are just files.** Markdown with YAML frontmatter. No database, no special tooling to author them.
2. **Frontmatter is the index.** Lightweight metadata enables matching without reading full content.
3. **Progressive disclosure.** Agents see the skill index (names + descriptions). Full content loads only when matched.
4. **Two-tier skill library.** Global skills (apply to all projects) + project-local skills (live in the repo).
5. **Composable.** Multiple skills can apply to one task. Agent gets all relevant skills, not just one.
6. **No LLM in the matching loop.** Skill selection is deterministic pattern matching, not another LLM call.

### Skill File Format

```markdown
---
name: fastapi-endpoint
description: How to implement a REST API endpoint following project conventions
triggers:
  - feature_type: api_endpoint
  - file_pattern: "*/routes/*.py"
  - file_pattern: "*/api/*.py"
tags: [api, http, routing, fastapi]
applies_to: [code_agent, review_agent]  # Which agents can use this skill
priority: 10  # Higher = loaded first when multiple skills match
---

## API Endpoint Implementation

### Structure
All endpoints follow this pattern:

```python
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_db
from app.schemas import {Model}Create, {Model}Response

router = APIRouter(prefix="/{resource}", tags=["{resource}"])

@router.post("/", response_model={Model}Response, status_code=201)
async def create_{resource}(
    payload: {Model}Create,
    db: Session = Depends(get_db)
):
    ...
```

### Conventions
- Always use async handlers
- Always use Pydantic schemas for request/response
- Always use dependency injection for DB sessions
- Error responses use HTTPException with detail messages
- Pagination via `skip` and `limit` query params with defaults (0, 20)

### Testing
- Every endpoint gets a test file at `tests/api/test_{resource}.py`
- Use `httpx.AsyncClient` with the test app fixture
- Test happy path, validation errors, not found, and auth failures
```

### Skill Index Structure

```python
@dataclass
class SkillEntry:
    """Lightweight index entry — loaded from frontmatter only."""
    name: str
    description: str
    triggers: list[SkillTrigger]
    tags: list[str]
    applies_to: list[str]       # Agent names that can use this skill
    priority: int
    file_path: Path             # Where to load full content from
    source: str                 # "global" or "project"

@dataclass 
class SkillTrigger:
    """A condition that activates this skill."""
    type: str                   # "feature_type", "file_pattern", "tag_match", "explicit"
    value: str                  # The pattern to match against

@dataclass
class LoadedSkill:
    """Full skill content, loaded on demand."""
    entry: SkillEntry
    content: str                # The markdown body (everything after frontmatter)
```

### Skill Discovery and Loading

```python
class SkillLibrary:
    """Discovers, indexes, and loads skills on demand."""
    
    def __init__(self, global_skills_dir: Path, project_skills_dir: Path | None = None):
        self._index: list[SkillEntry] = []
        self._cache: dict[str, LoadedSkill] = {}  # name -> loaded content
        self._build_index(global_skills_dir, source="global")
        if project_skills_dir:
            self._build_index(project_skills_dir, source="project")
    
    def _build_index(self, skills_dir: Path, source: str):
        """Scan directory, parse frontmatter only, build lightweight index."""
        for skill_file in skills_dir.glob("**/*.md"):
            frontmatter = parse_frontmatter(skill_file)  # YAML header only
            self._index.append(SkillEntry(
                name=frontmatter["name"],
                description=frontmatter["description"],
                triggers=[SkillTrigger(**t) for t in frontmatter.get("triggers", [])],
                tags=frontmatter.get("tags", []),
                applies_to=frontmatter.get("applies_to", ["*"]),
                priority=frontmatter.get("priority", 0),
                file_path=skill_file,
                source=source,
            ))
    
    def match(self, context: SkillMatchContext) -> list[SkillEntry]:
        """Deterministic matching — no LLM involved.
        
        Returns matching skills sorted by priority (highest first).
        Project-local skills override global skills with the same name.
        """
        matches = []
        for entry in self._index:
            if context.agent_name not in entry.applies_to and "*" not in entry.applies_to:
                continue
            if self._triggers_match(entry.triggers, context):
                matches.append(entry)
        
        # Project skills override global skills with same name
        matches = self._deduplicate_prefer_project(matches)
        return sorted(matches, key=lambda e: e.priority, reverse=True)
    
    def load(self, entry: SkillEntry) -> LoadedSkill:
        """Load full skill content. Cached after first load."""
        if entry.name not in self._cache:
            content = parse_body(entry.file_path)  # Everything after frontmatter
            self._cache[entry.name] = LoadedSkill(entry=entry, content=content)
        return self._cache[entry.name]
    
    def get_index_summary(self, agent_name: str) -> str:
        """Returns a compact summary of all available skills for an agent.
        
        This goes into the agent's base instructions so it knows what's available
        without loading full content.
        """
        relevant = [e for e in self._index 
                     if agent_name in e.applies_to or "*" in e.applies_to]
        lines = [f"- {e.name}: {e.description}" for e in relevant]
        return "Available skills:\n" + "\n".join(lines)
```

### Integration with ADK Agents

Skills plug into ADK at two points:

**Point 1: InstructionProvider** — matches and loads skills at invocation time:

```python
def code_agent_instructions(context: ReadonlyContext) -> str:
    # Deterministic skill matching based on current task
    match_context = SkillMatchContext(
        agent_name="code_agent",
        feature_type=context.state.get("current_feature_type"),
        file_paths=context.state.get("target_files", []),
        tags=context.state.get("feature_tags", []),
    )
    
    matched = skill_library.match(match_context)
    loaded = [skill_library.load(entry) for entry in matched]
    
    skills_text = "\n\n".join([
        f"### Skill: {s.entry.name}\n{s.content}" for s in loaded
    ])
    
    return f"""You are a code implementation agent.

{skills_text}

Current deliverable: {context.state.get('current_deliverable_spec')}
"""

code_agent = LlmAgent(
    name="code_agent",
    model=LiteLlm(model="anthropic/claude-sonnet-4-5-20250929"),
    instruction=code_agent_instructions,
)
```

**Point 2: CustomAgent skill loader** — a deterministic agent step that resolves skills into state before LLM agents run:

```python
class SkillLoaderAgent(BaseAgent):
    """Deterministic agent that loads relevant skills into session state.
    
    Runs before LLM agents in a SequentialAgent pipeline.
    Keeps skill resolution visible in the event stream.
    """
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        match_context = SkillMatchContext(
            agent_name=ctx.session.state.get("next_agent"),
            feature_type=ctx.session.state.get("current_feature_type"),
            file_paths=ctx.session.state.get("target_files", []),
            tags=ctx.session.state.get("feature_tags", []),
        )
        
        matched = skill_library.match(match_context)
        loaded = [skill_library.load(entry) for entry in matched]
        
        skills_content = {s.entry.name: s.content for s in loaded}
        skill_names = [s.entry.name for s in loaded]
        
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={
                "loaded_skills": skills_content,
                "loaded_skill_names": skill_names,
            })
        )

# Usage in pipeline — skill loading is a visible, deterministic workflow step
deliverable_pipeline = SequentialAgent(
    name="DeliverablePipeline",
    sub_agents=[
        SkillLoaderAgent(name="LoadSkills"),   # Deterministic: resolve skills
        plan_agent,                             # LLM: plan using loaded skills
        code_agent,                             # LLM: implement using loaded skills
        LinterAgent(),                          # Deterministic: lint
        TestRunnerAgent(),                       # Deterministic: test
    ]
)
```

The second approach (SkillLoaderAgent) is preferable for AutoBuilder because:
- Skill resolution appears in the event stream (observable/debuggable)
- Skills are loaded into state once, available to all subsequent agents in the pipeline
- It's a deterministic step — consistent with the ADK philosophy of explicit workflow composition
- You can see exactly which skills were loaded for any given feature execution

### Skill Directory Layout

```
autobuild/
├── skills/                          # Global skills (ship with AutoBuilder)
│   ├── code/
│   │   ├── api-endpoint.md
│   │   ├── data-model.md
│   │   ├── background-job.md
│   │   └── database-migration.md
│   ├── review/
│   │   ├── security-review.md
│   │   ├── performance-review.md
│   │   └── style-review.md
│   ├── test/
│   │   ├── unit-test-patterns.md
│   │   ├── integration-test-patterns.md
│   │   └── fixture-patterns.md
│   └── planning/
│       ├── feature-decomposition.md
│       └── dependency-analysis.md
│
└── ... (AutoBuilder core code)

user-project/
├── .autobuilder/
│   └── skills/                      # Project-local skills (override/extend global)
│       ├── code/
│       │   ├── api-endpoint.md       # Overrides global — project-specific conventions
│       │   └── auth-middleware.md    # Project-specific skill, no global equivalent
│       └── review/
│           └── compliance-review.md  # Project-specific compliance rules
├── src/
├── tests/
└── ...
```

Project-local skills with the same `name` as a global skill override it. This lets users customize behavior without forking or configuring anything — just drop a file.

### Trigger Matching Rules

| Trigger Type | Matches Against | Example |
|---|---|---|
| `feature_type` | `state["current_feature_type"]` | `feature_type: api_endpoint` |
| `file_pattern` | Any file in `state["target_files"]` | `file_pattern: "*/routes/*.py"` |
| `tag_match` | Any tag in `state["feature_tags"]` | `tag_match: database` |
| `explicit` | `state["requested_skills"]` | `explicit: fastapi-endpoint` |
| `always` | Always matches for the specified agents | `always: true` |

A skill matches if **any** of its triggers match (OR logic). This keeps trigger authoring simple — you're listing reasons this skill *could* be relevant, not building complex boolean expressions.

### What This Gives Us

1. **Zero-config skill discovery** — scan directory, read frontmatter, done
2. **Progressive disclosure** — agents know what's available (index summary) but only load what they need
3. **Deterministic matching** — no LLM involved in skill selection, reproducible and fast
4. **Project-local overrides** — users customize by dropping files, not writing code
5. **Observable** — SkillLoaderAgent emits events showing which skills were loaded and why
6. **Composable** — multiple skills load for a single task
7. **Token-efficient** — only matched skill content enters the prompt
8. **Framework-aligned** — skills load via the same mechanisms (state, events, CustomAgent) as everything else in ADK

### Implementation Priority

This is a **Phase 1 component** — build it alongside the core pipeline, not after. Agents without skills are generic; agents with skills produce project-appropriate output. The difference between "generate a FastAPI endpoint" and "generate a FastAPI endpoint following *our* conventions with *our* auth patterns and *our* test structure" is entirely in the skills.

Estimated scope: ~300-400 lines for the core SkillLibrary + SkillLoaderAgent + frontmatter parsing. Another ~200 lines for the initial set of global skills. Not a heavy lift, but disproportionate value.

---

## 9. References

- Pydantic AI docs: https://ai.pydantic.dev/
- Pydantic AI GitHub: https://github.com/pydantic/pydantic-ai
- Google ADK docs: https://google.github.io/adk-docs/
- Google ADK GitHub: https://github.com/google/adk-python
- ADK multi-agent patterns: https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/
- Pydantic AI + Temporal: https://ai.pydantic.dev/durable_execution/overview/
- Framework comparison benchmarks: https://newsletter.victordibia.com/p/autogen-vs-crewai-vs-langgraph-vs
