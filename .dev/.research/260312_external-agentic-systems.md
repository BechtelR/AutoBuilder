# External Agentic Workflow Systems Research

Research date: 2026-03-12
Focus: Architecture patterns, workflow composition, multi-agent coordination, and quality enforcement in production agentic coding systems. Research conducted for AutoBuilder Phase 7 (Workflow Composition System).

---

## Table of Contents

1. [Stripe Minions](#1-stripe-minions)
2. [Shopify Roast](#2-shopify-roast)
3. [Cognition Devin](#3-cognition-devin)
4. [Factory.ai Droids](#4-factoryai-droids)
5. [OpenAI Codex](#5-openai-codex)
6. [Google Jules](#6-google-jules)
7. [Amazon Q Developer](#7-amazon-q-developer)
8. [MetaGPT](#8-metagpt)
9. [Cross-System Comparison](#9-cross-system-comparison)
10. [Patterns Worth Adopting](#10-patterns-worth-adopting)
11. [Anti-Patterns to Avoid](#11-anti-patterns-to-avoid)
12. [Novel Insights for AutoBuilder](#12-novel-insights-for-autobuilder)

---

## 1. Stripe Minions

**Source**: https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents

### Architecture

- Built on a customized fork of Block's **goose** coding agent
- Runs on **isolated devboxes** -- the same machines Stripe engineers use, pre-warmed, spinning up in ~10 seconds with code and services pre-loaded
- Isolated from production and internet, enabling parallel execution without permission checks
- Central MCP server (**Toolshed**) hosts 400+ tools spanning internal systems and SaaS platforms

### Workflow Model

Opinionated orchestration that **interleaves agent creativity with deterministic steps**:
1. Engineer initiates via Slack (primary), CLI, or web
2. Minion creates isolated branch in devbox
3. Agent performs development work (creative/non-deterministic)
4. Code pushed to CI (deterministic)
5. Pull request created following Stripe's template (deterministic)
6. Engineer reviews; can iterate

The stated goal is "one-shotting" -- completing tasks without human intervention between start and finished PR.

### Quality Enforcement

**Layered, progressive feedback with hard iteration limits:**

- **Local phase (<5s)**: Automated heuristic-selected lints on each git push
- **CI phase**: Selective test execution from 3M+ test suite
- **Autofix**: Many test failures include automatic corrections applied without LLM
- **Iteration cap**: Maximum two CI rounds. If tests fail after first push, one fix attempt, then the process completes regardless

This is a critical design choice: they cap LLM iterations to avoid diminishing returns.

### Context Integration

- Consumes the same agent rule files used by human tools (Cursor, Claude Code)
- Rules are **conditionally applied by subdirectory**, not global
- MCP provides access to internal docs, tickets, build statuses, Sourcegraph code intelligence

### Strengths

- Environmental parity: agent uses same infrastructure as human engineers
- Slack-native entry point reduces adoption friction
- Hard iteration limits prevent runaway costs
- Massive scale proof: 1,000+ merged PRs/week, zero human-written code

### Weaknesses

- Tightly coupled to Stripe's proprietary infrastructure
- One-shot model limits complexity of addressable tasks
- No multi-agent coordination -- each minion is a single agent
- No explicit workflow composition; each run is an independent task

### Lessons for AutoBuilder

1. **Environmental parity matters more than agent sophistication** -- if the agent has the same tools as the human, it can solve the same problems
2. **Hard iteration caps are essential** -- 2 CI rounds, not "iterate until success." AutoBuilder's `max_iterations` on LoopAgent is the right pattern
3. **Conditional rule application by context** -- subdirectory-scoped rules are more effective than monolithic global instructions. Maps to AutoBuilder's 3-scope agent definition cascade
4. **Centralized tool server (MCP)** -- Toolshed's 400+ tools via MCP is analogous to AutoBuilder's GlobalToolset, but MCP gives extensibility

---

## 2. Shopify Roast

**Source**: https://github.com/Shopify/roast, https://shopify.engineering/introducing-roast

### Architecture

Ruby-based **convention-over-configuration** workflow orchestration framework. Core thesis: "Non-determinism is the enemy of reliability." Roast structures workflows to interleave deterministic code execution with non-deterministic AI steps.

Rebuilt from the ground up in v1.0 around a pure Ruby DSL (moved away from YAML-only configuration to composable Ruby syntax).

### Workflow Composition Model

**Cog-based composition** -- 7 building blocks that chain together:

| Cog | Purpose |
|-----|---------|
| `chat` | Send prompts to cloud LLMs (OpenAI, Anthropic, Gemini) |
| `agent` | Run local coding agents with filesystem access (Claude Code CLI) |
| `ruby` | Execute custom Ruby code |
| `cmd` | Run shell commands, capture output |
| `map` | Process collections serial or parallel |
| `repeat` | Iterate until conditions met |
| `call` | Invoke reusable workflow scopes |

Steps share **conversation transcripts**, so later steps reference earlier discoveries without explicit data piping.

**Control flow**: conditionals, case statements, iteration, parallel execution.

### Configuration

- `workflow.yml` manifest with markdown `prompt.md` files per step
- `.roast/initializers/` for custom authentication, retry strategies, token tracking
- Step types are **inferred by convention** (directory = prompt step, `$()` = command, `^` prefix = CodingAgent)
- **Session replay**: resume from any step, avoiding expensive re-runs

### Quality Enforcement

- CodingAgent iteratively fixes type errors, runs tests, ensures passing
- Built-in tool restrictions prevent unsafe filesystem operations
- Raix abstraction layer adds retry logic, caching, structured output handling

### Real-World Validation

- **Boba workflow**: Automated Sorbet type annotation. Deterministic cleanup with `sed` -> Sorbet autocorrect -> CodingAgent fixes remaining issues. Processes thousands of test files.
- SRE proactive monitoring, competitive intelligence aggregation

### Strengths

- Elegant interleaving of deterministic and non-deterministic steps
- Convention-over-configuration reduces boilerplate
- Session replay for debugging and cost savings
- `map` cog for parallel processing of collections
- CodingAgent integration gives full Claude Code capabilities within structured guardrails

### Weaknesses

- Ruby-only DSL limits adoption outside Ruby ecosystem
- No hierarchical supervision (flat workflow, no PM/Director equivalent)
- No built-in quality gates as first-class concepts (quality is embedded in step logic)
- Single-workflow focus; no compound workflow composition

### Lessons for AutoBuilder

1. **Cog taxonomy is valuable** -- the 7 cog types map almost perfectly to what AutoBuilder workflows need: LLM steps, deterministic steps, shell commands, iteration, parallel fan-out, and reusable sub-workflows. AutoBuilder's pipeline stages should support these same primitives.
2. **Session replay is powerful** -- being able to resume from any step avoids re-running expensive LLM calls during development/debugging. AutoBuilder should consider checkpoint-based resumability per pipeline stage.
3. **Convention over explicit typing** -- inferring step type from structure (directory = prompt, `$()` = command) reduces manifest boilerplate. AutoBuilder's WORKFLOW.yaml could adopt similar conventions for step type inference.
4. **Transcript sharing between steps** -- implicit context passing through conversation history is elegant for linear pipelines but breaks down for parallel/branching workflows. AutoBuilder's state-based approach (session state keys) is more general.

---

## 3. Cognition Devin

**Source**: https://cognition.ai/blog/devin-2, https://cognition.ai/blog/devin-annual-performance-review-2025, https://devin.ai/agents101

### Architecture

**Compound AI system** -- not a single model but a swarm of specialized models:

1. **The Planner**: High-reasoning model that outlines strategy
2. **The Coder**: Specialized model trained on code
3. **The Critic**: Adversarial model reviewing for security vulnerabilities and logic errors

Each Devin instance runs in an **isolated cloud VM** with its own IDE. Multiple instances can operate in parallel.

### Workflow Model

**Plan-Approve-Execute pattern:**
1. Devin parses request, loads repository context
2. Generates detailed plan with repo citations
3. User approves or adjusts plan before coding begins
4. Inside cloud IDE: edits code, runs commands, uses built-in browser
5. Runs unit tests / CI pipelines to confirm functionality
6. Session ends with PR or direct commit

**Checkpoint-based delivery** with human review gates between major phases.

### Quality Metrics (2025 Performance Review)

| Metric | Value |
|--------|-------|
| PR merge rate | 67% (vs 34% prior year) |
| Problem-solving speed | 4x faster than v1 |
| Resource efficiency | 2x improvement |
| Regression cycle reduction | 93% faster (Litera case) |
| Security fix velocity | 1.5 min vs 30 min human avg |
| Test coverage improvement | 50-60% to 80-90% |

### Critical Limitations Identified

- **Ambiguity intolerance**: Requires "clear, upfront requirements." Struggles with mid-task requirement changes.
- **Cannot independently tackle ambiguous projects end-to-end** like a senior engineer
- Tasks lacking "straightforwardly verifiable" outcomes require additional human oversight
- No soft skills (managing stakeholders, cross-team coordination)

### Fleet Deployment Pattern

Organizations deploy multiple Devin instances in parallel for migration tasks. One bank achieved 10x improvement (3-4 hrs vs 30-40) on ETL framework migrations. This is a **map-reduce pattern**: decompose large migration into per-file tasks, fan out to parallel agents, collect results.

### Strengths

- Planner-Coder-Critic tri-model architecture separates concerns
- Automatic codebase indexing and wiki generation
- Fleet deployment for parallel task execution
- Strong metrics demonstrating real-world value
- Plan-approve gate prevents wasted compute

### Weaknesses

- Requires clear, unambiguous requirements (cannot handle creative/exploratory work)
- No workflow composition -- each Devin run is independent
- No hierarchical supervision between instances
- Human must be the orchestrator for fleet deployments

### Lessons for AutoBuilder

1. **Planner-Coder-Critic maps to AutoBuilder's planner/coder/reviewer** -- but Devin's critic is adversarial (looks for security issues + logic errors), not just quality-checking. AutoBuilder's reviewer agent could benefit from an adversarial stance.
2. **Plan-approve gates before execution** -- Devin requires human plan approval before coding. AutoBuilder's Director->PM->Worker hierarchy should consider plan checkpoints at each level.
3. **Ambiguity is the enemy of autonomous agents** -- Devin's biggest failure mode is unclear requirements. AutoBuilder's spec decomposition phase must produce unambiguous deliverable specifications. The PM's role in spec refinement is critical.
4. **Fleet deployment = AutoBuilder's ParallelAgent** -- Devin's fleet pattern is exactly what AutoBuilder does with parallel deliverable execution, but AutoBuilder adds dependency-aware batching and regression testing between batches.
5. **Automatic codebase documentation** -- Devin Wiki auto-indexes repos every few hours. AutoBuilder could generate project context artifacts as a workflow byproduct.

---

## 4. Factory.ai Droids

**Source**: https://factory.ai/news/code-droid-technical-report, https://factory.ai

### Architecture

**Specialized Droids per SDLC stage:**
- **CodeDroid**: Implementation
- **ReviewDroid**: Pull request review
- **QADroid**: Testing
- Additional droids for specific workflow stages

Each droid operates in a **strictly sandboxed environment** with enterprise-grade audit trails.

**Two proprietary systems for codebase understanding:**
- **HyperCode**: Multi-resolution code representations -- explicit graph relationships + implicit latent-space similarity mappings
- **ByteRank**: Retrieval algorithm leveraging HyperCode for task-relevant code location

### Multi-Model Architecture

Strategically deploys different models (Anthropic, OpenAI) for specific subtasks. Generates **multiple solution trajectories** and validates against existing and self-generated tests.

### Quality Enforcement

- **DroidShield**: Internal static analysis layer performing real-time analysis for security vulnerabilities, bugs, and IP breaches before commit
- Multi-trajectory validation: generates multiple solutions, tests all, selects best
- Full action logging and explainability for every decision

### Context Intelligence

Native integrations (GitHub/GitLab, Jira, Slack, PagerDuty) + real-time indexing. "Context engineering" ensures droids understand repo structure, file relationships, and project history.

LLM-agnostic and interface-agnostic: works from terminal, IDE, Slack, Linear, browsers, or custom scripts.

### Strengths

- Specialized droids per SDLC stage (not one agent for everything)
- HyperCode/ByteRank for deep codebase understanding
- Multi-trajectory generation with test-based selection
- DroidShield as a deterministic safety net

### Weaknesses

- Proprietary, closed system -- no reusable patterns for external adoption
- Limited public technical detail on orchestration between droids
- SWE-bench scores (31.67%) suggest room for improvement on complex tasks

### Lessons for AutoBuilder

1. **Specialized agents per SDLC stage is the right model** -- Factory validates AutoBuilder's approach of planner/coder/reviewer/tester as separate agents rather than one monolithic agent
2. **Multi-trajectory generation** -- generating multiple solutions and test-selecting the best one is expensive but effective. Could be a configurable quality mode for critical deliverables in AutoBuilder.
3. **DroidShield = deterministic safety layer** -- analogous to AutoBuilder's LinterAgent/TestRunnerAgent as non-LLM quality gates. Factory's addition of IP breach detection is worth noting.
4. **Deep codebase indexing** -- HyperCode's graph+embedding approach for code understanding could inform AutoBuilder's MemoryService design for project context.

---

## 5. OpenAI Codex

**Source**: https://openai.com/index/introducing-codex/, https://developers.openai.com/codex/multi-agent/

### Architecture

**Agent loop architecture** (detailed in "Unrolling the Codex Agent Loop"):
- Each conversation turn: assemble inputs -> run inference -> execute tools -> feed results back into context -> repeat until loop ends
- **Sandboxed execution**: each task runs in its own cloud sandbox, preloaded with repo
- Native system-level sandboxing (open source, configurable)
- Prompt caching for linear-time model sampling despite quadratic payload growth

### Multi-Agent Orchestration

Codex supports **multi-agent workflows** via the Agents SDK:
- Spawn specialized agents in parallel, collect results
- Each sub-agent can have different model configurations, reasoning effort, sandbox modes, and instructions
- Sub-agents inherit parent sandbox policy
- Automatic **trace recording** of every prompt, tool call, and hand-off for inspection

**Skills system**: Bundles of instructions, resources, and scripts so Codex can reliably connect to tools, run workflows, and follow team preferences.

### Integration Pattern

Codex CLI is exposed as an **MCP server**, orchestrated via OpenAI Agents SDK:
- Enables deterministic, reviewable workflows
- Scales from single agent to complete software delivery pipeline
- AGENTS.md for repo-level agent configuration

### Strengths

- Multi-agent with explicit parallel execution and trace recording
- Skills as first-class bundled capabilities
- MCP server exposure enables external orchestration
- Configurable sandboxing at system level
- Trace dashboard for debugging agent runs

### Weaknesses

- Tied to OpenAI ecosystem (GPT models)
- Skills system is relatively new (March 2026), limited documentation
- No built-in hierarchical supervision pattern
- Workflow composition is ad-hoc (Agents SDK scripting, not declarative)

### Lessons for AutoBuilder

1. **Trace recording is table stakes** -- every prompt, tool call, hand-off must be inspectable. AutoBuilder's event bus (Redis Streams) provides this foundation; the presentation layer needs to surface it clearly.
2. **Skills as bundled capabilities** -- Codex Skills bundle instructions + resources + scripts. This validates AutoBuilder's SKILL.md approach but suggests skills should also bundle script assets, not just instruction text.
3. **MCP as the external tool interface** -- Codex exposes itself as an MCP server AND consumes MCP tools. AutoBuilder's GlobalToolset could expose an MCP interface for external tool integration.
4. **Sub-agent inheritance of sandbox policy** -- when AutoBuilder spawns parallel deliverable workers, they should inherit security constraints from the PM level without re-declaration.

---

## 6. Google Jules

**Source**: https://jules.google.com/, https://jules.google/docs/

### Architecture

- Powered by **Gemini 2.5 Pro** (later Gemini 3 Pro)
- Every task runs in a **dedicated, sandboxed VM on Google Cloud**
- VMs are ephemeral: destroyed after task completion, no persistent containers or shared volumes
- GitHub-native integration

### Workflow Model

**Perceive-Plan-Execute-Evaluate loop:**
1. **Perceive**: Analyze codebase, understand problem
2. **Plan**: Generate detailed step-by-step roadmap (presented to user for approval)
3. **Execute**: Spin up VM, implement changes
4. **Evaluate**: Internal critic evaluates patches, checks beyond syntax/linting

Plan-approve gate before execution (similar to Devin).

### AGENTS.md Standard

Jules reads `AGENTS.md` from repo root -- a README designed for AI coding agents. Adopted by 20,000+ open-source projects. Provides repository-specific context, conventions, and instructions.

### Quality Enforcement

- Internal **critic function** evaluates patches (peer review)
- Developers review plan before execution
- Developers review final PR for project standard alignment
- Every step is "observable, traceable, and reversible"

### Strengths

- Ephemeral VM isolation (strongest sandboxing model observed)
- AGENTS.md as an open standard for agent context
- Plan-approve-execute model gives human control
- Tight GitHub integration

### Weaknesses

- Single-agent, single-task model
- No workflow composition or multi-agent coordination
- Tied to Google Cloud and Gemini models
- Limited to GitHub (no GitLab, Bitbucket)

### Lessons for AutoBuilder

1. **Ephemeral execution environments** -- Jules' destroy-after-completion VMs are the gold standard for isolation. AutoBuilder's git worktree per deliverable is a lighter-weight version of this principle.
2. **AGENTS.md as open standard** -- with 20,000+ repos adopting it, this is becoming a de facto standard. AutoBuilder should read and respect AGENTS.md files in target repositories as part of project context loading.
3. **Perceive-Plan-Execute-Evaluate maps to AutoBuilder's pipeline** -- nearly identical to the planner->coder->linter/tester->reviewer sequence.

---

## 7. Amazon Q Developer

**Source**: https://aws.amazon.com/q/developer/

### Architecture

Agent-based system that autonomously performs multi-step workflows:
- Analyzes existing codebase
- Maps step-by-step implementation plan
- Upon approval, executes code changes and tests
- Reads/writes files locally, generates diffs, runs shell commands
- Real-time updates during execution

### Quality Enforcement

- SWE-bench Verified: 66% (among top-ranking models)
- Automatic test generation and execution
- Human approval before implementation

### Strengths

- Deep AWS ecosystem integration
- Broad language support (Python, Java, JS, TS, Go, Rust, etc.)
- Strong benchmarks
- Scales to enterprise via AWS infrastructure

### Weaknesses

- AWS-centric (tight platform coupling)
- Limited public architecture detail
- No workflow composition primitives
- Single-agent model

### Lessons for AutoBuilder

1. **Broad language/framework support is table stakes** -- AutoBuilder workflows should be language-agnostic; the workflow system should not assume any particular technology stack in target projects.
2. **Real-time updates during execution** -- streaming progress events to clients. AutoBuilder's SSE + Redis Streams architecture already supports this.

---

## 8. MetaGPT

**Source**: https://github.com/FoundationAgents/MetaGPT, ICLR 2024 paper

### Architecture

**Simulated software company** with role-based AI agents following Standard Operating Procedures (SOPs):
- Product Manager: Creates PRD
- Architect: System design
- Engineer: Implementation
- QA: Testing

Agents communicate through **structured outputs** (not free-form conversation). Each agent generates artifacts that serve as input to the next agent in the assembly line.

### Workflow Model

**Assembly line paradigm with SOPs:**
1. User prompt -> Product Manager generates PRD
2. PRD -> Architect generates system design
3. System design -> Engineer generates code
4. Code -> QA generates and runs tests

SOPs define required output format at each stage, enabling deterministic handoffs between agents.

### Key Innovation

Encoding human organizational workflows (how real software teams operate) into agent coordination protocols. Agents don't just chat -- they produce formal artifacts that downstream agents consume.

### Strengths

- Role-based decomposition mirrors real engineering teams
- Structured handoffs via SOPs prevent drift
- Assembly line model enables clear quality gates between stages
- Open source with academic rigor

### Weaknesses

- Rigid sequential pipeline (no parallel execution)
- SOPs are static -- no runtime adaptation
- No iteration/review loops within stages
- Overly academic -- practical deployment challenging
- Single-pass execution (no retry on failure)

### Lessons for AutoBuilder

1. **Structured handoffs between agents are critical** -- MetaGPT's SOP-driven artifact passing is more reliable than free-form conversation. AutoBuilder's state keys (e.g., `worker:plan`, `worker:code_output`) serve this purpose but should have schema validation.
2. **Role-based decomposition works** -- validates AutoBuilder's Director/PM/Worker hierarchy. MetaGPT proves that mimicking real org structures produces better results than monolithic agents.
3. **SOPs need runtime adaptability** -- MetaGPT's static SOPs are a weakness. AutoBuilder's skill-based dynamic instruction assembly (InstructionAssembler) addresses this.
4. **Missing iteration loops are a critical gap** -- MetaGPT's single-pass execution means errors propagate. AutoBuilder's ReviewCycle (LoopAgent with max iterations) is essential.

---

## 9. Cross-System Comparison

### Architecture Patterns

| System | Agent Model | Execution Isolation | Workflow Composition | Multi-Agent |
|--------|------------|---------------------|---------------------|-------------|
| Stripe Minions | Single agent (goose fork) | Devbox (pre-warmed VM) | None (one-shot tasks) | Parallel independent runs |
| Shopify Roast | Sequential cogs | Local process | DSL-based (Ruby/YAML) | Sequential chain |
| Devin | Tri-model (Planner/Coder/Critic) | Cloud VM per instance | None (per-task) | Fleet deployment (parallel instances) |
| Factory Droids | Specialized droids per stage | Sandboxed environment | SDLC-stage pipeline | Stage-specialized coordination |
| OpenAI Codex | Agent loop + sub-agents | Cloud sandbox per task | Agents SDK scripting | Explicit parallel sub-agents |
| Google Jules | Single agent (Gemini) | Ephemeral VM | None (per-task) | None |
| Amazon Q | Single agent | Local environment | None | None |
| MetaGPT | Role-based team | Local process | SOP assembly line | Sequential role handoffs |

### Quality Enforcement Comparison

| System | Deterministic Gates | LLM Review | Iteration Limits | Human Approval |
|--------|-------------------|------------|------------------|----------------|
| Stripe Minions | Lint + selective CI | None explicit | 2 CI rounds max | PR review |
| Shopify Roast | Shell commands, type checkers | CodingAgent iteration | Repeat cog conditions | None built-in |
| Devin | Unit tests + CI | Critic model | Not documented | Plan approval |
| Factory Droids | DroidShield static analysis | Multi-trajectory selection | Not documented | Not documented |
| OpenAI Codex | Sandbox tool restrictions | Model self-correction | Per-agent configurable | Optional per-step |
| Google Jules | Build/test in VM | Internal critic | Not documented | Plan + PR approval |
| Amazon Q | Test execution | Self-correction | Not documented | Plan approval |
| MetaGPT | SOP format validation | None | None (single-pass) | None |
| **AutoBuilder** | **Lint + Test + Regression (mandatory)** | **Reviewer agent** | **Configurable max (default 3)** | **CEO queue + checkpoints** |

### Context Engineering

| System | Repo Context | Agent Instructions | External Tools | Memory |
|--------|-------------|-------------------|----------------|--------|
| Stripe Minions | Sourcegraph + MCP | Subdirectory-scoped rules | Toolshed (400+ MCP tools) | None |
| Shopify Roast | Filesystem access | Prompt files per step | Shell commands | Session transcript |
| Devin | Auto-indexed wiki | Built-in | Browser, terminal | Cross-session wiki |
| Factory Droids | HyperCode + ByteRank | Context engineering | Native integrations | Real-time index |
| OpenAI Codex | AGENTS.md | Skills bundles | MCP tools | None |
| Google Jules | AGENTS.md | AGENTS.md | GitHub-native | None |
| Amazon Q | Codebase analysis | Built-in | AWS ecosystem | None |
| MetaGPT | Repository loading | SOP templates | Code execution | None |
| **AutoBuilder** | **MemoryLoaderAgent + Skills** | **3-scope cascade + InstructionAssembler** | **GlobalToolset + MCP** | **MemoryService (PostgreSQL)** |

---

## 10. Patterns Worth Adopting

### Pattern 1: Hard Iteration Limits (Stripe)

Stripe caps at 2 CI rounds. This is not a weakness -- it is a deliberate design choice that prevents runaway costs and diminishing returns from LLM-in-a-loop.

**AutoBuilder alignment**: Already have `max_iterations` on LoopAgent/ReviewCycle. Validate that this is strictly enforced and configurable per workflow, not just per agent.

### Pattern 2: Deterministic-First, LLM-Second (Roast)

Roast's "Boba" workflow: `sed` cleanup -> Sorbet autocorrect -> CodingAgent for remaining issues. Deterministic steps handle the predictable 80%; LLM handles the unpredictable 20%.

**AutoBuilder alignment**: Pipeline stages should always try deterministic resolution before LLM iteration. The DiagnosticsAgent pattern (hybrid: deterministic analysis -> LLM reasoning) embodies this.

### Pattern 3: Plan-Approve-Execute Gates (Devin, Jules, Amazon Q)

Three independent systems converged on the same pattern: generate plan, show to human, execute only after approval.

**AutoBuilder alignment**: The CEO queue and Director checkpoints serve this purpose. Consider whether PM-level plan approval (before worker execution) should be a configurable gate, not just Director-level.

### Pattern 4: Session Replay / Checkpoint Resumability (Roast)

Resume from any step avoids re-running expensive earlier steps during development and debugging.

**AutoBuilder alignment**: `checkpoint_project` after each batch provides crash recovery, but step-level resumability within a deliverable pipeline would reduce iteration costs during development.

### Pattern 5: Specialized Agents per SDLC Stage (Factory)

CodeDroid, ReviewDroid, QADroid -- not one agent doing everything.

**AutoBuilder alignment**: Already implemented with planner/coder/reviewer/linter/tester separation. Validated by external systems.

### Pattern 6: AGENTS.md as Open Standard (Jules, Codex)

20,000+ repos have AGENTS.md files. This is becoming the standard way to communicate repo conventions to AI agents.

**AutoBuilder alignment**: AutoBuilder should read AGENTS.md from target repositories during project context loading and inject relevant content as a PROJECT instruction fragment.

### Pattern 7: Trace Recording (Codex)

Every prompt, tool call, and hand-off recorded for post-hoc inspection.

**AutoBuilder alignment**: Redis Streams event bus captures events. Ensure the trace is complete enough for full replay -- every LLM call, tool invocation, state mutation, and agent transition should be traceable.

### Pattern 8: Multi-Trajectory Generation (Factory)

Generate multiple solution candidates, validate against tests, select the best.

**AutoBuilder alignment**: Expensive but valuable for high-stakes deliverables. Could be a quality mode setting in WORKFLOW.yaml: `quality_mode: standard | thorough` where thorough generates N candidates.

---

## 11. Anti-Patterns to Avoid

### Anti-Pattern 1: Unlimited LLM Iteration

No system that ships at scale allows unbounded LLM retry loops. Stripe caps at 2, Roast uses conditional `repeat`, Codex makes it configurable. Infinite loops are a cost and quality trap -- LLMs rarely improve after the 3rd attempt at the same problem.

### Anti-Pattern 2: Monolithic Single-Agent Design

Jules, Amazon Q, and early Devin use single-agent models. Every system that achieves higher quality (Stripe with tooling, Devin 2.0 with Planner/Coder/Critic, Factory with specialized Droids) moves toward multi-agent or multi-stage designs. AutoBuilder's hierarchical multi-agent approach is validated.

### Anti-Pattern 3: Free-Form Inter-Agent Communication

MetaGPT's key insight: structured handoffs via SOPs outperform free-form agent conversation. When agents "chat" to coordinate, output quality degrades. AutoBuilder should enforce typed state keys for inter-agent data flow, not rely on conversation context.

### Anti-Pattern 4: Static SOPs Without Runtime Adaptation

MetaGPT's static SOPs work for toy examples but break on real projects. AutoBuilder's InstructionAssembler with dynamic fragment composition addresses this, but workflow-level adaptation (e.g., skipping lint stages for documentation-only deliverables) should also be supported.

### Anti-Pattern 5: Skipping Plan Approval for Complex Tasks

Every production system (Devin, Jules, Amazon Q) requires human plan approval before execution. AutoBuilder's CEO queue serves this role. Do not optimize it away for efficiency -- the cost of executing a wrong plan far exceeds the cost of a human review checkpoint.

### Anti-Pattern 6: Coupling Agent Identity to Workflow

No agent should "know" which workflow it's part of. Stripe's conditional rules, Codex's Skills, and AutoBuilder's 3-scope agent definitions all enable the same agent definition to operate differently in different workflow contexts. Agent identity should be workflow-agnostic; workflow context should be injected.

---

## 12. Novel Insights for AutoBuilder

### Insight 1: AutoBuilder's Hierarchical Supervision is Unique

None of the surveyed systems implement a true Director->PM->Worker hierarchy with persistent supervision. Stripe has flat independent runs. Devin has fleet deployment but no coordinator. Factory has stage-specialized droids but no meta-orchestrator. MetaGPT has role-based agents but no supervision loop.

AutoBuilder's PM-as-outer-loop with Director oversight and CEO escalation is architecturally differentiated. This is a genuine competitive advantage for complex, multi-deliverable projects.

### Insight 2: Workflow-as-Plugin is Rare

Only Roast provides true workflow composition as a first-class concept. Most systems hardcode a single workflow (code task -> PR). AutoBuilder's WORKFLOW.yaml manifest + WorkflowRegistry + pluggable pipelines addresses a gap that every other system will eventually need.

The compound workflow concept (auto-design -> auto-market) is not implemented by any surveyed system. This is a Phase 2 differentiator.

### Insight 3: Deterministic Quality Gates are Under-Invested Across the Industry

Most systems treat quality as "run tests, hope they pass." Only Stripe (progressive feedback with hard limits) and Factory (DroidShield static analysis) invest in deterministic quality enforcement. AutoBuilder's mandatory lint/test/review gates with deterministic enforcement are architecturally sound but should be more prominently documented as a differentiator.

### Insight 4: The "Context Engineering" Arms Race

Factory's HyperCode, Devin's auto-indexing wiki, Stripe's Toolshed -- every system is racing to give agents better project context. AutoBuilder's three-pronged approach (MemoryLoaderAgent + SkillLoaderAgent + InstructionAssembler) is well-positioned, but the quality of context engineering will likely determine competitive outcomes.

### Insight 5: Skills Convergence

OpenAI Codex Skills (instructions + resources + scripts), AutoBuilder Skills (SKILL.md), Stripe's agent rule files, and Jules' AGENTS.md all converge on the same concept: bundled, domain-specific knowledge that shapes agent behavior. The industry is standardizing around "skills as configuration, not code." AutoBuilder's skill system is ahead of most competitors.

### Insight 6: The Interleaving Pattern is the Right Architecture

Roast and Stripe both demonstrate that the highest-quality results come from **interleaving** deterministic and non-deterministic steps, not running them in separate phases. AutoBuilder's pipeline design (SkillLoader [det] -> Planner [LLM] -> Coder [LLM] -> Linter [det] -> Tester [det] -> Reviewer [LLM]) already implements this pattern. The key addition from Roast is that even within an "LLM step," deterministic sub-steps should be attempted first.

### Insight 7: Workflow Scale Spectrum

Surveyed systems cluster at two extremes:
- **Micro-tasks**: One issue -> one PR (Stripe, Jules, Amazon Q)
- **Full-project**: Requirements -> working software (MetaGPT, partially Devin)

AutoBuilder's workflow system should explicitly support the full spectrum: single-pass workflows (micro-tasks), sequential pipelines (medium complexity), and batch-parallel workflows (full projects). The `pipeline_type` field in WORKFLOW.yaml (batch_parallel | sequential | single_pass) already captures this.

---

## Source Index

- Stripe Minions: https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents
- Shopify Roast: https://github.com/Shopify/roast, https://shopify.engineering/introducing-roast
- Devin 2.0: https://cognition.ai/blog/devin-2
- Devin Performance Review: https://cognition.ai/blog/devin-annual-performance-review-2025
- Devin Agents 101: https://devin.ai/agents101
- Factory.ai Code Droid: https://factory.ai/news/code-droid-technical-report
- Factory.ai GA: https://factory.ai/news/factory-is-ga
- OpenAI Codex: https://openai.com/index/introducing-codex/
- OpenAI Codex Multi-Agent: https://developers.openai.com/codex/multi-agent/
- OpenAI Codex Agent Loop: https://openai.com/index/unrolling-the-codex-agent-loop/
- Google Jules: https://jules.google.com/, https://jules.google/docs/
- Amazon Q Developer: https://aws.amazon.com/q/developer/
- MetaGPT: https://github.com/FoundationAgents/MetaGPT

---

**Document Version:** 1.0
**Research Date:** 2026-03-12
**Purpose:** Phase 7 Workflow Composition System design input
