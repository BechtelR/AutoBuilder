# AutoBuilder Architecture

## 1. System Overview

AutoBuilder is an autonomous agentic workflow system that orchestrates multi-agent teams alongside deterministic tooling in structured, resumable pipelines. The core engine is built on Google ADK, which provides unified composition of LLM agents and deterministic tools as equal workflow participants. The system runs continuously from specification to verified output, using dependency-aware batch scheduling, git worktree isolation for parallel execution, and six levels of progressive memory to maintain context across features and sessions.

The architecture is organized around three layers: the outer orchestration loop (dynamic batch scheduling), the inner feature pipeline (sequential plan/code/lint/test/review), and the shared infrastructure (state, memory, skills, tools, observability). All agent types -- LLM and deterministic -- participate in the same event stream, state system, and observability infrastructure.

---

## 2. Architecture Diagram

```
+===========================================================================+
|                            APPLICATION LAYER                               |
+---------------------------------------------------------------------------+
|                                                                            |
|  +--------------------------------------------------------------------+   |
|  |                     ADK App Container                               |   |
|  |  - Context compression (EventsCompactionConfig)                     |   |
|  |  - Resumability (ResumabilityConfig)                                |   |
|  |  - Plugins (TokenTracking, Logging)                                 |   |
|  |  - Lifecycle hooks (on_startup, on_shutdown)                        |   |
|  +-----------------------------------+--------------------------------+   |
|                                      |                                    |
+======================================|====================================+
                                       |
+======================================|====================================+
|                         ORCHESTRATION LAYER                                |
+--------------------------------------+------------------------------------+
|                                      |                                    |
|  +-----------------------------------v--------------------------------+   |
|  |              BatchOrchestrator (CustomAgent)                        |   |
|  |  - Dynamic ParallelAgent batch construction                         |   |
|  |  - Dependency-aware feature selection                               |   |
|  |  - Checkpoint/resume                                                |   |
|  |  - Regression test orchestration                                    |   |
|  +------+-----------------------------+----------------------------+--+   |
|         |                             |                            |      |
|    +----v--------+    +---------------v-----------+    +-----------v--+   |
|    | Batch_001   |    | Batch_002                 |    | Batch_N      |   |
|    | Parallel    |    | ParallelAgent             |    | Parallel     |   |
|    | Agent       |    |                           |    | Agent        |   |
|    +----+--------+    +---------------+-----------+    +-----------+--+   |
|         |                             |                            |      |
+=========|=============================|============================|======+
          |                             |                            |
+==========================================================================+
|                          PIPELINE LAYER (per feature)                      |
+--------------------------------------------------------------------------+
|                                                                            |
|  +--------------------------------------------------------------------+   |
|  |              FeaturePipeline (SequentialAgent)                       |   |
|  |                                                                      |   |
|  |  1. SkillLoaderAgent ........... [Deterministic: CustomAgent]        |   |
|  |  2. plan_agent ................. [LLM: LlmAgent]                    |   |
|  |  3. code_agent ................. [LLM: LlmAgent]                    |   |
|  |  4. LinterAgent ................ [Deterministic: CustomAgent]        |   |
|  |  5. TestRunnerAgent ............ [Deterministic: CustomAgent]        |   |
|  |  6. ReviewCycle (LoopAgent, max_iterations=3)                       |   |
|  |     a. review_agent ............ [LLM: LlmAgent]                    |   |
|  |     b. fix_agent ............... [LLM: LlmAgent]                    |   |
|  |     c. LinterAgent ............ [Deterministic: CustomAgent]        |   |
|  |     d. TestRunnerAgent ........ [Deterministic: CustomAgent]        |   |
|  |                                                                      |   |
|  +--------------------------------------------------------------------+   |
|                                                                            |
+==========================================================================+
          |                             |                            |
+==========================================================================+
|                     SHARED INFRASTRUCTURE LAYER                            |
+--------------------------------------------------------------------------+
|                                                                            |
|  +----------------+  +----------------+  +-----------------------------+  |
|  | Tool Registry  |  | Skill Library  |  | LLM Router                 |  |
|  | (FunctionTools)|  | (Global +      |  | (task_type -> model)       |  |
|  |                |  |  Project-local) |  |                            |  |
|  | - file_read    |  | - Markdown +   |  | - planning -> opus         |  |
|  | - file_write   |  |   YAML front-  |  | - coding -> sonnet         |  |
|  | - file_edit    |  |   matter       |  | - review -> sonnet         |  |
|  | - bash_exec    |  | - Deterministic|  | - classification -> haiku  |  |
|  | - git_*        |  |   matching     |  | - Fallback chains          |  |
|  | - web_*        |  |                |  |                            |  |
|  | - todo_*       |  |                |  |                            |  |
|  +----------------+  +----------------+  +-----------------------------+  |
|                                                                            |
|  +----------------+  +----------------+  +-----------------------------+  |
|  | State System   |  | Memory Service |  | Observability              |  |
|  | (4 scopes)     |  | (SQLite FTS5)  |  |                            |  |
|  |                |  |                |  | - Unified Event stream     |  |
|  | - session      |  | - Cross-session|  | - ADK Dev UI (adk web)    |  |
|  | - user:        |  |   learnings    |  | - OpenTelemetry native    |  |
|  | - app:         |  | - Searchable   |  | - Python logging          |  |
|  | - temp:        |  |   archive      |  | - Plugin system           |  |
|  +----------------+  +----------------+  +-----------------------------+  |
|                                                                            |
+==========================================================================+
          |                             |
+==========================================================================+
|                        PERSISTENCE LAYER                                   |
+--------------------------------------------------------------------------+
|                                                                            |
|  +---------------------------+  +-------------------------------------+   |
|  | DatabaseSessionService    |  | FileArtifactService                 |   |
|  | (SQLite / PostgreSQL)     |  | (Large data: code, files, reports)  |   |
|  |                           |  |                                     |   |
|  | - Session history         |  | - save_artifact / load_artifact     |   |
|  | - State persistence       |  | - Git worktree isolation            |   |
|  | - Event replay            |  |                                     |   |
|  +---------------------------+  +-------------------------------------+   |
|                                                                            |
+==========================================================================+
```

---

## 3. The Autonomous Execution Loop

```
1. Load spec -> generate features (spec-to-feature pipeline)
2. Resolve dependencies (topological sort)
3. While incomplete features exist:
   a. Select next batch (respecting deps + concurrency limits)
   b. For each feature in batch (parallel):
      i.   Load relevant skills (deterministic: SkillLoaderAgent)
      ii.  Plan implementation (LLM: plan_agent)
      iii. Write code (LLM: code_agent)
      iv.  Lint code (deterministic: LinterAgent)
      v.   Run tests (deterministic: TestRunnerAgent)
      vi.  Review quality (LLM: review_agent)
      vii. Loop steps iii-vi if review fails (max N iterations)
   c. Merge completed features
   d. Run regression tests
   e. Optional: pause for human review
4. Report completion
```

The loop runs autonomously until all features are complete. No human prompting is required between iterations. Optional human-in-the-loop intervention points can be configured at the batch boundary (step 3e).

---

## 4. ADK Mapping

### Outer Loop

A `CustomAgent` (inheriting `BaseAgent`) dynamically constructs `ParallelAgent` batches per iteration, manages dependency-aware batch selection, and handles checkpoint/resume.

### Inner Pipeline

A `SequentialAgent` with nested `LoopAgent` for review cycles. Each step in the sequence is either an `LlmAgent` (probabilistic) or a `CustomAgent` (deterministic), composed declaratively.

### Deterministic Steps

`CustomAgent` subclasses (LinterAgent, TestRunnerAgent, SkillLoaderAgent, FormatterAgent) participate as equal workflow citizens. They emit events into the same stream, read/write the same state, and cannot be skipped by LLM judgment.

```python
# Inner feature pipeline -- declarative composition
feature_pipeline = SequentialAgent(
    name="FeaturePipeline",
    sub_agents=[
        SkillLoaderAgent(name="LoadSkills"),     # Deterministic
        plan_agent,                                # LLM
        code_agent,                                # LLM
        LinterAgent(name="Lint"),                  # Deterministic
        TestRunnerAgent(name="Test"),               # Deterministic
        LoopAgent(
            name="ReviewCycle",
            max_iterations=3,
            sub_agents=[
                review_agent,                      # LLM
                fix_agent,                         # LLM
                LinterAgent(name="ReLint"),        # Deterministic
                TestRunnerAgent(name="ReTest"),     # Deterministic
            ]
        )
    ]
)
```

```python
# Outer loop -- dynamic orchestrator
class BatchOrchestrator(BaseAgent):
    """Dynamically constructs ParallelAgent batches per iteration."""
    async def _run_async_impl(self, ctx):
        while incomplete_features_exist(ctx):
            batch = select_next_batch(ctx)  # Dependency-aware, respects concurrency
            parallel = ParallelAgent(
                name=f"Batch_{batch.id}",
                sub_agents=[create_pipeline(f) for f in batch.features]
            )
            async for event in parallel.run_async(ctx):
                yield event
            await run_regression_tests(ctx)
            await checkpoint(ctx)
```

---

## 5. State Architecture

Agents communicate via session state, not direct message passing. All state updates happen through `Event.actions.state_delta`, making every change auditable in the event stream.

| Scope | Prefix | Contents | Persistence |
|-------|--------|----------|-------------|
| **Session** | *(none)* | Current batch, feature statuses, loaded skills, test results, lint results | Per-run (persistent via `DatabaseSessionService`) |
| **User** | `user:` | Preferences, model selections, intervention settings | Cross-session per user |
| **App** | `app:` | Project config, global conventions, skill index | Cross-user, cross-session |
| **Temp** | `temp:` | Intermediate LLM outputs, scratch data | Discarded after invocation |
| **Memory** | `MemoryService` | Cross-session learnings, past decisions, discovered patterns | Persistent, searchable archive |

State values are injectable into agent instructions via `{key}` templating. For example: `"Implement the feature: {current_feature_spec}"` auto-resolves from `session.state['current_feature_spec']`. Use `{key?}` for optional keys that may not exist.

---

## 6. Multi-Agent Communication

Agents communicate via four mechanisms, all operating through session state:

| # | Mechanism | How It Works |
|---|-----------|-------------|
| 1 | `output_key` | Agent writes its result to a named state key |
| 2 | `{key}` templates | Agent reads from state via template injection in instructions |
| 3 | `InstructionProvider` | Dynamic function reads state and constructs context-appropriate instructions at invocation time |
| 4 | `before_model_callback` | Injects additional context (file contents, test results) right before LLM call |

No agent calls another agent directly. All coordination flows through the shared state system, making data flow explicit and debuggable.

---

## 7. Observability

ADK's event-driven architecture provides unified observability without custom bridging:

| # | Mechanism | Description |
|---|-----------|-------------|
| 1 | **Event stream** | Every agent (LLM or deterministic) emits `Event` objects into a unified chronological stream |
| 2 | **ADK Dev UI** | `adk web` for local debugging with detailed traces |
| 3 | **OpenTelemetry native** | Auto-traces `BaseAgent.run_async`, `FunctionTool.run_async`, `Runner.run_async` |
| 4 | **Python logging** | Hierarchical loggers under `google.adk.*` |
| 5 | **Plugin system** | `LoggingPlugin` + custom plugins intercept at workflow callback points |
| 6 | **Third-party** | Langfuse, Arize Phoenix, LangWatch, AgentOps (all OTel-compatible) |

Full pipeline visibility from plan to code to lint to test to review without additional instrumentation. Deterministic `CustomAgent` steps emit events into the same stream as `LlmAgent` steps.

---

## 8. Context Window Management

ADK's `LlmAgent` automatically receives session event history as part of each LLM prompt. Two built-in mechanisms manage growth:

- **Context compression** -- sliding window summarization of older events (config-driven, interval + overlap)
- **Context caching** -- caches static prompt parts server-side (system instructions, knowledge bases)

**Gap identified**: ADK has no built-in context-window usage metric. Agents cannot reactively respond to "you are at 80% capacity."

**Solution**: A `before_model_callback` that token-counts the assembled `LlmRequest`, writes percentage to state, and downstream logic reacts (trigger summarization, prune skills, checkpoint and restart). Approximately 50 lines of code.

**Implication for pipeline design**: For longer pipelines, agents should not rely on reading raw event history from prior steps. Better to use SkillLoaderAgent + explicit state writes so each agent gets precisely the context it needs, not the full event log.

---

## 9. Dynamic Context & Knowledge Loading

ADK provides injection hooks but no built-in knowledge management system. AutoBuilder's knowledge loading is layered:

| Layer | Mechanism | What It Loads |
|-------|-----------|---------------|
| 1 | Static instruction string | Base agent personality/role |
| 2 | `InstructionProvider` function | Project conventions, patterns, feature spec (at invocation time) |
| 3 | `before_model_callback` | File context, codebase analysis, test results (right before LLM call) |
| 4 | `BaseToolset.get_tools()` | Different tools per feature type |
| 5 | Artifacts (`save_artifact`/`load_artifact`) | Large data (full file contents, generated code) |
| 6 | Context compression | Sliding window summarization for long autonomous runs |

No built-in RAG or vector store. For AutoBuilder, knowledge is deterministic lookup -- conventions from files, codebase via tools, specs via state, patterns from local directory. `InstructionProvider` + callbacks are sufficient.

---

## 10. App Class Implementation

ADK's `App` class (v1.14.0+) is the top-level container for the entire agent workflow. AutoBuilder uses `App` as the application shell.

### What App Provides

| Feature | Purpose | AutoBuilder Use |
|---------|---------|----------------|
| `root_agent` | The top-level agent tree | `BatchOrchestrator` (CustomAgent) |
| `events_compaction_config` | Context compression (sliding window summarization) | Keep long autonomous runs within context limits |
| `resumability_config` | Workflow resume after interruption | Pick up where we left off after crash/power loss |
| `plugins` | Global lifecycle hooks (logging, metrics, guardrails) | Token tracking, cost monitoring, security guardrails |
| `context_cache_config` | Cache static prompt parts server-side | Cache system instructions and skill content |
| Lifecycle hooks | `on_startup` / `on_shutdown` | Initialize DB connections, tool registry, skill library |
| State scope boundary | `app:*` prefix for app-level state | Project config, global conventions, workflow registry |

### AutoBuilder App Structure

```python
from google.adk.apps import App, EventsCompactionConfig, ResumabilityConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer

# Summarizer uses a cheap/fast model -- not the primary coding model
summarizer = LlmEventSummarizer(
    llm=LiteLlm(model="anthropic/claude-haiku-4-5-20251001")
)

app = App(
    name="autobuilder",
    root_agent=batch_orchestrator,   # CustomAgent: the outer loop

    # Context compression for long autonomous runs
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5,       # Compress every 5 invocations
        overlap_size=1,              # Retain 1 invocation overlap for continuity
        summarizer=summarizer,       # Explicit model (required when root is non-LLM agent)
    ),

    # Enable workflow resume after interruption
    resumability_config=ResumabilityConfig(
        is_resumable=True,
    ),

    # Global plugins
    plugins=[
        TokenTrackingPlugin(),       # Track cost/tokens per agent per feature
        LoggingPlugin(),             # Structured event logging
    ],
)
```

### Resumability for CustomAgents

ADK's Resume feature (v1.16+) tracks workflow execution and allows picking up after unexpected interruption. Key considerations:

- **Resume is not automatic for CustomAgents** -- we must implement `BaseAgentState` subclass and define checkpoint steps in `BatchOrchestrator`
- Tools may run more than once on resume -- git, file write, and bash tools must be idempotent or include duplicate-run protection
- The system reinstates results from successfully completed tools and re-runs from the point of failure
- This significantly reduces the severity of the "no Temporal-style durability" tradeoff -- ADK native resume may be sufficient for Phase 1

### Runner Configuration

```python
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

# Local persistence -- no GCP services
session_service = DatabaseSessionService(
    db_url="sqlite:///./autobuilder_sessions.db"  # Or postgres://...
)

runner = Runner(
    app=app,
    session_service=session_service,
    artifact_service=FileArtifactService(base_dir="./artifacts"),
)
```

---

*Document Version: 1.0*
*Last Updated: February 2026*
