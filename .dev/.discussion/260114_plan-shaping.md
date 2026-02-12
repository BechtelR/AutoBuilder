# AutoBuilder: Plan Shaping Discussion

**Date**: 2026-01-14
**Status**: Planning Phase

---

## 1. Vision & Requirements

We're designing AutoBuilder, an autonomous Agentic workflow tool with dynamic human-in-the-loop elements that can:

- **Support multiple workflow types** - auto-code, auto-design, auto-market, auto-research, and future workflows
- **Support multiple AI providers** - Claude (with OAuth), OpenAI, Ollama, etc. via provider abstraction
- **Work with greenfield or brownfield projects** - Not just new apps, but existing codebases
- **Plan deliverables and full projects** - Generate comprehensive deliverable sets from specifications using multi-agents + human-in-loop interviews
- **Run autonomously and continuously** - Execute until all jobs are complete and co-verified by agent team, zero intervention required
- **Run multiple agents in parallel** - Concurrent execution with proper isolation
- **Utilize general and skilled agents** - General agents do the heavy lifting and boilerplate, specialist agents to complex work
- **Provide structured workflows** - Organized, trackable progress
- **Offer optional intervention points** - Human-in-the-loop when desired, hands-off when not

---

## 1a. Problems For Resolving

- Forced excessive human-in-the-loop agentic tools available (Claude Code, Firebase, Chat LLMs, etc.)
- Lack of intelligent sequential vs parallel process orchestration
- Autonomous agentic tools available juice not worth the squeeze (Blitzy $10k+ investment per project, research tools, etc)
- Fragmented ecosystem of overly-specific tools (agent harnesses that do specific things instead of orchestrating multi-agent teams)
- Too little reflection, verification, quality-control, and intelligently pragmatic human-in-the-loop
- Projects interrupting for human feedback when unrelated processes can continue while waiting
- No broadly effective shared continuous memory/context solutions while teams of agents continuously process and reset their context windows
- No multi-level memory, business operations/practices/standards, project context/standards/roadmap, session context/task-lists/status
- No lightweight agentic-team coordination patterns; director->workers, specialists, reflectors, reviewers, security, etc.
- Existing systems waste TONS of unnecessary tokens due to excessive human-friendly language prompts back and forth when many processes could utilize machine-formatted structures
- Too much non-deterministic processing (variable language prompts) where scripts and tools can be used; leaves work products lacking uniformity and standarized outputs

## 2. Existing Framework Analysis

### Frameworks Evaluated

| Framework | Location | Approach |
|-----------|----------|----------|
| **Autocoder** | `/home/dmin/projects/autocoder` | Python, two-agent TDD pattern |
| **Automaker** | `/home/dmin/projects/automaker` | TypeScript, Kanban-based studio |
| **SpecDevLoop** | `/home/dmin/projects/SpecDevLoop` | Python, Claude Code headless CLI |
| **oh-my-opencode** | `/home/dmin/projects/oh-my-opencode` | TypeScript, OpenCode plugin, multi-agent orchestration |

### Autocoder

**Strengths**:
- Autonomous execution with auto-continuation (3-second delay between sessions)
- Comprehensive test generation (150-400+ deliverables from spec)
- Two-agent pattern (Initializer + Coding Agent)
- Built-in regression testing
- YOLO mode for rapid prototyping

**Weaknesses**:
- No parallel execution (single agent, PID-locked)
- Weak brownfield support (designed for greenfield)
- Minimal intervention points
- No dependency resolution
- No git isolation
- Claude-only (no multi-model support)
- Single workflow type (coding only)

### Automaker

**Strengths**:
- Git worktree isolation (essential for parallel execution)
- Concurrent execution infrastructure
- Dependency resolution (topological sorting)
- Works on existing codebases
- Plan-approve-execute workflow
- Multi-provider support (Claude, Cursor, Codex, OpenCode)
- Shared package architecture (`libs/`)

**Weaknesses**:
- Heavy/bloated (19+ views, 32 themes, Electron, 150+ routes)
- No auto-continuation until complete
- No bulk deliverable generation from spec
- No built-in regression testing
- More manual intervention expected
- No OAuth support for Claude usage plans
- No multi-workflow architecture

### SpecDevLoop

**Approach**: Spawns Claude Code CLI (`claude -p`) as subprocess per iteration, uses ledger file for state handoff between fresh contexts.

**Claimed Benefits**:
- Fresh context per iteration (no accumulation)
- Ledger-based state persistence
- OAuth authentication

**Weaknesses**:
- Subprocess overhead per iteration
- Claude-only (tied to Claude Code CLI)
- Single workflow type
- No parallel execution

**Reality**: Fresh context achievable with SDK without subprocess overhead, but Claude Code planning, workflows, and tool calls are very strong.

### oh-my-opencode

**Approach**: OpenCode plugin (v3.5.2) that transforms OpenCode into a batteries-included multi-agent orchestration framework. 11 specialized agents, 41 lifecycle hooks, 25+ tools, 3 built-in skills. ~117k lines of TypeScript across 1069 files. Philosophy: "Human intervention = failure signal."

**Strengths**:
- True multi-model orchestration with automatic provider fallback chains (anthropic → kimi → zai → openai → google)
- Separation of planning (Prometheus) and execution (Atlas) — planner never writes code
- Background agent parallelization with tmux visualization and concurrency control
- Category-based task routing (7 categories: visual-engineering, ultrabrain, artistry, quick, etc.)
- Advanced tooling: LSP integration (rename, diagnostics, references), AST-grep pattern matching
- Sophisticated context window management (dynamic pruning, truncation, recovery hooks)
- Boulder state mechanism for multi-session plan continuity
- Full Claude Code compatibility layer (hooks, commands, skills, MCPs)
- OAuth-enabled MCP servers (RFC 9728/8414/8707/7591 compliant)
- Quality controls: comment checker (prevents AI slop), todo continuation enforcer
- 11 specialized agents with distinct models, temperatures, and tool permissions (read-only agents for exploration)

**Weaknesses**:
- Extreme complexity (117k+ lines, 41 hooks, 2000+ line single files) — steep learning curve
- Tightly coupled to OpenCode plugin API — requires OpenCode >= 1.0.150, breaks if OpenCode breaks
- High token cost — "Ultrawork" mode runs multiple Opus 4.6 agents in parallel
- Not a standalone orchestrator — it's a plugin enhancing an existing agentic CLI, not an independent system
- No deliverable-generation-from-spec pipeline — agents work on user-directed tasks, not spec-driven deliverable queues
- No git worktree isolation for parallel work — relies on tmux visual separation, not filesystem isolation
- No dependency resolution between tasks — task system tracks blockers but no topological ordering
- No autonomous "run until all complete" loop — requires ongoing user interaction via OpenCode sessions
- Configuration complexity (21 Zod schema files, multi-level config resolution)
- Restrictive license (SUL-1.0 Sisyphus Use License)

**Key Architectural Patterns Worth Noting**:
1. **3-step model resolution**: User override → provider fallback chain → system default
2. **Agent tool restrictions**: Read-only agents (oracle, librarian, explore) can't write — prevents scope creep
3. **Category routing**: Tasks classified by domain, routed to optimal model/agent combo
4. **Background manager**: Full task lifecycle (pending → running → completed/failed) with concurrency limits per provider/model
5. **Hook system**: 41 hooks across 7 event types for extensible behavior injection

---

## 3. Key Decision: SDK Over Headless CLI

**Decision**: Use Claude Agent SDK directly, not Claude Code headless CLI.

### Why SDK Wins

| Aspect | Headless CLI (SpecDevLoop) | SDK (Our Approach) |
|--------|---------------------------|-------------------|
| Latency | Process spawn + CLI init (~1-2s overhead) | Direct API call (~100ms) |
| Parallelism | Multiple subprocesses (heavy) | Async calls (lightweight) |
| Streaming | Parse CLI JSON output | Native streaming control |
| Tools | Limited to CLI's built-in tools | Custom tool definitions |
| Session control | External ledger files | Native `sdkSessionId` |
| Error handling | Parse CLI error strings | Programmatic exceptions |
| Version coupling | Tied to Claude Code releases | Stable SDK API |
| Resources | N processes for N agents | Single process, N coroutines |

### The "Fresh Context" Non-Argument

SpecDevLoop's core claim is subprocess isolation gives fresh context. But SDK achieves this trivially:

```typescript
// Fresh context = just don't pass conversation history
for (const feature of features) {
  await sdk.query({
    prompt: buildPrompt(feature, ledger),
    // No sessionId = fresh context automatically
  });
}
```

The ledger/handoff pattern works identically with SDK. Subprocess isolation is unnecessary overhead.

**Additional benefit**: SDK approach enables provider abstraction for multi-model support, whereas headless CLI locks us to Claude Code.

---

## 4. Key Decision: New Streamlined App

**Decision**: Build a new focused `AutoBuilder` app rather than modifying Automaker.

### Rationale

1. **Automaker's libs contain the architectural value** - Reuse these
2. **Automaker's apps contain the complexity debt** - Don't inherit this
3. **Building focused is faster than stripping down**
4. **Cleaner mental model** for autonomous execution use case
5. **Can add features later** vs. constantly removing unwanted ones

### What to Reuse from Automaker

```
libs/
├── git-utils/           ✅ Worktree isolation
├── dependency-resolver/ ✅ Topological sorting
├── types/               ✅ Core TypeScript definitions
├── platform/            ✅ Path security, management
├── model-resolver/      ✅ Model alias resolution
├── utils/               ✅ Logging, errors, utilities
└── prompts/             ✅ Adapt prompt templates
```

### What NOT to Inherit

- 19+ UI views (need ~4)
- 32 themes (need 2: light/dark)
- Electron desktop app (web-only is fine)
- 13+ services (need ~5)
- 150+ API routes (need ~30)
- Complex Zustand stores

---

## 5. Initial Architecture Concept

> **Note**: Superseded by Section 7 (Updated Architecture) which incorporates the provider abstraction layer.

### Project Structure (Initial)

```
AutoBuilder/
├── apps/
│   └── auto-builder/
│       ├── server/              # Minimal Express + WebSocket
│       │   ├── index.ts
│       │   ├── services/
│       │   │   ├── execution-engine.ts    # Core autonomous loop
│       │   │   ├── deliverable-generator.ts # Spec → deliverables
│       │   │   ├── agent-runner.ts        # Claude SDK wrapper
│       │   │   └── worktree-manager.ts    # Git isolation
│       │   └── routes/
│       │       ├── projects.ts
│       │       ├── deliverables.ts
│       │       ├── execution.ts
│       │       └── events.ts              # WebSocket
│       └── ui/                  # Minimal React (NO Electron)
│           ├── views/
│           │   ├── Dashboard.tsx          # Progress overview
│           │   ├── FeatureList.tsx        # Simple list view
│           │   ├── ExecutionLog.tsx       # Real-time output
│           │   └── Settings.tsx           # Minimal config
│           └── components/
└── libs/                        # Shared with/from Automaker
    ├── git-utils/
    ├── dependency-resolver/
    ├── types/
    ├── platform/
    ├── model-resolver/
    └── utils/
```

### Core Execution Engine

```typescript
class ExecutionEngine {
  async runUntilComplete(projectPath: string, options: RunOptions) {
    // 1. Load or generate deliverables from spec
    const deliverables = await this.loadOrGenerateDeliverables(projectPath);

    // 2. Resolve dependencies (topological sort)
    const ordered = resolveDependencies(deliverables);

    // 3. Execute until all complete
    while (hasIncompleteDeliverables(ordered)) {
      // Get next batch respecting concurrency limit
      const batch = getNextExecutableBatch(ordered, options.maxConcurrency);

      // Run in parallel with worktree isolation
      await Promise.all(batch.map(deliverable =>
        this.executeDeliverable(deliverable, {
          worktree: true,
          requireApproval: options.interventionPoints,
          runRegression: options.regressionTest,
        })
      ));

      // Optional pause between batches
      if (options.pauseBetweenBatches) {
        await this.waitForContinue();
      }
    }
  }
}
```

### CLI-First Design

```bash
# Initialize from spec
auto-builder init --spec ./requirements.md --project ./my-app

# Run autonomously until complete
auto-builder run --concurrency 3 --regression --no-approval

# Run with intervention points
auto-builder run --pause-between-deliverables

# Optional web dashboard
auto-builder dashboard --port 3000

# Check status
auto-builder status
```

---

## 6. Key Decision: Provider Abstraction Layer

### Expanded Vision

AutoBuilder will support **multiple workflow types** over time:
- `auto-code` - Autonomous coding/development
- `auto-design` - Design systems, UI/UX workflows
- `auto-market` - Marketing content, campaigns
- Future workflows as needed

This requires **multi-model support** - different workflows benefit from different model capabilities.

### Options Evaluated

| Approach | OAuth | Multi-Model | Effort | Lock-in |
|----------|-------|-------------|--------|---------|
| LangChain/LangGraph | ❌ Lost | ✅ Easy | Low | High |
| Provider Abstraction | ✅ Preserved | ✅ Medium | Medium | None |
| Hybrid (LangGraph + SDKs) | ✅ Partial | ✅ Easy | Medium | Partial |
| Claude SDK + bolt-on | ✅ | ⚠️ Messy | Low | Low |

### Decision: Provider Abstraction Layer

**Rationale**:
1. **Preserves Claude OAuth** - Claude SDK under the hood for Claude models
2. **No framework lock-in** - Own abstraction, full control
3. **Native SDK performance** - Direct SDK calls per provider
4. **Clean multi-workflow routing** - Capability-based provider selection

### Provider Interface

```typescript
interface AgentProvider {
  id: string;
  capabilities: Capability[];  // 'coding', 'vision', 'extended-thinking', etc.

  execute(options: ExecuteOptions): AsyncGenerator<AgentEvent>;
  supportsWorkflow(workflow: WorkflowType): boolean;
}
```

### Provider Implementations

| Provider | SDK Used | Auth | Use Cases |
|----------|----------|------|-----------|
| `ClaudeProvider` | Claude Agent SDK | OAuth | Primary coding, extended thinking |
| `AnthropicProvider` | Anthropic SDK | API Key | Fallback Claude access |
| `OpenAIProvider` | OpenAI SDK | API Key | GPT-4, vision tasks |
| `OllamaProvider` | Ollama API | None | Local models, privacy |

### Workflow Definition

```typescript
interface Workflow {
  id: string;
  name: string;
  phases: Phase[];
  requiredCapabilities: Capability[];
  preferredModels?: string[];
  tools: Tool[];
}
```

### Capability-Based Routing

```typescript
class ProviderRouter {
  selectProvider(workflow: WorkflowType, preferences?: Preferences): AgentProvider {
    // 1. Filter by required capabilities
    // 2. Apply user preferences
    // 3. Return best match
  }
}
```

### Why Not LangChain/LangGraph

- **Loses Claude OAuth** - Must use API keys, no usage plan benefits
- **Heavy abstraction** - Unnecessary overhead for our use case
- **Version churn** - LangChain has frequent breaking changes
- **Framework lock-in** - Harder to pivot if needed

---

## 7. Updated Architecture

### Project Structure

```
AutoBuilder/
├── core/
│   ├── providers/
│   │   ├── interface.ts           # Provider contract
│   │   ├── router.ts              # Capability-based routing
│   │   ├── claude-provider.ts     # Claude SDK (OAuth)
│   │   ├── anthropic-provider.ts  # Anthropic SDK (API key)
│   │   ├── openai-provider.ts     # OpenAI SDK
│   │   └── ollama-provider.ts     # Local models
│   ├── workflows/
│   │   ├── interface.ts           # Workflow contract
│   │   ├── engine.ts              # Workflow executor
│   │   ├── auto-code/             # Coding workflow
│   │   ├── auto-design/           # Design workflow
│   │   └── auto-market/           # Marketing workflow
│   └── tools/
│       ├── interface.ts           # Tool contract
│       ├── file-tools.ts          # Read, Write, Edit
│       ├── shell-tools.ts         # Bash, process mgmt
│       └── workflow-specific/     # Figma, browser, etc.
├── apps/
│   ├── cli/                       # CLI application
│   └── dashboard/                 # Optional web UI
└── libs/                          # Shared utilities
    ├── git-utils/
    ├── dependency-resolver/
    └── ...
```

---

## 8. Feature Comparison: Target vs Existing

| Capability | Autocoder | Automaker | SpecDevLoop | oh-my-opencode | AutoBuilder (Target) |
|------------|-----------|-----------|-------------|----------------|---------------------|
| Greenfield | ✅ | ✅ | ✅ | ✅ | ✅ |
| Brownfield | ❌ | ✅ | ✅ | ✅ | ✅ |
| Spec → Features | ✅ (150-400+) | ⚠️ Partial | ❌ | ❌ | ✅ |
| Auto-continue | ✅ | ❌ | ✅ | ⚠️ (boulder state) | ✅ |
| Parallel agents | ❌ | ✅ | ❌ | ✅ (background mgr) | ✅ |
| Git isolation | ❌ | ✅ | ❌ | ❌ | ✅ |
| Dependency resolution | ❌ | ✅ | ❌ | ⚠️ (blockers only) | ✅ |
| Intervention points | ❌ | ✅ | ❌ | ✅ (keyword triggers) | ✅ (optional) |
| Regression testing | ✅ | ❌ | ❌ | ❌ | ✅ |
| Multi-workflow | ❌ | ❌ | ❌ | ⚠️ (categories) | ✅ |
| Multi-model | ❌ | ✅ (4 providers) | ❌ | ✅ (9+ providers) | ✅ (extensible) |
| OAuth support | ❌ (CLI only) | ❌ | ✅ | ✅ (MCP OAuth) | ✅ |
| Specialized agents | ⚠️ (2 agents) | ❌ | ❌ | ✅ (11 agents) | ✅ |
| Agent tool restrictions | ❌ | ❌ | ❌ | ✅ (read-only agents) | ✅ |
| Context mgmt | ❌ | ❌ | ⚠️ (ledger) | ✅ (pruning/recovery) | ✅ |
| Plan/Execute separation | ❌ | ❌ | ❌ | ✅ (Prometheus/Atlas) | ✅ |
| Complexity | Medium | High | Low | Very High (117k LOC) | Low-Medium |

---

## 9. Lessons from oh-my-opencode for AutoBuilder

### What oh-my-opencode Validates in Our Plan

1. **Multi-model orchestration is essential** — oh-my-opencode's 9+ provider support with fallback chains proves the value of our Provider Abstraction Layer decision. Their 3-step resolution (user override → fallback chain → default) is a pattern we should adopt.

2. **Separation of planning and execution works** — Prometheus (planner, never writes code) and Atlas (executor) is the strongest pattern in oh-my-opencode. Our workflow engine should enforce this boundary: planning agents produce structured plans, execution agents consume them.

3. **Agent tool restrictions prevent scope creep** — Read-only agents (oracle, librarian, explore) that can't write/edit are a crucial design insight. Not every agent needs every tool. AutoBuilder should define tool permission sets per agent role.

4. **Category-based task routing is powerful** — Routing tasks to optimal model/agent combinations by domain (visual, logic, writing, etc.) aligns with our capability-based provider routing. We should combine capability matching with domain categorization.

5. **Background agent parallelization needs lifecycle management** — oh-my-opencode's BackgroundManager (pending → running → completed/failed, concurrency limits per provider, task queuing, stale pruning) proves this needs more than just `Promise.all`. Our execution engine needs a proper task lifecycle manager.

### What oh-my-opencode Gets Wrong (For Our Use Case)

1. **Plugin, not orchestrator** — oh-my-opencode enhances a human-driven CLI session. It doesn't run autonomously until all deliverables are complete. AutoBuilder's core differentiator is the autonomous "run until done" loop that oh-my-opencode lacks entirely.

2. **No spec-to-deliverable pipeline** — oh-my-opencode has no mechanism to take a specification and generate 150-400+ implementable deliverables. This is a key gap that Autocoder fills and AutoBuilder must have.

3. **No git worktree isolation** — Despite parallel agents, oh-my-opencode doesn't isolate work in separate worktrees. This limits true parallel code generation to non-conflicting changes. Our git isolation (from Automaker) remains essential.

4. **No topological dependency resolution** — oh-my-opencode tracks `blockedBy` on tasks but has no automated dependency graph or execution ordering. AutoBuilder needs Automaker's topological sorting for proper deliverable sequencing.

5. **Complexity explosion** — 117k lines, 41 hooks, 2000+ line files. This validates our decision to build lean. oh-my-opencode's feature richness came at the cost of maintainability. AutoBuilder should resist this trajectory.

6. **Token cost opacity** — "Ultrawork" mode runs multiple expensive agents without cost visibility. AutoBuilder should track and expose token/cost metrics per deliverable and per agent.

### Patterns to Adopt

| Pattern | oh-my-opencode Implementation | AutoBuilder Adaptation |
|---------|-------------------------------|----------------------|
| **Provider fallback chains** | 3-step: user → fallback chain → default | Adopt directly in ProviderRouter |
| **Agent role restrictions** | Tool allowlists per agent (read-only explorers) | Define `AgentRole` with `allowedTools[]` |
| **Plan/Execute separation** | Prometheus (plan) → Atlas (execute) | `PlanningPhase` → `ExecutionPhase` in workflow engine |
| **Category routing** | 7 categories route to optimal models | Merge with capability-based routing |
| **Task lifecycle** | BackgroundManager with states + concurrency | Adopt in ExecutionEngine task runner |
| **Context window management** | Dynamic pruning, truncation, recovery hooks | Implement context budget per agent session |
| **Boulder state (plan continuity)** | JSON state persisted across sessions | Adapt for deliverable-level checkpoint/resume |

### Patterns to Avoid

| Pattern | oh-my-opencode Issue | AutoBuilder Approach |
|---------|---------------------|---------------------|
| **Monolithic files** | 2000+ line hook/agent files | Max ~500 lines per module, extract strategies |
| **41 hooks for everything** | Hook system became a crutch for all behavior | Use hooks sparingly; prefer explicit workflow phases |
| **Keyword-based triggers** | "ultrawork", "ulw" as magic words in prompts | Structured config, not prompt keyword detection |
| **Platform-specific binaries** | 7 platform packages for CLI | Pure TypeScript/Node, no native dependencies |
| **Plugin coupling** | Breaks when OpenCode API changes | Standalone system, no host dependency |

---

## 10. Open Questions

1. **Lib sharing strategy**: Copy libs from Automaker or set up shared monorepo?
2. **Feature file format**: Adopt Automaker's JSON or Autocoder's SQLite or something else?
3. **Spec parsing**: How sophisticated should spec → deliverable decomposition be?
4. **Regression strategy**: Random sampling (Autocoder) or dependency-aware?
5. **UI priority**: CLI-first with optional dashboard, or dashboard-first?
6. **Workflow packaging**: How are workflows defined and distributed? Built-in vs plugins?
7. **Agent role system**: How granular should tool permissions be per agent role? (Informed by oh-my-opencode's read-only agents pattern)
8. **Context budget strategy**: Per-agent context limits with pruning, or fresh context per task? (Informed by oh-my-opencode's dynamic pruning/recovery)
9. **Cost tracking**: Should AutoBuilder expose per-deliverable and per-agent token/cost metrics? (Informed by oh-my-opencode's token cost opacity problem)

---

## 11. Decisions Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | SDK over headless CLI | Less overhead, better parallelism, native streaming |
| 2 | New app over modifying Automaker | Reuse libs, skip complexity debt |
| 3 | Provider Abstraction Layer | Preserve OAuth, no lock-in, multi-model support |
| 4 | Multi-workflow architecture | Future-proof for auto-design, auto-market, etc. |
| 5 | Standalone orchestrator, not plugin | oh-my-opencode shows plugin coupling is fragile; autonomous loop needs full control |
| 6 | Plan/Execute phase separation | oh-my-opencode's Prometheus/Atlas pattern validates strict role boundaries |
| 7 | Agent role-based tool restrictions | oh-my-opencode's read-only agents prove exploration agents shouldn't have write access |
| 8 | Provider fallback chains | oh-my-opencode's 3-step resolution (user → chain → default) is proven and pragmatic |

---

## 12. Next Steps

1. [ ] Decide on monorepo structure (standalone vs shared libs)
2. [ ] Define provider interface with fallback chain support
3. [ ] Implement ClaudeProvider with OAuth support
4. [ ] Define workflow interface with plan/execute phase separation
5. [ ] Define agent role system with tool permission sets
6. [ ] Implement auto-code workflow as first workflow
7. [ ] Build execution engine with task lifecycle manager (not just Promise.all)
8. [ ] Create minimal CLI
9. [ ] Optional: Add web dashboard
10. [ ] Optional: Add cost/token tracking per deliverable and agent

---

## 13. References

- Full framework comparison: `/home/dmin/projects/autocode-vs-automaker.md`
- Autocoder: `/home/dmin/projects/autocoder`
- Automaker: `/home/dmin/projects/automaker`
- SpecDevLoop: `/home/dmin/projects/SpecDevLoop`
- oh-my-opencode: `/home/dmin/projects/oh-my-opencode`
