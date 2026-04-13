[<- Architecture Overview](../02-ARCHITECTURE.md)

# Context Optimizer

**AutoBuilder Platform**
**Context Optimization Architecture Reference**

---

## Status

**Phase 14 — Pre-Design Sketch.** This document captures architectural intent from Phase 7b shaping, enriched with research findings from the context optimization research spike (2026-04-12). It will be expanded to a full L2 spec during Phase 14 shaping.

**Research source:** `.dev/.research/260412_context-optimization/` — algorithm landscape survey, GEPA evaluation, eval suite design patterns, architecture/API/data model design, cost modeling, and 24 academic/industry references.

---

## Why This Exists

Every agent invocation assembles context from multiple sources: instruction fragments (SAFETY, IDENTITY, GOVERNANCE, PROJECT, TASK, SKILL), memory, skills, and node prompts. The quality of output is directly proportional to the quality and relevance of this assembled context — within a fixed token budget.

Today, context assembly is rule-based: InstructionAssembler composes fragments by type, SkillLoaderAgent loads matched skills, MemoryLoaderAgent loads relevant memories. This works, but it is not optimized. Some skills may add noise. Some memories may be irrelevant. Some instruction fragments may be redundant for a given task. The token budget is consumed by context that may not improve output.

The problem compounds across three axes:

1. **LLM models change** — Provider updates, new model versions, or model swaps alter how instructions are interpreted. Context optimized for Claude Sonnet 4.5 may underperform on Sonnet 4.6.
2. **New workflows are created** — Each new workflow type (auto-design, auto-research, etc.) requires context that must be tuned against measurable outcomes.
3. **Drift over time** — Accumulated changes to skills, tools, and pipeline structure can subtly degrade context effectiveness.

Manual prompt iteration is unscalable. Humans cannot run hundreds of simulation variations, track which changes produced which improvements, or systematically explore the optimization landscape. The prompt optimization problem is **black-box, discrete, non-differentiable** — the search space is natural language, high-dimensional, combinatorial, and non-continuous.

The context optimizer makes context assembly **evidence-based** — measuring which context configurations produce the best output and tuning assembly toward those configurations over time.

---

## Core Architecture

### What Gets Optimized

| Context Source | Optimization Question | Mechanism |
|---------------|----------------------|-----------|
| **Instruction fragments** | Which fragments matter most for this node type? | Fragment-level quality signal correlation |
| **Skills** | Which skills actually improve output for this deliverable type? | Skill inclusion/exclusion A/B testing |
| **Memory** | Which memories are worth the token cost? | Memory relevance scoring refinement |
| **Node prompts** | Can the prompt be tightened without losing intent? | Prompt compression with quality regression testing |
| **Model routing** | Which model performs best for this specific task profile? | Per-node-type model performance tracking |

### Optimization Engine: GEPA

The research spike evaluated five algorithm families for prompt optimization. **GEPA (Reflective Evolutionary + Pareto)** was selected as the core optimization engine.

**Paper**: "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning" (Agrawal et al., 2025). ICLR 2026 (Oral). MIT license.

| Family | Examples | Strengths | Weaknesses | Decision |
|--------|----------|-----------|------------|----------|
| Bayesian Surrogate | DSPy MIPROv2 | Surrogate model improves proposals over time | Sample-hungry, higher cost | Rejected: GEPA outperforms by 10+ pp |
| LLM-as-Optimizer | OPRO (DeepMind) | Simple, uses LLM to propose improvements from history | No principled exploration, requires strong optimizer model | Rejected: no exploration strategy |
| Evolutionary | EvoPrompt | Embarrassingly parallel, population-based | Blind mutations — knows *that* something failed, not *why* | Rejected: reflection > blind mutation |
| Textual Gradient | TextGrad, ProTeGi | PyTorch-like API, gradient analogy | Better for single variables, less proven on multi-component | Rejected: multi-component is our case |
| **Reflective Evolutionary + Pareto** | **GEPA** | Reflection-based intelligent mutations, Pareto diversity, sample-efficient | Newer community (growing fast) | **Selected** |

**Why GEPA over alternatives:**

1. **Reflection over blind mutation.** GEPA's reflector LLM reads full execution traces (inputs, outputs, errors, scores) and diagnoses *why* a candidate failed — then proposes targeted textual mutations. It understands word selection, instruction ordering, emphasis, and phrasing impact.
2. **Pareto frontier = built-in lineage tracking.** Instead of evolving only the global best, GEPA maintains a frontier of candidates that each excel on different subsets of test cases. Candidates are never discarded if they're best at *something*. Full genealogy with tracked mutation history.
3. **Sample efficient = affordable.** Outperforms GRPO (RL) by 6-20% while using up to 35x fewer rollouts. Estimated cost: ~$0.90 per 150-evaluation campaign using cheap task models.
4. **Already integrated with Google ADK.** Same ecosystem as AutoBuilder. ADK's `adk optimize` uses GEPA internally — but we use the standalone `optimize_anything` API directly for broader control (ADK's wrapper only handles root agent instructions).
5. **Uses LiteLLM.** Same routing layer AutoBuilder uses. Cheap models for simulation, expensive models for reflection — natively supported.
6. **Optimizes any text artifact.** The `optimize_anything` API handles prompts, code, agent architectures, configurations, and more. Not prompt-only.
7. **Production-proven.** In use at Shopify, Databricks, Dropbox, OpenAI, Pydantic, MLflow, Comet ML, and 50+ organizations.

**Integration path:** Standalone `gepa` package via `optimize_anything` — no DSPy dependency required. The standalone API is cleaner for our use case (optimizing raw context strings, not DSPy program modules).

### GEPA Core Algorithm

```
1. Initialize candidate pool with seed context
2. Loop until budget exhausted or convergence:
   a. Sample a candidate from the Pareto frontier (weighted by coverage)
   b. Execute candidate on a minibatch of eval cases using cheap task model
   c. Capture full execution traces (inputs, outputs, errors, reasoning)
   d. Reflect — strong model reads traces + feedback, diagnoses failures,
      proposes targeted mutation to context
   e. Evaluate mutated candidate on the minibatch
   f. If improved: evaluate on full Pareto validation set
   g. Update Pareto frontier (keep if best on any subset)
   h. Optionally: merge two frontier candidates (crossover by module lineage)
3. Return candidate with best aggregate validation score
```

**Two mutation strategies (selected adaptively):**
- **Reflective Mutation**: Sample one candidate, execute, reflect on traces, propose improvement. Focused, directed.
- **System-Aware Merge**: Sample two frontier candidates, combine modules based on evolution history. Creates hybrids with complementary strengths.

**Key concepts:**
- **Actionable Side Information (ASI)**: Rich textual feedback logged during evaluation — error messages, structural mismatches, reasoning traces, constraint violations. This is what makes GEPA's mutations targeted rather than random.
- **Pareto Frontier**: Non-dominated candidate set. Selection probability proportional to coverage (instances where candidate is best). Prevents local optima and preserves diverse strategies.
- **Candidate Lineage**: Full ancestry tree tracking which candidate descended from which, what mutations were applied, and score deltas at each step.

### Evaluation Modes: Intrinsic vs. Extrinsic

The optimizer supports two evaluation modes. Every eval case declares which mode it uses.

**Intrinsic evaluation** tests the target component's output directly. One LLM call, deterministic validation on the result. Use when the component produces a final, independently verifiable artifact.
- Coder agent instructions produces code, validated by compile + run tests
- Formatter agent instructions produces formatted output, validated by schema check
- Any agent whose output IS the deliverable

**Extrinsic evaluation** tests the target component's output by its downstream impact. Multiple LLM calls in a causal chain — the optimized component's output becomes input context for subsequent fixed components, and validation happens at the end of the chain. Use when the component produces *intermediate context* consumed by other agents.
- Planner instructions produces plan, fed to Coder (fixed), validated by compile + run tests
- Decomposer instructions produces deliverable list, fed to Planner (fixed), validated structurally
- Reviewer instructions produces review feedback, fed to Coder (fixed), validated by diff quality

The key constraint: **only one component in the chain is the optimization target** (the free variable). All other chain participants use fixed instructions. GEPA mutates the target; the chain measures downstream impact.

```
INTRINSIC (single-hop):

  ┌─────────────────┐       ┌────────────────┐
  │ Target context   │──LLM──│ Output         │──> Deterministic validation
  │ (GEPA mutates)   │       │                │
  └─────────────────┘       └────────────────┘

EXTRINSIC (multi-hop):

  ┌─────────────────┐       ┌────────────┐       ┌──────────────┐       ┌────────────────┐
  │ Target context   │──LLM──│ Intermediate│──────│ Fixed agent  │──LLM──│ Final output   │──> Deterministic
  │ (GEPA mutates)   │       │ output      │      │ (not mutated)│       │                │    validation
  └─────────────────┘       └────────────┘       └──────────────┘       └────────────────┘
```

**Cost implications**: Extrinsic cases cost more per evaluation (N LLM calls per hop). Suites should mix both modes — intrinsic for fast, cheap signal on obvious quality dimensions; extrinsic for high-value decision-quality tests that only reveal themselves downstream. Recommended starting ratio: 60% intrinsic / 40% extrinsic.

**ASI richness**: Extrinsic evaluation produces richer Actionable Side Information for GEPA's reflector because the full chain trace is logged — the reflector can see not just that the final output failed, but *where* in the chain the quality degraded. This enables more targeted mutations.

### Optimization Loop

```
Agent invocation
  -> Context assembled (fragments + skills + memory + prompt)
  -> Agent executes
  -> Output quality signals collected
     (gate results, review scores, escalation rate, user feedback)
  -> Context configuration + quality signal stored
  -> Over N invocations, statistical patterns emerge:
     "For node type 'code', including skill 'api-endpoint' improves
      gate pass rate by 15%. Skill 'database-migration' has no effect."
  -> Context assembly rules updated:
     Skill 'api-endpoint' prioritized for 'code' nodes
     Skill 'database-migration' deprioritized (still available, lower token priority)
```

### Quality Signals — Evaluation Dimensions

The optimizer measures quality across four concrete dimensions, not a single aggregate score:

**1. Intelligence** — The agent makes smart decisions. Catches non-obvious dependencies, handles ambiguity without over-committing, decomposes at the right granularity. Tests use contrastive boundary pairs and ambiguous specifications that require genuine reasoning.

**2. Compliance** — The agent follows the rules encoded in its context. If the instructions say "always validate before committing" or "use SequentialAgent not custom loops," the model does that. Not sometimes — always. Tests encode specific behavioral rules and verify strict adherence.

**3. Tool Discipline** — The agent calls the right tools, with correct arguments, at the right pipeline stage. Doesn't hallucinate tool names, doesn't skip required tools, doesn't call tools unnecessarily. Tests present scenarios where tool selection matters and validate tool call sequence and parameters.

**4. Deliverable Quality** — The final output actually solves the request. Code runs, plans are actionable, decompositions are implementable. Tests validate the end artifact deterministically — compile, execute, schema-validate.

GEPA's Pareto frontier naturally handles multi-dimensional optimization — candidates that excel on compliance but sacrifice intelligence are preserved alongside candidates that are brilliant but sloppy. GEPA's merge operation combines their strengths.

### Production Signal Sources

| Signal | Source | Weight |
|--------|--------|--------|
| **Gate pass rate** | Quality gates | High — direct evidence of correctness |
| **Review cycle count** | Review loop iterations before approval | Medium — fewer cycles = better first-pass quality |
| **Escalation rate** | Escalations per deliverable | Medium — fewer escalations = better autonomous handling |
| **Rework rate** | Deliverables requiring retry/fix | High — rework is waste |
| **CEO intervention rate** | CEO queue items per TaskGroup | Low — some intervention is expected |
| **Cost efficiency** | Tokens per successful deliverable | Low — cost matters but quality matters more |

### Non-Goals for the Optimizer

- **Not prompt rewriting**: The optimizer does not rewrite node prompts with LLM. It measures which prompts work and flags underperformers for human revision.
- **Not model training**: No fine-tuning. Optimization is in assembly, not in the model.
- **Not real-time**: Optimization runs offline against accumulated data, not inline during execution. Updated configurations apply to the next workflow run, not the current one.

---

## Eval Suite Design

### Suite Architecture: Hybrid Pattern

Three eval suite design patterns were researched (GUIDE/AAAI 2026, Item Response Theory/Fluid Benchmarking, EvolveCoder adversarial-discriminative cycling, Anthropic's capability/regression methodology). The recommended design is a hybrid combining all three.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Eval Suite Structure                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  GATE TIER (3-5 cases)                                          │
│  Hard gates. Format, schema, basic compliance.                   │
│  Score = 0 on any failure.                                       │
│  Dimensions: compliance, tool_discipline                         │
│                                                                  │
│  CORE TIER (10-15 cases)                                        │
│  Contrastive boundary pairs. High discriminative power per case. │
│  Dimensions: intelligence, compliance                            │
│                                                                  │
│  FRONTIER TIER (8-12 cases)                                     │
│  Adversarial-discriminative cases. Evolve between campaigns.     │
│  Dimensions: intelligence, tool_discipline                       │
│                                                                  │
│  REGRESSION TIER (graduated cases, grows over time)              │
│  Low-weight, previously-solved cases that prevent backsliding.   │
│  All dimensions.                                                 │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Total: 25-35 active cases per campaign                          │
│  Small enough to be cheap. Discriminative enough for real signal.│
│  Adaptive enough to never plateau.                               │
└─────────────────────────────────────────────────────────────────┘
```

### Pattern 1: Contrastive Boundary Pairs

**Source**: GUIDE framework (Grading Using Iteratively Designed Exemplars, AAAI 2026).

Instead of testing "can the planner decompose this spec," test "can the planner distinguish between two specs that *look* similar but require fundamentally different decompositions?"

Each contrastive pair has two cases:
- **Case A**: Surface cues SUGGEST the principle applies, but it doesn't.
- **Case B**: NO surface cues, but the principle DOES apply.
- Getting BOTH right = understands the principle. Getting only one right = pattern matching on keywords.

**Why this maximizes improvement**: Most eval suites waste cases on things the model already gets right. Boundary pairs concentrate all signal at the decision frontier — the exact place where instruction quality matters most. GEPA converges faster because every eval provides maximum information.

### Pattern 2: Adaptive Difficulty Calibration (IRT-Inspired)

**Source**: Item Response Theory and Fluid Benchmarking research.

The value of an evaluation sample depends on the model's current capability level. Easy cases every model passes are wasted evaluations. Impossible cases no model passes are also wasted. The informative cases are at the model's current capability boundary. Hence the tiered structure: gate (trivial), core (moderate, 60-80% pass rate), frontier (hard, 20-40% pass rate).

### Pattern 3: Adversarial-Discriminative Cycling

**Source**: Synthesized from EvolveCoder (adversarial + discriminative test generation) and Anthropic's capability/regression eval methodology.

A static eval suite has a ceiling. Once the optimizer "solves" all cases, further runs produce zero signal. The suite itself must evolve between campaigns:

1. **Adversarial Discovery**: Run current best context against broad challenge set. Identify failure cases.
2. **Discriminative Sharpening**: From failures, construct minimal pairs that isolate the specific weakness.
3. **Graduation**: Solved cases move to regression tier at low weight (0.1). Never discarded.
4. **Rebalancing**: Keep frontier at 8-12 cases by dropping lowest-information cases.

### Suite Evolution Between Campaigns

```
Campaign N completes with best_context
  -> Evaluate best_context against all cases
  -> Graduate solved core cases (score > 0.95) to regression tier
  -> Cluster remaining failures by ASI-logged reasons
  -> Generate new frontier cases targeting each failure cluster
  -> Rebalance frontier to 8-12 cases
  -> Suite ready for Campaign N+1
```

Key dynamics:
- **Gates kill early.** If basic compliance fails, GEPA does not waste reflection budget analyzing why a frontier case scored poorly. The reflector sees "GATE FAILED" and fixes fundamentals first.
- **Core pairs force principled learning.** Both sides of a contrastive pair must score well, so GEPA cannot "cheat" by adding a keyword that helps one case but hurts its twin. The reflector must propose instruction changes that encode the *reasoning principle*, not a surface heuristic.
- **Frontier targets the current weakest point.** After each campaign, the evolution step clusters failures by their ASI-logged reasons, then generates new cases that isolate those specific weaknesses. The optimizer never runs out of signal.
- **Regression prevents catastrophic forgetting.** Solved cases drop to low weight but never disappear. If a mutation improves frontier scores but regresses on previously-solved cases, the Pareto frontier catches the tradeoff and preserves both variants for merge.

### Suite Generation

Suites are LLM-generated, human-approved. A strong model (Claude Sonnet/Opus) ingests the full context of the optimization target and generates comprehensive test cases across all four evaluation dimensions. Human role is approval, not authorship.

**Critical rule**: Use a **different model family** for test generation than the task model being optimized. If optimizing context for Haiku, generate tests with Sonnet/Opus. This prevents shared blind spots where the generator and evaluator converge on what they *think* is good rather than what actually is.

### Validation Pipeline

All validation is deterministic. No LLM judge calls during scoring. Validation types:

| Type | Purpose |
|------|---------|
| **json_parse** | Can the output be parsed as valid JSON? Gate check. |
| **schema** | Does parsed output match a JSON schema (required fields, types, value ranges)? |
| **execute_code** | Run arbitrary Python validation logic against the output. Most powerful and flexible. |
| **compile** | Extract code from output, compile/syntax-check it. Language-specific. |
| **run_tests** | Extract code from output, run it against provided test cases, report pass/fail count. |
| **regex** | Pattern matching against output (presence/absence of expected patterns). |
| **value_check** | Numeric/range/threshold checks on extracted values. |

Steps with `required=True` are hard gates — any failure zeroes the score. Remaining steps contribute weighted scores.

---

## System Architecture

### System Context

```
                    ┌──────────────┐
                    │   CLI        │
                    │  (typer)     │
                    └──────┬───────┘
                           │
                           v
┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐
│  Dashboard   │──>│   Gateway    │──>│   Optimizer Worker    │
│  (React SPA) │   │  (FastAPI)   │   │   (ARQ + GEPA)       │
└──────────────┘   └──────────────┘   └──────────┬───────────┘
                                                  │
                                        ┌─────────┴──────────┐
                                        v                    v
                                  ┌───────────┐      ┌────────────┐
                                  │ Task LLM  │      │ Reflection │
                                  │ (cheap)   │      │ LLM (smart)│
                                  │ Haiku /   │      │ Sonnet /   │
                                  │ 4o-mini   │      │ Opus       │
                                  └───────────┘      └────────────┘
```

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Context Optimizer                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐   ┌────────────────┐                    │
│  │ Suite Generator │   │ Campaign       │                    │
│  │ (LLM-powered   │   │ Manager        │                    │
│  │  test authoring)│   │ (scheduler)    │                    │
│  └────────────────┘   └───────┬────────┘                    │
│                               │                              │
│  ┌────────────────┐   ┌──────v─────────┐                    │
│  │ Eval Suite      │   │ GEPA Engine    │                    │
│  │ Registry        │   │ (optimize_     │                    │
│  │ (versioned      │   │  anything)     │                    │
│  │  test cases)    │   └───────┬────────┘                    │
│  └────────────────┘           │                              │
│                        ┌──────v─────────┐                    │
│  ┌────────────────┐   │ AutoBuilder    │                    │
│  │ Result Store    │<──│ Adapter        │                    │
│  │ (versioned      │   │ (evaluate +   │                    │
│  │  contexts +     │   │  trace + ASI) │                    │
│  │  lineage)       │   └───────────────┘                    │
│  └────────────────┘                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Standalone API** — The optimizer is a self-contained service callable from CLI, web UI, or programmatically by AutoBuilder. It has no coupling to ADK, agents, or workflow internals.
2. **Isolated evaluation** — Test cases are micro-tests: send context + input to an LLM, score the output. No pipeline execution, no agent orchestration. Minimum effective experiment size.
3. **Eval suites are reusable assets** — Once a suite is human-validated for a target, it is run repeatedly across model changes, drift checks, and re-optimization campaigns. The human approves the *goal*; the machine optimizes toward it.
4. **LLM-generated test suites** — A strong model ingests the full context of the optimization target and generates comprehensive test cases. Human role is approval, not authorship.
5. **Results are versioned and explicit** — Optimized contexts don't auto-deploy. Human reviews delta, approves, then explicitly applies. Automation of the apply step is a future option.

### Codebase Location

```
app/
  optimizer/
    __init__.py
    api.py                   # FastAPI router (mounted on gateway at /optimizer/*)
    schemas.py               # Pydantic request/response models
    models.py                # SQLAlchemy ORM models (EvalSuite, EvalCase, Campaign, Result)
    worker.py                # ARQ task: campaign execution (GEPA wrapper)
    adapter.py               # AutoBuilder GEPA adapter (evaluate + trace + ASI)
    scoring.py               # Validation pipeline implementations
    generator.py             # LLM-based eval suite generation
    cli.py                   # Typer commands (mounted on main CLI)
```

Follows existing patterns: gateway exposes REST endpoints, worker executes via ARQ (same queue infrastructure as workflow execution), database models use existing SQLAlchemy engine + Alembic migrations, LLM calls go through existing LiteLLM router.

---

## Cost Model

### Two-Tier LLM Strategy

| Role | Model | Cost per call | Purpose |
|------|-------|--------------|---------|
| Task (simulation) | Haiku / GPT-4o-mini | ~$0.001 | Run candidate context against test cases |
| Reflection (mutation) | Sonnet / GPT-4o | ~$0.01 | Analyze traces, diagnose failures, propose mutations |
| Generation (suites) | Sonnet / Opus | ~$0.05 | One-time: generate test cases from context |

### Per-Campaign Cost Estimates

Costs vary by eval mode mix. Extrinsic cases cost Nx per hop in the chain.

| Budget | Suite Mix | Task Cost | Reflection Cost | Total | Use Case |
|--------|-----------|-----------|-----------------|-------|----------|
| 150 | 100% intrinsic | $0.15 | $0.75 | ~$0.90 | Single-agent optimization |
| 150 | 60/40 intrinsic/extrinsic (avg 1.8 calls/eval) | $0.27 | $0.75 | ~$1.00 | Typical mixed suite |
| 300 | 60/40 mixed | $0.54 | $1.50 | ~$2.00 | Deep optimization |
| 500 | 60/40 mixed | $0.90 | $2.50 | ~$3.40 | Exhaustive search |

Suite generation is a one-time cost of ~$0.50-$2.00 depending on complexity.

---

## Integration Points

### With InstructionAssembler (existing)
The assembler's fragment composition becomes parameterizable: fragment weights, inclusion/exclusion rules, token budget allocation per fragment type. The optimizer writes configuration; the assembler reads it.

### With SkillLibrary (existing)
Skill matching gains a relevance score informed by historical quality signals. High-signal skills for a given node type are prioritized when token budget is constrained.

### With MemoryLoaderAgent (existing)
Memory search results gain an optimizer-informed relevance boost. Memories correlated with high-quality output for similar tasks rank higher.

### With Workflow Eval Suite (Phase 14)
The eval suite is the optimizer's test harness. A/B testing of context configurations runs within the eval suite, not in production. Production data provides signals; the eval suite validates proposed changes before they apply.

### Triggered by AutoBuilder (future)

- **On model change**: When the LLM router config updates to a new model, trigger re-optimization of all agent contexts against that model.
- **On workflow creation**: When a new workflow is registered, trigger suite generation + optimization for its agent roles.
- **On drift detection**: Periodic re-evaluation of current contexts; if scores drop below threshold, trigger re-optimization.

### Results Applied to AutoBuilder

The `apply` action writes the optimized context back to the target (agent instruction template in database/skill files, skill file content, or WORKFLOW.yaml configuration). The exact mechanism depends on where the target context is stored (database vs. filesystem). The apply endpoint handles routing.

### Observability

- Campaign progress streamed via SSE (same Redis Streams infrastructure as workflow events)
- Cost tracking per campaign, per suite, per target
- Score trajectory data for trend visualization in dashboard
- Lineage trees for debugging optimization decisions

---

## API Surface (Sketch)

### Eval Suite Endpoints

```
POST   /optimizer/suites                  Create eval suite
GET    /optimizer/suites                  List suites (filterable by target_type, target_id)
GET    /optimizer/suites/{id}             Get suite with all cases
PUT    /optimizer/suites/{id}             Update suite (bumps version)
DELETE /optimizer/suites/{id}             Soft-delete suite
POST   /optimizer/suites/generate         LLM-generate test cases from context + seed examples
```

### Campaign Endpoints

```
POST   /optimizer/campaigns               Launch optimization campaign
GET    /optimizer/campaigns               List campaigns (filterable by suite, status)
GET    /optimizer/campaigns/{id}          Campaign status + current best score + progress
GET    /optimizer/campaigns/{id}/lineage  Full Pareto frontier history + ancestry tree
GET    /optimizer/campaigns/{id}/events   SSE stream of optimization progress
DELETE /optimizer/campaigns/{id}          Cancel running campaign
```

### Result Endpoints

```
GET    /optimizer/results                 List results (filterable by suite, target, score range)
GET    /optimizer/results/{id}            Full result: optimized context + scores + lineage
POST   /optimizer/results/{id}/apply      Deploy optimized context to target (explicit action)
GET    /optimizer/results/compare         Side-by-side comparison of two results
```

### CLI Commands (Sketch)

```bash
autobuilder optimizer generate-suite --target agent:planner --seed-examples ./golden.yaml
autobuilder optimizer create-suite ./suites/planner_draft.yaml --validated
autobuilder optimizer run --suite planner-decomposition --task-lm haiku --reflection-lm sonnet
autobuilder optimizer status {campaign_id}
autobuilder optimizer watch {campaign_id}       # SSE stream
autobuilder optimizer best --target agent:planner
autobuilder optimizer compare {result_a} {result_b}
autobuilder optimizer lineage {campaign_id}
autobuilder optimizer apply {result_id}
```

---

## Data Model (Sketch)

Four core tables: `optimizer_eval_suites`, `optimizer_eval_cases`, `optimizer_campaigns`, `optimizer_results`. Key relationships:

- **EvalSuite**: name, target_type, target_id, optimization_objective, version (auto-incremented on update), validated (human-reviewed flag). Has many EvalCases.
- **EvalCase**: eval_mode (intrinsic/extrinsic), description, weight, is_holdout (reserved for validation, not training), context_fixtures (fixed surrounding layers), input_data, chain (extrinsic hop definitions, null for intrinsic), validation (ordered deterministic validation steps with types and weights).
- **Campaign**: suite_id, seed_context, status (pending/running/completed/failed/cancelled), config (task_lm, reflection_lm, max_metric_calls), progress, cost_usd, tags. Has one OptimizedResult.
- **OptimizedResult**: best_context, best_score, seed_score, delta, pareto_frontier (full frontier snapshot), lineage_tree (full ancestry), score_trajectory, applied (boolean), applied_at.

Full schema in research docs: `.dev/.research/260412_context-optimization/02-architecture-api-data-model.md` (sections 5.1-5.4).

---

## Open Questions

| # | Question | Notes |
|---|----------|-------|
| 1 | Eval suites: database records or YAML files on disk? | Database is more queryable; YAML is more version-controllable. Could do both (YAML as source of truth, imported to DB for runtime). |
| 2 | Multi-turn context optimization? | Some agent instructions produce multi-turn conversations. Eval cases may need conversation trees. GEPA supports this via custom adapters. |
| 3 | Shared or separate ARQ worker pool? | Optimization campaigns are long-running. Separate pool prevents starving workflow workers. |
| 4 | Minimum eval suite size? | GEPA docs say 10-50 sufficient, works with as few as 3. Recommend 20-30 train + 10 holdout as baseline. |
| 5 | Extrinsic chain depth limit? | 2-hop chains are the common case. 3+ hops multiply cost and add noise. Recommend capping at 3. |
| 6 | Non-determinism in extrinsic chain intermediates? | Mitigation: low temperature on chain hops, or average scores across N chain executions per eval (increases cost but reduces variance). |
| 7 | `execute_code` validation sandbox? | Eval cases include arbitrary Python. Needs isolation. Subprocess with timeout + restricted imports is minimum. Docker or WASM sandbox is safer. Decision needed for Phase 14. |
| 8 | First real eval suite target? | Recommend Planner agent (auto-code) end-to-end: gate cases, contrastive boundary pairs, frontier cases, extrinsic chain through Coder. Validates the framework design against real friction. |
| 9 | Suite evolution automation? | `evolve_suite` generates new frontier cases and graduates solved cases. Human-approved initially, automated later. |

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| GEPA library instability (newer project) | Medium | Pin version, adapter pattern isolates GEPA internals. If GEPA breaks, swap engine behind adapter. |
| Eval suite quality determines optimization ceiling | High | Strong suite generation with human validation. Seed with golden examples. Iterate suites as understanding grows. |
| Extrinsic chain variance (non-determinism) | Medium | Low temperature on chain hops. Optional multi-execution averaging. GEPA's Pareto frontier is robust to some noise. |
| Optimization overfits to eval suite | Medium | Holdout validation set (20% of cases). Monitor generalization gap. Periodically refresh suites. |
| Cost overrun on large campaigns | Low | Budget caps via max_metric_calls. Cost tracking per campaign. Alerts at thresholds. |
| `execute_code` validation security | Medium | Sandboxed subprocess with timeout + restricted imports. Eval cases are human-validated, limiting injection risk. |
| Extrinsic eval tests wrong thing (chain failure vs. target failure) | Medium | GEPA's ASI logging captures each hop separately — reflector can distinguish target-caused vs. chain-caused failures. |

---

## Key Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| `gepa` | latest (0.1.x) | Core optimization engine |
| `litellm` | existing | LLM routing for task/reflection models |
| `sqlalchemy` | existing | Data persistence |
| `arq` | existing | Worker task execution |
| `fastapi` | existing | API endpoints |
| `typer` | existing | CLI interface |

No new infrastructure dependencies. Uses existing PostgreSQL, Redis, and LiteLLM stack.

---

## See Also

- [Workflow Eval Suite](./workflow-eval.md) — the eval framework that provides quality signals
- [Context Assembly](./context.md) — current instruction assembly architecture
- [Skills](./skills.md) — skill matching and loading
- [State & Memory](./state.md) — memory architecture
- Research corpus: [.dev/.research/260412_context-optimization/](../.research/260412_context-optimization/00-index.md) — full research with algorithm analysis, data model schemas, eval suite pseudocode, concrete examples, and 24 references
- Pre-work notes: [.dev/.todo/260413_pre-phase-14.md](../.todo/260413_pre-phase-14.md)

---

**Document Version:** 0.2 (Pre-Design Sketch, enriched with research findings)
**Last Updated:** 2026-04-12
**Status:** Phase 14 — Pre-Design
**Research Source:** `.dev/.research/260412_context-optimization/` (2026-04-12 spike)
