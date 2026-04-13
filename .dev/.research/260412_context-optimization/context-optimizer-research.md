# Context Optimizer — Design Notes

*Input document for FRD and technical specification.*
*Captured: 2026-04-12*

---

## 1. Problem Statement

AutoBuilder's agent pipelines depend on carefully crafted context (system prompts, agent instructions, skill preambles, workflow manifests) to produce quality deliverables. This context degrades or becomes suboptimal when:

1. **LLM models change** — Provider updates, new model versions, or model swaps alter how instructions are interpreted. Context optimized for Claude Sonnet 4.5 may underperform on Sonnet 4.6.
2. **New workflows are created** — Each new workflow type (auto-design, auto-research, etc.) requires context that must be tuned against measurable outcomes.
3. **Drift over time** — Accumulated changes to skills, tools, and pipeline structure can subtly degrade context effectiveness.

Manual prompt iteration is unscalable. Humans cannot run hundreds of simulation variations, track which changes produced which improvements, or systematically explore the optimization landscape.

### What We Need

An algorithmic system that:

- Accepts a context artifact + a set of quantifiable test cases
- Runs affordable, parallel simulations against any LLM
- Tracks its revision history N layers deep (lineage)
- Progressively self-improves toward maximum score / minimum delta
- Operates autonomously in the background
- Exposes a standalone API callable from CLI, web UI, or AutoBuilder internals

---

## 2. Research Summary

### 2.1 Optimization Algorithm Landscape

The prompt optimization problem is a **black-box, discrete, non-differentiable** optimization challenge. The search space is natural language — high-dimensional, combinatorial, and non-continuous.

| Family | Examples | Strengths | Weaknesses |
|--------|----------|-----------|------------|
| **Bayesian Surrogate** | DSPy MIPROv2 | Surrogate model improves proposals over time | Sample-hungry, higher cost |
| **LLM-as-Optimizer** | OPRO (DeepMind) | Simple, uses LLM to propose improvements from history | No principled exploration, requires strong optimizer model |
| **Evolutionary** | EvoPrompt | Embarrassingly parallel, population-based | Blind mutations — knows *that* something failed, not *why* |
| **Textual Gradient** | TextGrad, ProTeGi | PyTorch-like API, gradient analogy | Better for single variables, less proven on multi-component systems |
| **Reflective Evolutionary + Pareto** | **GEPA** | Reflection-based intelligent mutations, Pareto diversity, sample-efficient | Newer, smaller community (growing fast) |

### 2.2 Recommendation: GEPA (Genetic-Pareto)

**Paper**: "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning" (Agrawal et al., 2025)
**Venue**: ICLR 2026 (Oral — highest acceptance tier)
**Repo**: https://github.com/gepa-ai/gepa
**Docs**: https://gepa-ai.github.io/gepa/
**License**: MIT

#### Why GEPA

1. **Reflection over blind mutation.** GEPA's reflector LLM reads full execution traces (inputs, outputs, errors, scores) and diagnoses *why* a candidate failed — then proposes targeted textual mutations. This is the "smart" algorithm behavior required: it understands word selection, instruction ordering, emphasis, and phrasing impact.

2. **Pareto frontier = built-in lineage tracking.** Instead of evolving only the global best, GEPA maintains a frontier of candidates that each excel on different subsets of test cases. Candidates are never discarded if they're best at *something*. The frontier provides full genealogy — every candidate descends from ancestors with tracked mutation history.

3. **Sample efficient = affordable.** GEPA outperforms GRPO (RL) by 6-20% while using up to 35x fewer rollouts. Outperforms MIPROv2 by 10+ percentage points across benchmarks. Estimated cost: ~$0.90 per 150-evaluation campaign using cheap task models.

4. **Already integrated with Google ADK.** Google ADK has official agent optimization powered by GEPA. Same ecosystem as AutoBuilder.

5. **Uses LiteLLM.** Same routing layer AutoBuilder uses. Cheap models for simulation, expensive models for reflection — natively supported.

6. **Optimizes any text artifact.** The `optimize_anything` API handles prompts, code, agent architectures, configurations, and more. Not prompt-only.

7. **Production-proven.** In use at Shopify, Databricks, Dropbox, OpenAI, Pydantic, MLflow, Comet ML, and 50+ organizations.

#### GEPA Core Algorithm

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

- **Reflective Mutation**: Sample one candidate → execute → reflect on traces → propose improvement. Focused, directed improvement.
- **System-Aware Merge**: Sample two frontier candidates → combine modules based on evolution history. Creates hybrids with complementary strengths.

**Pareto Selection**: A candidate stays on the frontier if it achieves the highest score on *at least one* evaluation instance. Strictly dominated candidates are pruned. Selection probability is proportional to coverage (number of instances where candidate is best). This prevents local optima and preserves diverse strategies.

#### Key GEPA Concepts

- **Actionable Side Information (ASI)**: Rich textual feedback logged during evaluation — not just scores. Error messages, structural mismatches, reasoning traces, constraint violations. This is what makes GEPA's mutations targeted rather than random.
- **Pareto Frontier**: The set of non-dominated candidates. Maintains diversity, prevents premature convergence.
- **Reflective Meta-Prompting**: The reflection model receives: current instructions, execution traces, ASI, and scores. It outputs a diagnosis + proposed instruction modification.
- **Candidate Lineage**: Full ancestry tree tracking which candidate descended from which, what mutations were applied, and score deltas at each step.

#### GEPA vs. Alternatives (Decision Rationale)

- **vs. MIPROv2**: GEPA outperforms by 10+ percentage points across benchmarks. MIPROv2 uses Bayesian optimization which is more sample-hungry. GEPA's reflection provides richer learning signal than score-only surrogate models.
- **vs. OPRO**: OPRO requires strong optimizer models and has no principled exploration strategy. GEPA's Pareto selection is strictly more robust for avoiding local optima.
- **vs. EvoPrompt**: EvoPrompt's mutations are blind (GA/DE crossover). GEPA's reflection-based mutations are informed by *why* things failed, not just *that* they failed.
- **vs. TextGrad**: TextGrad works well for single variables but is less proven on multi-component systems. GEPA handles multi-module optimization natively.
- **vs. Custom build**: GEPA already does everything required — evolutionary search, lineage tracking, Pareto frontiers, reflection-based mutations, budget management, LiteLLM integration, ADK integration. Building custom would take weeks and produce something strictly worse.

### 2.3 DSPy Integration Path

GEPA is available as `dspy.GEPA` within the DSPy framework. For AutoBuilder, we use the standalone `gepa` package directly via `optimize_anything` — no DSPy dependency required. The standalone API is cleaner for our use case (optimizing raw context strings, not DSPy program modules).

```python
import gepa
from gepa.optimize_anything import optimize_anything, GEPAConfig, EngineConfig
```

---

## 3. Architecture

### 3.1 Design Principles

1. **Standalone API** — The optimizer is a self-contained service callable from CLI, web UI, or programmatically by AutoBuilder. It has no coupling to ADK, agents, or workflow internals.

2. **Isolated evaluation** — Test cases are micro-tests: send context + input to an LLM, score the output. No pipeline execution, no agent orchestration. Minimum effective experiment size.

3. **Eval suites are reusable assets** — Once a suite is human-validated for a target, it's run repeatedly across model changes, drift checks, and re-optimization campaigns. The human approves the *goal*; the machine optimizes toward it.

4. **LLM-generated test suites** — A strong model (Claude Sonnet/Opus) ingests the full context of the optimization target (agent instructions, skills, workflow manifest, example specs) and generates comprehensive test cases. Human role is approval, not authorship.

5. **Results are versioned and explicit** — Optimized contexts don't auto-deploy. Human reviews delta, approves, then explicitly applies. Automation of the apply step is a future option.

### 3.2 Evaluation Modes: Intrinsic vs. Extrinsic

The optimizer supports two evaluation modes. Every eval case declares which mode it uses.

**Intrinsic evaluation** tests the target component's output directly. One LLM call, deterministic validation on the result. Use when the component produces a final, independently verifiable artifact.

- Coder agent instructions → produces code → compile + run tests
- Formatter agent instructions → produces formatted output → schema validation
- Any agent whose output IS the deliverable

**Extrinsic evaluation** tests the target component's output by its downstream impact. Multiple LLM calls in a causal chain — the optimized component's output becomes input context for subsequent fixed components, and validation happens at the end of the chain. Use when the component produces *intermediate context* consumed by other agents.

- Planner instructions → produces plan → feed to Coder (fixed) → compile + run tests
- Decomposer instructions → produces deliverable list → feed to Planner (fixed) → produces plans → structural validation
- Reviewer instructions → produces review feedback → feed to Coder (fixed) → produces revised code → diff quality check

The key constraint: **only one component in the chain is the optimization target** (the free variable). All other chain participants use fixed instructions. GEPA mutates the target; the chain measures downstream impact.

```
INTRINSIC (single-hop):

  ┌─────────────────┐       ┌────────────────┐
  │ Target context   │──LLM──│ Output         │──▶ Deterministic validation
  │ (GEPA mutates)   │       │                │
  └─────────────────┘       └────────────────┘

EXTRINSIC (multi-hop):

  ┌─────────────────┐       ┌────────────┐       ┌──────────────┐       ┌────────────────┐
  │ Target context   │──LLM──│ Intermediate│──────│ Fixed agent  │──LLM──│ Final output   │──▶ Deterministic
  │ (GEPA mutates)   │       │ output      │      │ (not mutated)│       │                │    validation
  └─────────────────┘       └────────────┘       └──────────────┘       └────────────────┘
                                                          │
                                                  (can be multiple hops)
```

**Cost implications**: Extrinsic cases cost more per evaluation (N LLM calls per hop in the chain). Suites should mix both modes — use intrinsic cases for fast, cheap signal on obvious quality dimensions, and extrinsic cases for the high-value decision-quality tests that only reveal themselves downstream. A typical ratio might be 60% intrinsic / 40% extrinsic.

**ASI richness**: Extrinsic evaluation produces richer Actionable Side Information for GEPA's reflector because the full chain trace is logged — the reflector can see not just that the final output failed, but *where* in the chain the quality degraded. This enables more targeted mutations.

### 3.3 System Context

```
                    ┌──────────────┐
                    │   CLI        │
                    │  (typer)     │
                    └──────┬───────┘
                           │
                           ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐
│  Dashboard   │──▶│   Gateway    │──▶│   Optimizer Worker    │
│  (React SPA) │   │  (FastAPI)   │   │   (ARQ + GEPA)       │
└──────────────┘   └──────────────┘   └──────────┬───────────┘
                                                  │
                                        ┌─────────┴──────────┐
                                        ▼                    ▼
                                  ┌───────────┐      ┌────────────┐
                                  │ Task LLM  │      │ Reflection │
                                  │ (cheap)   │      │ LLM (smart)│
                                  │ Haiku /   │      │ Sonnet /   │
                                  │ 4o-mini   │      │ Opus       │
                                  └───────────┘      └────────────┘
```

### 3.4 Component Overview

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
│  ┌────────────────┐   ┌──────▼─────────┐                    │
│  │ Eval Suite      │   │ GEPA Engine    │                    │
│  │ Registry        │   │ (optimize_     │                    │
│  │ (versioned      │   │  anything)     │                    │
│  │  test cases)    │   └───────┬────────┘                    │
│  └────────────────┘           │                              │
│                        ┌──────▼─────────┐                    │
│  ┌────────────────┐   │ AutoBuilder    │                    │
│  │ Result Store    │◀──│ Adapter        │                    │
│  │ (versioned      │   │ (evaluate +   │                    │
│  │  contexts +     │   │  trace + ASI) │                    │
│  │  lineage)       │   └───────────────┘                    │
│  └────────────────┘                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. API Design

### 4.1 Eval Suite Endpoints

```
POST   /optimizer/suites                  Create eval suite (from manual or generated input)
GET    /optimizer/suites                  List all suites (filterable by target_type, target_id)
GET    /optimizer/suites/{id}             Get suite with all cases
PUT    /optimizer/suites/{id}             Update suite (bumps version)
DELETE /optimizer/suites/{id}             Soft-delete suite

POST   /optimizer/suites/generate         LLM-generate test cases from context + seed examples
```

#### Suite Generation Payload

```json
{
    "target_context": "Full agent instructions being optimized...",
    "workflow_manifest": "WORKFLOW.yaml contents for structural context...",
    "relevant_skills": ["skill_a.md contents...", "skill_b.md contents..."],
    "example_specs": ["Real spec 1...", "Real spec 2..."],
    "example_outputs": ["Expected output 1...", "Expected output 2..."],
    "generation_model": "claude-sonnet",
    "num_cases": 30,
    "focus_areas": ["edge cases", "ambiguous inputs", "error recovery", "constraint adherence"]
}
```

Returns a draft suite for human review and approval.

### 4.2 Campaign Endpoints

```
POST   /optimizer/campaigns               Launch optimization campaign
GET    /optimizer/campaigns               List campaigns (filterable by suite, status)
GET    /optimizer/campaigns/{id}          Campaign status + current best score + progress
GET    /optimizer/campaigns/{id}/lineage  Full Pareto frontier history + ancestry tree
GET    /optimizer/campaigns/{id}/events   SSE stream of optimization progress
DELETE /optimizer/campaigns/{id}          Cancel running campaign
```

#### Campaign Launch Payload

```json
{
    "suite_id": "uuid",
    "seed_context": "Starting agent instructions...",
    "config": {
        "task_lm": "haiku",
        "reflection_lm": "sonnet",
        "max_metric_calls": 200,
        "batch_size": 5
    },
    "tags": ["model-migration", "v4.6-upgrade"]
}
```

### 4.3 Result Endpoints

```
GET    /optimizer/results                 List results (filterable by suite, target, score range)
GET    /optimizer/results/{id}            Full result: optimized context + scores + lineage
POST   /optimizer/results/{id}/apply      Deploy optimized context to target (explicit action)
GET    /optimizer/results/compare         Side-by-side comparison of two results
```

---

## 5. Data Model

### 5.1 Eval Suite

```python
class EvalSuite(Base):
    __tablename__ = "optimizer_eval_suites"

    id: Mapped[uuid]
    name: Mapped[str]                        # "planner-agent-decomposition"
    description: Mapped[str]                 # What this suite validates
    target_type: Mapped[str]                 # "agent_instructions" | "skill" | "workflow_manifest"
    target_id: Mapped[str]                   # Identifier of the specific target
    optimization_objective: Mapped[str]      # Natural language objective for GEPA
    version: Mapped[int]                     # Auto-incremented on update
    created_by: Mapped[str]                  # "human" | "generated" | "generated+approved"
    validated: Mapped[bool]                  # Human has reviewed and approved
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    cases: Mapped[list["EvalCase"]] = relationship()
```

### 5.2 Eval Case

```python
class EvalCase(Base):
    __tablename__ = "optimizer_eval_cases"

    id: Mapped[uuid]
    suite_id: Mapped[uuid]                   # FK to EvalSuite
    eval_mode: Mapped[str]                   # "intrinsic" | "extrinsic"
    description: Mapped[str]                 # What capability/decision this case tests
    weight: Mapped[float]                    # Relative importance in composite score (default 1.0)
    is_holdout: Mapped[bool]                 # Reserved for validation, not training (default False)
    order: Mapped[int]                       # Display/execution order

    # Context assembly — the full stack the target sees in production
    context_fixtures: Mapped[dict]           # Fixed surrounding layers:
                                             #   system_instructions: str
                                             #   workflow_context: str
                                             #   relevant_skills: list[str]
                                             #   simulated_state: dict

    # Test input
    input_data: Mapped[dict]                 # The input sent to the target (spec, question, scenario)

    # Extrinsic chain definition (only for eval_mode="extrinsic")
    chain: Mapped[list[dict] | None]         # Ordered list of downstream hops:
                                             #   [
                                             #     {
                                             #       "agent_role": "coder",
                                             #       "instructions": "Fixed coder instructions...",
                                             #       "context_fixtures": { ... },
                                             #       "input_template": "{previous_output}"
                                             #     },
                                             #     {
                                             #       "agent_role": "test_runner",
                                             #       ...
                                             #     }
                                             #   ]
                                             # Each hop receives the previous hop's output.
                                             # None for intrinsic cases.

    # Validation — deterministic checks on the FINAL output (whether intrinsic or end-of-chain)
    validation: Mapped[list[dict]]           # Ordered validation steps:
                                             #   [
                                             #     {
                                             #       "type": "execute_code",
                                             #       "code": "python validation logic...",
                                             #       "required": true,
                                             #       "weight": 0.5
                                             #     },
                                             #     ...
                                             #   ]
                                             # Types: json_parse, schema, execute_code, regex,
                                             #         value_check, compile, run_tests
                                             # "required" = hard gate (score 0 on failure)
                                             # "weight" = contribution to composite score
```

### 5.3 Campaign

```python
class Campaign(Base):
    __tablename__ = "optimizer_campaigns"

    id: Mapped[uuid]
    suite_id: Mapped[uuid]                   # FK to EvalSuite
    seed_context: Mapped[str]                # Starting prompt/instructions
    status: Mapped[str]                      # "pending" | "running" | "completed" | "failed" | "cancelled"
    config: Mapped[dict]                     # GEPA config (task_lm, reflection_lm, max_metric_calls, etc.)
    tags: Mapped[list[str]]                  # Freeform tags for filtering/grouping
    progress: Mapped[dict]                   # Current iteration, best score so far, eval count
    cost_usd: Mapped[float]                  # Accumulated cost estimate
    error: Mapped[str | None]                # Error message if failed
    started_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]

    result: Mapped["OptimizedResult | None"] = relationship()
```

### 5.4 Optimized Result

```python
class OptimizedResult(Base):
    __tablename__ = "optimizer_results"

    id: Mapped[uuid]
    campaign_id: Mapped[uuid]                # FK to Campaign
    suite_id: Mapped[uuid]                   # FK to EvalSuite (denormalized for query convenience)
    target_type: Mapped[str]                 # Denormalized from suite
    target_id: Mapped[str]                   # Denormalized from suite
    best_context: Mapped[str]                # The optimized context
    best_score: Mapped[float]                # Best composite score achieved
    seed_score: Mapped[float]                # Score of the original seed context
    delta: Mapped[float]                     # best_score - seed_score
    pareto_frontier: Mapped[dict]            # Full frontier snapshot (candidates + per-case scores)
    lineage_tree: Mapped[dict]               # Full ancestry (parent → child → mutation → score)
    score_trajectory: Mapped[list[dict]]     # Score over iterations [{iteration, best_score, avg_score}]
    metadata: Mapped[dict]                   # Token usage, model versions, timing
    applied: Mapped[bool]                    # Whether deployed to target
    applied_at: Mapped[datetime | None]
    created_at: Mapped[datetime]
```

---

## 6. Worker Implementation

### 6.1 Campaign Execution

```python
async def run_optimization_campaign(campaign_id: uuid):
    """ARQ worker task. Wraps GEPA optimize_anything."""
    campaign = await db.get_campaign(campaign_id)
    suite = await db.get_suite_with_cases(campaign.suite_id)

    train_cases = [c for c in suite.cases if not c.is_holdout]
    holdout_cases = [c for c in suite.cases if c.is_holdout]

    def evaluate(candidate: dict, example: dict) -> float:
        """Evaluate candidate context via intrinsic or extrinsic chain."""
        task_lm = campaign.config["task_lm"]

        # Step 1: Assemble full context stack and run target component
        full_context = assemble_context(
            system=example.get("context_fixtures", {}).get("system_instructions", ""),
            workflow=example.get("context_fixtures", {}).get("workflow_context", ""),
            agent_role=candidate["instructions"],   # ← GEPA mutates THIS
            skills=example.get("context_fixtures", {}).get("relevant_skills", []),
            state=example.get("context_fixtures", {}).get("simulated_state", {}),
        )

        response = litellm.completion(
            model=task_lm,
            messages=[
                {"role": "system", "content": full_context},
                {"role": "user", "content": json.dumps(example["input_data"])}
            ]
        )
        current_output = response.choices[0].message.content
        oa.log(f"Target output: {current_output}")

        # Step 2: If extrinsic, run the causal chain
        if example.get("eval_mode") == "extrinsic" and example.get("chain"):
            for i, hop in enumerate(example["chain"]):
                hop_context = assemble_context(
                    system=hop.get("context_fixtures", {}).get("system_instructions", ""),
                    workflow=hop.get("context_fixtures", {}).get("workflow_context", ""),
                    agent_role=hop["instructions"],   # Fixed — not optimized
                    skills=hop.get("context_fixtures", {}).get("relevant_skills", []),
                    state=hop.get("context_fixtures", {}).get("simulated_state", {}),
                )

                # Previous output becomes input for next hop
                hop_input = hop.get("input_template", "{previous_output}").format(
                    previous_output=current_output
                )

                hop_response = litellm.completion(
                    model=task_lm,
                    messages=[
                        {"role": "system", "content": hop_context},
                        {"role": "user", "content": hop_input}
                    ]
                )
                current_output = hop_response.choices[0].message.content
                oa.log(f"Chain hop {i+1} ({hop['agent_role']}): {current_output}")

        # Step 3: Run deterministic validation on final output
        score = run_validation_pipeline(current_output, example["validation"])
        oa.log(f"Final score: {score}")

        return score

    result = optimize_anything(
        seed_candidate={"instructions": campaign.seed_context},
        evaluator=evaluate,
        dataset=[c.to_dict() for c in train_cases],
        valset=[c.to_dict() for c in holdout_cases] if holdout_cases else None,
        objective=suite.optimization_objective,
        config=GEPAConfig(
            engine=EngineConfig(
                max_metric_calls=campaign.config.get("max_metric_calls", 200),
                task_lm=campaign.config["task_lm"],
                reflection_lm=campaign.config["reflection_lm"],
            )
        ),
    )

    await db.save_result(
        campaign_id=campaign_id,
        best_context=result.best_candidate["instructions"],
        best_score=result.best_score,
        pareto_frontier=result.pareto_frontier,
        lineage_tree=result.lineage,
        score_trajectory=result.score_trajectory,
    )
```

### 6.2 Validation Pipeline

All validation is deterministic. No LLM judge calls during scoring.

```python
def run_validation_pipeline(output: str, steps: list[dict]) -> float:
    """Run ordered validation steps against the final output.
    Steps with required=True are hard gates — any failure zeroes the score.
    Remaining steps contribute weighted scores."""
    score = 0.0
    total_weight = 0.0

    for step in steps:
        result = run_validation_step(output, step)

        if step.get("required") and not result.passed:
            oa.log(f"GATE FAILED: {step['type']} — {result.reason}")
            return 0.0

        if "weight" in step:
            score += result.score * step["weight"]
            total_weight += step["weight"]

        oa.log(f"{step['type']}: {'PASS' if result.passed else 'FAIL'} "
               f"(score: {result.score}) — {result.reason}")

    return score / total_weight if total_weight > 0 else 0.0


def run_validation_step(output: str, step: dict) -> ValidationResult:
    """Route to appropriate deterministic validation."""
    match step["type"]:
        case "json_parse":
            return validate_json_parse(output)
        case "schema":
            return validate_schema(output, step["config"])
        case "execute_code":
            return validate_execute_code(output, step["code"])
        case "compile":
            return validate_compile(output, step.get("config", {}))
        case "run_tests":
            return validate_run_tests(output, step["config"])
        case "regex":
            return validate_regex(output, step["config"])
        case "value_check":
            return validate_value_check(output, step["config"])
        case _:
            raise ValueError(f"Unknown validation type: {step['type']}")
```

**Validation types (all deterministic):**

- **json_parse** — Can the output be parsed as valid JSON? Gate check.
- **schema** — Does parsed output match a JSON schema (required fields, types, value ranges)?
- **execute_code** — Run arbitrary Python validation logic against the output. Returns `{score: float, passed: bool, reason: str}`. This is the most powerful and flexible — any programmatic check.
- **compile** — Extract code from output, compile/syntax-check it. Language-specific.
- **run_tests** — Extract code from output, run it against provided test cases, report pass/fail count.
- **regex** — Pattern matching against output (presence/absence of expected patterns).
- **value_check** — Numeric/range/threshold checks on extracted values.

### 6.3 Cost Tracking

Cost is estimated per evaluation using LiteLLM's token counting:

```python
cost_per_eval = litellm.completion_cost(response)
campaign.cost_usd += cost_per_eval
# Reflection costs tracked separately via GEPA's internal accounting
```

### 6.4 Concrete Examples

#### Example A: Intrinsic — Coder Agent (direct output verification)

Optimizing the Coder agent's instructions. Output is code. Validation: does it run?

```yaml
eval_mode: intrinsic
description: "Coder handles a function with edge cases (empty input, single element)"

context_fixtures:
  workflow_context: "auto-code workflow context..."
  relevant_skills: ["python-conventions.md", "error-handling.md"]
  simulated_state:
    language: python
    framework: fastapi

input_data:
  spec: |
    Write a function `deduplicate(items: list) -> list` that removes
    duplicates while preserving order. Must handle empty lists and
    lists with unhashable types (fall back to O(n²) comparison).

chain: null  # Intrinsic — no downstream hops

validation:
  - type: compile
    required: true                     # Gate: must be valid Python

  - type: run_tests
    required: true
    weight: 0.6
    config:
      test_code: |
        assert deduplicate([]) == []
        assert deduplicate([1, 2, 3]) == [1, 2, 3]
        assert deduplicate([1, 2, 2, 3, 1]) == [1, 2, 3]
        assert deduplicate([[1, 2], [3], [1, 2]]) == [[1, 2], [3]]
        assert deduplicate([1]) == [1]

  - type: execute_code
    weight: 0.4
    code: |
      import ast
      tree = ast.parse(output)
      funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
      has_type_hints = any(f.returns is not None for f in funcs)
      has_docstring = any(ast.get_docstring(f) for f in funcs)
      line_count = len(output.strip().splitlines())
      concise = line_count < 30

      return {
          "score": (0.4 if has_type_hints else 0.0)
                 + (0.3 if has_docstring else 0.0)
                 + (0.3 if concise else 0.0),
          "passed": True,
          "reason": f"type_hints={has_type_hints}, docstring={has_docstring}, lines={line_count}"
      }
```

#### Example B: Extrinsic — Planner Agent (downstream impact on code quality)

Optimizing the Planner agent's instructions. Planner output is a decomposition plan — but we evaluate whether that plan leads to good code when the Coder acts on it.

```yaml
eval_mode: extrinsic
description: "Planner catches hidden dependency: auth must precede protected routes"

context_fixtures:
  workflow_context: "auto-code workflow context..."
  relevant_skills: ["decomposition-patterns.md"]
  simulated_state:
    project_type: web_api
    language: python

input_data:
  spec: |
    Build a REST API with:
    - User registration and login (JWT auth)
    - Protected CRUD endpoints for blog posts
    - Public read-only endpoint for published posts

chain:
  - agent_role: coder
    instructions: "Fixed coder agent instructions..."
    context_fixtures:
      relevant_skills: ["python-conventions.md", "fastapi-patterns.md"]
    input_template: |
      Implement the following plan as a single Python FastAPI application.
      Plan:
      {previous_output}

validation:
  # Validate the FINAL output (code from the coder), not the intermediate plan
  - type: compile
    required: true

  - type: execute_code
    required: true
    weight: 0.4
    code: |
      # The key test: did the planner's decomposition lead to code where
      # auth is set up BEFORE protected routes reference it?
      import ast
      tree = ast.parse(output)

      # Find auth-related and route-related definitions
      lines = output.splitlines()
      auth_line = next((i for i, l in enumerate(lines)
                       if 'jwt' in l.lower() or 'authenticate' in l.lower()
                       or 'get_current_user' in l.lower()), None)
      protected_route_line = next((i for i, l in enumerate(lines)
                                   if 'Depends(' in l and 'current_user' in l.lower()), None)

      if auth_line is None:
          return {"score": 0.0, "passed": False, "reason": "No auth implementation found"}
      if protected_route_line is None:
          return {"score": 0.0, "passed": False, "reason": "No protected routes found"}

      auth_before_routes = auth_line < protected_route_line

      return {
          "score": 1.0 if auth_before_routes else 0.0,
          "passed": auth_before_routes,
          "reason": f"Auth at line {auth_line}, protected route at {protected_route_line}"
      }

  - type: execute_code
    weight: 0.3
    code: |
      # Check the code has proper separation of concerns
      has_models = 'class User' in output or 'class BlogPost' in output
      has_schemas = 'BaseModel' in output
      has_error_handling = 'HTTPException' in output
      public_endpoint = 'published' in output.lower()

      hits = sum([has_models, has_schemas, has_error_handling, public_endpoint])
      return {
          "score": hits / 4,
          "passed": hits >= 2,
          "reason": f"models={has_models}, schemas={has_schemas}, "
                    f"errors={has_error_handling}, public={public_endpoint}"
      }

  - type: execute_code
    weight: 0.3
    code: |
      # Did the plan lead to right-sized code? Not a 10-line stub, not a 500-line mess.
      line_count = len(output.strip().splitlines())
      in_range = 40 <= line_count <= 200
      return {
          "score": 1.0 if in_range else max(0, 1.0 - abs(line_count - 120) / 200),
          "passed": in_range,
          "reason": f"{line_count} lines (target: 40-200)"
      }
```

**Why this works**: The planner's instructions are the only free variable. If GEPA mutates the planner instructions to emphasize "identify authentication dependencies before decomposing protected resources," the downstream coder is more likely to produce code with correct auth ordering — and the `execute_code` validation catches that deterministically. GEPA's reflector sees the full chain trace (plan + code + validation result) and can pinpoint whether a failure originated in the plan or the code step.

---

## 7. Optimization Goal

The Context Optimizer exists to produce the most intelligent, disciplined agent harness possible through optimized context. "Better context" is not an abstract quality — it is measured across four concrete dimensions:

### 7.1 Evaluation Dimensions

**1. Intelligence** — The agent makes smart decisions. Catches non-obvious dependencies, handles ambiguity without over-committing, decomposes at the right granularity, doesn't over-engineer or under-engineer. Tests for this dimension use contrastive boundary pairs and ambiguous specifications that require genuine reasoning.

**2. Compliance** — The agent follows the rules encoded in its context. If the instructions say "always validate before committing" or "use SequentialAgent not custom loops," the model does that. Not sometimes — always. Tests for this dimension encode specific behavioral rules and verify strict adherence.

**3. Tool Discipline** — The agent calls the right tools, with correct arguments, at the right pipeline stage. Doesn't hallucinate tool names, doesn't skip required tools, doesn't call tools unnecessarily. Tests for this dimension present scenarios where tool selection matters and validate the tool call sequence and parameters.

**4. Deliverable Quality** — The final output actually solves the request. Code runs, plans are actionable, decompositions are implementable. Tests for this dimension validate the end artifact deterministically — compile, execute, schema-validate.

The eval suite needs cases that stress each dimension independently AND in combination. A model that's intelligent but ignores rules is dangerous. A model that follows rules perfectly but makes dumb decisions is useless. The optimizer finds the context sweet spot where all four dimensions are maximized simultaneously.

GEPA's Pareto frontier naturally handles multi-dimensional optimization — candidates that excel on compliance but sacrifice intelligence are preserved alongside candidates that are brilliant but sloppy. GEPA's merge operation combines their strengths into candidates that balance all dimensions.

---

## 8. Eval Suite Design Patterns

Three eval suite design patterns, synthesized from current research (GUIDE/AAAI 2026, Item Response Theory/Fluid Benchmarking, EvolveCoder adversarial-discriminative cycling, Anthropic's capability/regression eval methodology). These target maximum improvement and narrow simulation deltas.

### 8.1 Pattern 1: Contrastive Boundary Pairs

**Source**: GUIDE framework (Grading Using Iteratively Designed Exemplars). Core insight: effective evaluation requires examples that act as counterpoints rather than just representatives — contrastive pairs that appear semantically similar but require fundamentally different decisions.

**Applied to AutoBuilder**: Instead of testing "can the planner decompose this spec," test "can the planner distinguish between two specs that *look* similar but require fundamentally different decompositions?"

```yaml
# PAIR A: Looks like it needs auth, actually doesn't
- input: "Build an API that returns public weather data from a third-party service"
  trap: "third-party service" sounds like auth, but it's public data
  correct_decision: No auth deliverable. Simple proxy/cache pattern.

# PAIR B: Looks simple, actually needs auth
- input: "Build an API that returns weather data from our internal service"
  trap: "weather data" sounds simple, but "internal service" implies service-to-service auth
  correct_decision: Must include service auth/API key management deliverable.
```

Validation checks: did the optimizer produce context that makes the model get BOTH cases right? Getting one right is easy. Getting the boundary pair right requires the instructions to encode the *reasoning principle*, not just a pattern match.

**Why this maximizes improvement**: Most eval suites waste cases on things the model already gets right. Boundary pairs concentrate all signal at the decision frontier — the exact place where instruction quality matters most. GEPA converges faster because every eval provides maximum information.

**Applicable dimensions**: Primarily Intelligence (decision quality), but can be designed for Compliance (rules that apply in similar-but-different situations) and Tool Discipline (tools that are correct in one scenario but wrong in a near-identical one).

### 8.2 Pattern 2: Adaptive Difficulty Calibration (IRT-Inspired)

**Source**: Item Response Theory and Fluid Benchmarking research. Core insight: the value of an evaluation sample depends on the model's current capability level. Easy cases every model passes are wasted evaluations. Impossible cases no model passes are also wasted. The informative cases are at the model's current capability boundary.

**Applied to AutoBuilder**: Tier eval cases by difficulty so optimization pressure always targets the highest-value frontier.

```yaml
suite:
  tiers:
    - name: gate
      difficulty: trivial
      purpose: Sanity check. Format compliance, basic tool calling.
        If these fail, something is fundamentally broken.
      count: 3-5
      scoring: required (hard gate, score = 0 on failure)
      dimensions: [compliance, tool_discipline]

    - name: core
      difficulty: moderate
      purpose: Baseline capability. Standard decomposition patterns,
        known-good tool sequences, rule adherence under normal conditions.
        Most models get 60-80% of these.
      count: 10-15
      scoring: weighted (bulk of the score signal)
      dimensions: [intelligence, compliance, deliverable_quality]

    - name: frontier
      difficulty: hard
      purpose: Decision quality under ambiguity, constraint conflicts,
        novel combinations, implicit dependencies. Current models get 20-40%.
      count: 8-12
      scoring: weighted (rewards excellence)
      dimensions: [intelligence, tool_discipline]

    - name: stretch
      difficulty: near-impossible
      purpose: Aspirational. Multi-step reasoning chains, conflicting
        requirements that demand creative resolution. Tests the ceiling.
      count: 3-5
      scoring: low weight (doesn't dominate, rewards breakthroughs)
      dimensions: [intelligence]
```

GEPA's Pareto frontier naturally exploits tiering — some candidates excel at core cases, others at frontier. The frontier diversity prevents premature convergence on "good enough for easy stuff."

**Why this narrows simulation deltas**: Early iterations make big jumps on core cases (high-value, achievable improvements). Later iterations shift signal toward frontier cases where diminishing returns are more gradual. The convergence curve is smoother and the final delta is tighter because evaluations aren't wasted on cases that are already solved or unsolvable.

### 8.3 Pattern 3: Adversarial-Discriminative Cycling

**Source**: Synthesized from EvolveCoder (adversarial + discriminative test generation) and Anthropic's capability/regression eval methodology. Core insight: a static eval suite has a ceiling. Once the optimizer "solves" all cases, further runs produce zero signal. The suite itself needs to evolve between campaigns.

**Applied to AutoBuilder**: Two-phase cycle that prevents suite saturation.

**Phase A — Adversarial Discovery**: Before each optimization campaign, run the current best context against a broad challenge set. Identify the cases where it fails or scores lowest. These become the "attack surface."

**Phase B — Discriminative Sharpening**: From those failures, construct minimal pairs that isolate the specific weakness. If the planner fails on specs with implicit ordering constraints, create 3-4 cases that each test a different flavor of implicit ordering.

```python
def evolve_suite(current_context: str, base_suite: EvalSuite) -> EvalSuite:
    # Step 1: Run current context against broad challenge set
    results = evaluate_all(current_context, base_suite.cases)

    # Step 2: Identify failure clusters
    failures = [r for r in results if r.score < 0.5]
    failure_patterns = cluster_by_failure_reason(failures)

    # Step 3: For each failure pattern, generate discriminative cases
    new_cases = []
    for pattern in failure_patterns:
        pairs = generate_discriminative_pairs(
            failure_pattern=pattern,
            current_context=current_context,
            num_pairs=3
        )
        new_cases.extend(pairs)

    # Step 4: Graduate solved cases to regression tier
    solved = [r for r in results if r.score > 0.95]
    for case in solved:
        case.weight = 0.1   # Still checked, doesn't dominate score
        case.tier = "regression"

    return base_suite.with_additions(new_cases)
```

The regression tier is critical — solved cases still run on every evaluation at low weight. If a mutation improves frontier performance but regresses on previously-solved cases, the Pareto frontier catches it. Prevents "fixing one thing, breaking another."

**Why this produces maximum improvement**: The suite never saturates. As GEPA solves cases, new harder cases replace them at the frontier. Optimization pressure continuously targets the weakest point of the current best candidate.

### 8.4 The Hybrid: Recommended Suite Structure

Combine all three patterns into a single suite:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Eval Suite Structure                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  GATE TIER (3-5 cases)                                          │
│  Hard gates from Pattern 2. Format, schema, basic compliance.    │
│  Score = 0 on any failure. Dimensions: compliance, tool_discipline│
│                                                                  │
│  CORE TIER (10-15 cases)                                        │
│  Contrastive boundary pairs from Pattern 1. High discriminative  │
│  power per case. Dimensions: intelligence, compliance            │
│                                                                  │
│  FRONTIER TIER (8-12 cases)                                     │
│  Adversarial-discriminative cases from Pattern 3. Evolve between │
│  campaigns. Dimensions: intelligence, tool_discipline            │
│                                                                  │
│  REGRESSION TIER (graduated cases)                               │
│  Low-weight, previously-solved cases that prevent backsliding.   │
│  Grows over time as cases are "solved." All dimensions.          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Total: 25-35 active cases per campaign                          │
│  Small enough to be cheap. Discriminative enough for real signal.│
│  Adaptive enough to never plateau.                               │
└─────────────────────────────────────────────────────────────────┘
```

**Contrastive pairs** maximize information per evaluation (GEPA runs fewer wasted evals).
**Tiered difficulty** calibrates where optimization pressure lands.
**Adversarial cycling** prevents suite saturation across campaigns.

### 8.5 Hybrid Suite — Implementation Pseudocode

```python
# ── THE HYBRID EVAL SUITE ──

class HybridEvalSuite:
    gate_cases: list[EvalCase]       # 3-5 cases, required=True
    core_cases: list[EvalCase]       # 10-15 contrastive boundary pairs
    frontier_cases: list[EvalCase]   # 8-12 adversarial-discriminative
    regression_cases: list[EvalCase] # Grows over time, weight=0.1


def evaluate_candidate(candidate: str, suite: HybridEvalSuite, example: dict) -> float:
    """Single evaluation within a GEPA campaign."""

    # ── Step 1: Run the LLM (intrinsic or extrinsic chain) ──
    output = run_chain(candidate, example)

    # ── Step 2: Gate tier — hard pass/fail ──
    for gate in suite.gate_cases:
        if not gate.validate(output):
            oa.log(f"GATE FAILED: {gate.description} — {gate.failure_reason}")
            return 0.0  # Dead. No partial credit.

    # ── Step 3: Core tier — contrastive boundary pairs ──
    # Each pair tests a reasoning principle, not a pattern.
    # BOTH sides of the pair must score well for full credit.
    core_score = 0.0
    for case in suite.core_cases:
        result = case.validate(output)
        core_score += result.score * case.weight
        oa.log(f"CORE [{case.dimension}] {case.description}: {result.score} — {result.reason}")

    # ── Step 4: Frontier tier — hardest active cases ──
    frontier_score = 0.0
    for case in suite.frontier_cases:
        result = case.validate(output)
        frontier_score += result.score * case.weight
        oa.log(f"FRONTIER [{case.dimension}] {case.description}: {result.score} — {result.reason}")

    # ── Step 5: Regression tier — don't break what works ──
    regression_score = 0.0
    for case in suite.regression_cases:
        result = case.validate(output)
        regression_score += result.score * 0.1  # Low weight, but nonzero
        if not result.passed:
            oa.log(f"REGRESSION FAILURE: {case.description}")  # Loud signal to reflector

    return core_score + frontier_score + regression_score


# ── SUITE EVOLUTION (between campaigns) ──

def evolve_suite(best_context: str, suite: HybridEvalSuite) -> HybridEvalSuite:
    """Run after each campaign completes. Prepares suite for next campaign."""

    # 1. Evaluate current best against everything
    results = evaluate_all(best_context, suite.all_cases())

    # 2. Graduate solved core cases → regression
    for case, result in zip(suite.core_cases, results.core):
        if result.score > 0.95:  # Consistently solved
            case.weight = 0.1
            suite.regression_cases.append(case)
            suite.core_cases.remove(case)

    # 3. Find what's still failing
    failures = [(c, r) for c, r in zip(suite.frontier_cases, results.frontier)
                if r.score < 0.5]
    failure_clusters = cluster_by_asi(failures)  # Group by failure reason from ASI logs

    # 4. Generate new frontier cases targeting each failure cluster
    for cluster in failure_clusters:
        new_cases = generate_discriminative_pairs(
            failure_pattern=cluster.common_reason,
            current_context=best_context,
            dimensions=cluster.affected_dimensions,
            num_pairs=3,
            model="claude-sonnet"
        )
        suite.frontier_cases.extend(new_cases)

    # 5. Rebalance: keep frontier at 8-12 cases
    #    Drop lowest-information frontier cases if over budget
    if len(suite.frontier_cases) > 12:
        suite.frontier_cases = rank_by_discriminative_power(
            suite.frontier_cases, top_k=12
        )

    return suite


# ── CONTRASTIVE PAIR GENERATION ──

def generate_contrastive_pair(
    target_principle: str,
    dimension: str,
) -> tuple[EvalCase, EvalCase]:
    """Generate two cases that look similar but require different decisions.
    The pair tests whether the context encodes a PRINCIPLE, not a pattern.

    Case A: surface cues SUGGEST the principle applies, but it doesn't.
    Case B: NO surface cues, but the principle DOES apply.
    Getting BOTH right = understands the principle.
    Getting only one right = pattern matching on keywords.
    """

    prompt = f"""
    Generate a contrastive eval pair for an agent that decomposes specifications.
    Target principle: {target_principle}
    Evaluation dimension: {dimension}

    Case A should have surface cues that SUGGEST the principle applies, but it doesn't.
    Case B should have NO surface cues, but the principle DOES apply.

    For each case, provide:
    - input: the specification text
    - trap: what makes this deceptive
    - correct_decision: what the agent should do
    - validation_code: Python that deterministically checks the decision
    """

    return llm_generate(prompt, model="claude-sonnet")


# ── FULL CAMPAIGN LIFECYCLE ──

def run_full_lifecycle(target: str, seed_context: str):
    """End-to-end: generate suite → optimize → evolve → repeat."""

    # 1. Generate initial suite (one-time, human approves)
    suite = generate_initial_suite(
        target_context=seed_context,
        num_gate=4,
        num_core_pairs=12,    # 6 contrastive pairs = 12 cases
        num_frontier=10,
        dimensions=[
            "intelligence",
            "compliance",
            "tool_discipline",
            "deliverable_quality",
        ],
    )
    suite = human_review_and_approve(suite)

    # 2. Run optimization campaign
    result = run_gepa_campaign(
        suite=suite,
        seed_context=seed_context,
        task_lm="haiku",
        reflection_lm="sonnet",
        max_metric_calls=200,
    )

    # 3. Human reviews result
    if human_approves(result):
        apply_context(result.best_context, target)

    # 4. Evolve suite for next campaign
    #    (triggered by model change, drift detection, or schedule)
    suite = evolve_suite(result.best_context, suite)

    # 5. Next campaign uses evolved suite.
    #    Gate and regression persist.
    #    Core may have graduated some cases to regression.
    #    Frontier has new cases targeting newly-discovered weaknesses.
    #    Repeat from step 2.
```

**Key dynamics in the pseudocode:**

- **Gates kill early.** If basic compliance fails, GEPA doesn't waste reflection budget analyzing *why* a frontier case scored poorly when the real problem is broken formatting. The reflector sees "GATE FAILED" and knows to fix fundamentals first.

- **Core pairs force principled learning.** Because both sides of a contrastive pair must score well, GEPA can't "cheat" by adding a keyword that helps one case but hurts its twin. The reflector must propose instruction changes that encode the *reasoning principle*, not a surface heuristic.

- **Frontier targets the current weakest point.** After each campaign, the evolution step clusters failures by their ASI-logged reasons, then generates new cases that isolate those specific weaknesses. The optimizer never runs out of signal.

- **Regression prevents catastrophic forgetting.** Solved cases drop to low weight but never disappear. If a mutation improves frontier scores but breaks a previously-solved case, the Pareto frontier catches the tradeoff and preserves both variants for merge.

---

## 9. Eval Suite Generation

### 9.1 Generation Flow

```
Human provides:
  - Target context (agent instructions, skill, manifest)
  - Workflow context (manifest, related skills)
  - 5-10 seed examples (golden input/output pairs)
  - Optional: focus areas ("edge cases", "ambiguity", "error recovery")

Strong model (Claude Sonnet/Opus) receives:
  - Full target context
  - Workflow structural context
  - Seed examples as calibration anchors
  - Instructions to generate N test cases covering:
    - Core capability validation
    - Edge cases and boundary conditions
    - Ambiguous inputs requiring judgment
    - Error/constraint handling
    - Format/structure compliance
    - Behavioral nuance (tone, verbosity, specificity)

Output:
  - Draft EvalSuite with N EvalCases
  - Each case has: input, expected output, metric type, description
  - Holdout split recommended (80/20 train/validation)

Human reviews:
  - Approves, tweaks, or rejects cases
  - Marks suite as validated
  - Suite is now a permanent reusable asset
```

### 9.2 Generation Model Selection

Use a **different model family** for test generation than the task model being optimized. If optimizing context for Haiku, generate tests with Sonnet/Opus. This prevents shared blind spots where the generator and evaluator converge on what they *think* is good rather than what actually is.

### 9.3 Generation Endpoint

The generation endpoint can be called:

- **Via CLI**: `autobuilder optimizer generate-suite --target agent:planner --seed-examples ./golden.yaml`
- **Via API**: `POST /optimizer/suites/generate` (payload described in §4.1)
- **Via Claude Code headless**: Batch job that produces the suite artifact for async review
- **Via AutoBuilder agent**: A future agent that triggers suite generation as part of workflow creation

---

## 10. CLI Interface

```bash
# ── Suite Management ──

# Generate eval suite from seed examples + context
autobuilder optimizer generate-suite \
  --target agent:planner \
  --seed-examples ./tests/planner_golden.yaml \
  --context ./contexts/planner_instructions.md \
  --workflow ./workflows/auto-code/WORKFLOW.yaml \
  --num-cases 30 \
  --model claude-sonnet \
  --output ./suites/planner_draft.yaml

# Review generated suite (opens in editor or prints to stdout)
autobuilder optimizer review-suite ./suites/planner_draft.yaml

# Import and validate suite
autobuilder optimizer create-suite ./suites/planner_draft.yaml --validated

# List suites
autobuilder optimizer list-suites

# ── Campaign Execution ──

# Run optimization campaign
autobuilder optimizer run \
  --suite planner-decomposition \
  --seed-context ./contexts/planner_v2.md \
  --task-lm haiku \
  --reflection-lm sonnet \
  --budget 200 \
  --tags model-migration,v4.6

# Check campaign status
autobuilder optimizer status {campaign_id}

# Stream live progress
autobuilder optimizer watch {campaign_id}

# Cancel running campaign
autobuilder optimizer cancel {campaign_id}

# ── Results ──

# View best result for a target
autobuilder optimizer best --target agent:planner

# Compare two results side-by-side
autobuilder optimizer compare {result_a} {result_b}

# View Pareto frontier and lineage
autobuilder optimizer lineage {campaign_id}

# Deploy optimized context
autobuilder optimizer apply {result_id}

# View score trajectory (convergence curve)
autobuilder optimizer trajectory {campaign_id}
```

---

## 11. Codebase Location

```
app/
  optimizer/
    __init__.py
    api.py                   # FastAPI router (mounted on gateway at /optimizer/*)
    schemas.py               # Pydantic request/response models
    models.py                # SQLAlchemy ORM models (EvalSuite, EvalCase, Campaign, Result)
    worker.py                # ARQ task: campaign execution (GEPA wrapper)
    adapter.py               # AutoBuilder GEPA adapter (evaluate + trace + ASI)
    scoring.py               # Metric implementations (exact_match, structural, llm_judge, composite)
    generator.py             # LLM-based eval suite generation
    cli.py                   # Typer commands (mounted on main CLI)
```

Follows existing patterns:
- Gateway exposes high-level REST endpoints
- Worker executes via ARQ (same queue infrastructure as workflow execution)
- Database models use existing SQLAlchemy engine + Alembic migrations
- CLI uses existing typer infrastructure
- LLM calls go through existing LiteLLM router

---

## 12. Cost Model

### Two-Tier LLM Strategy

| Role | Model | Cost per call | Purpose |
|------|-------|--------------|---------|
| Task (simulation) | Haiku / GPT-4o-mini | ~$0.001 | Run candidate context against test cases |
| Reflection (mutation) | Sonnet / GPT-4o | ~$0.01 | Analyze traces, diagnose failures, propose mutations |
| Judge (scoring) | Sonnet / GPT-4o | ~$0.005 | Score outputs when using llm_judge metric |
| Generation (suites) | Sonnet / Opus | ~$0.05 | One-time: generate test cases from context |

### Per-Campaign Cost Estimates

Costs vary by eval mode mix. Extrinsic cases cost N× per hop in the chain.

| Budget | Suite Mix | Task Cost | Reflection Cost | Total | Use Case |
|--------|-----------|-----------|-----------------|-------|----------|
| 150 | 100% intrinsic (1 call/eval) | $0.15 | $0.75 | ~$0.90 | Single-agent optimization |
| 150 | 60/40 intrinsic/extrinsic (avg 1.8 calls/eval) | $0.27 | $0.75 | ~$1.00 | Typical mixed suite |
| 150 | 100% extrinsic, 2-hop chain | $0.30 | $0.75 | ~$1.05 | Upstream agent optimization |
| 300 | 60/40 mixed | $0.54 | $1.50 | ~$2.00 | Deep optimization |
| 500 | 60/40 mixed | $0.90 | $2.50 | ~$3.40 | Exhaustive search |

Suite generation is a one-time cost of ~$0.50-$2.00 depending on complexity.

---

## 13. Integration Points

### 13.1 Triggered by AutoBuilder

Future: AutoBuilder can programmatically trigger optimization campaigns:

- **On model change**: When the LLM router config updates to a new model, trigger re-optimization of all agent contexts against that model.
- **On workflow creation**: When a new workflow is registered, trigger suite generation + optimization for its agent roles.
- **On drift detection**: Periodic re-evaluation of current contexts; if scores drop below threshold, trigger re-optimization.

### 13.2 Results Applied to AutoBuilder

The `apply` action writes the optimized context back to the target:

- **Agent instructions**: Updates the agent's instruction template in the database or skill files.
- **Skill content**: Updates skill file content.
- **Workflow manifest**: Updates WORKFLOW.yaml configuration.

The exact mechanism depends on where the target context is stored (database vs. filesystem). The apply endpoint handles routing.

### 13.3 Observability

- Campaign progress streamed via SSE (same Redis Streams infrastructure as workflow events)
- Cost tracking per campaign, per suite, per target
- Score trajectory data for trend visualization in dashboard
- Lineage trees for debugging optimization decisions

---

## 14. Phase Placement

### Phase 2 (Target)

- `app/optimizer/` module structure
- Database models + migrations
- GEPA integration via `optimize_anything`
- Core scoring functions (exact_match, structural)
- Campaign execution worker
- Basic CLI commands (run, status, results)
- Basic API endpoints

### Phase 3 (Enhancement)

- LLM judge scoring
- Suite generation endpoint
- Dashboard integration (campaign progress, score trajectories, lineage visualization)
- Automated campaign triggers (model change, drift detection)
- Composite scoring with configurable weights

### Future

- Multi-target campaigns (optimize multiple agent contexts simultaneously)
- A/B deployment (run both old and new context, compare live performance)
- Cross-workflow optimization (shared infrastructure context)
- Self-optimizing optimizer (use GEPA to optimize its own reflection prompts)

---

## 15. Open Questions

| # | Question | Notes |
|---|----------|-------|
| 1 | Should eval suites be stored as database records or YAML files on disk? | Database is more queryable; YAML is more version-controllable. Could do both (YAML as source of truth, imported to DB for runtime). |
| 2 | How to handle multi-turn context optimization? | Some agent instructions produce multi-turn conversations. Eval cases may need conversation trees, not single input/output pairs. GEPA supports this via custom adapters. |
| 3 | Should the optimizer share the same ARQ worker pool as workflow execution, or have its own? | Optimization campaigns are long-running and compute-bound. Separate pool prevents starving workflow workers. |
| 4 | What's the minimum eval suite size for reliable optimization? | GEPA docs say 10-50 examples is sufficient, works with as few as 3. Recommend 20-30 train + 10 holdout as a reasonable baseline per target. |
| 5 | What's the right intrinsic/extrinsic mix per suite? | Extrinsic cases are more realistic but cost N× more per eval. Starting recommendation: 60% intrinsic / 40% extrinsic. Intrinsic cases provide fast, cheap signal; extrinsic cases catch decision-quality issues that only surface downstream. |
| 6 | Should optimized contexts be diffed against seeds? | Useful for human review — seeing exactly what changed. Standard text diff should suffice. |
| 7 | How deep can extrinsic chains go before cost becomes prohibitive? | 2-hop chains are the common case (planner→coder, decomposer→planner). 3+ hops multiply cost and add noise. Recommend capping at 3 hops max. |
| 8 | How to handle non-determinism in extrinsic chain intermediate outputs? | The coder's output (intermediate hop) varies between runs even with same plan input. Mitigation: low temperature on chain hops, or average scores across N chain executions per eval (increases cost but reduces variance). |
| 9 | Should `execute_code` validation steps run in a sandbox? | Eval cases include arbitrary Python code that runs against LLM output. Needs isolation for safety. Subprocess with timeout + restricted imports is minimum. Docker container per eval is safer but slower. WASM sandbox is a third option. Decision needed for Phase 2. |
| 10 | What's the first real eval suite target for validation? | Recommend building a concrete hybrid suite for the Planner agent (auto-code) end-to-end: gate cases, contrastive boundary pairs, frontier cases, extrinsic chain through Coder. Validates the framework design against real friction before committing to full implementation. |
| 11 | Should suite evolution between campaigns be automated or human-gated? | `evolve_suite` generates new frontier cases and graduates solved cases. Fully automated risks drifting the suite without oversight. Human-approved for Phase 2 (review new frontier cases before next campaign), automated for Phase 3. |
| 12 | Where does the optimizer live in the documentation stack? | Needs a home before implementation starts. Options: new `11-OPTIMIZER.md` in project docs, or fold into existing docs as a subsection. Roadmap entry needed as Phase 2 deliverable. |

---

## 16. Key Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| `gepa` | latest (0.1.x) | Core optimization engine |
| `litellm` | existing | LLM routing for task/reflection/judge models |
| `sqlalchemy` | existing | Data persistence |
| `arq` | existing | Worker task execution |
| `fastapi` | existing | API endpoints |
| `typer` | existing | CLI interface |

No new infrastructure dependencies. Uses existing PostgreSQL, Redis, and LiteLLM stack.

---

## 17. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| GEPA library instability (newer project) | Medium | Pin version, adapter pattern isolates GEPA internals. If GEPA breaks, swap engine behind adapter. |
| Eval suite quality determines optimization ceiling | High | Strong suite generation with human validation. Seed with golden examples. Iterate suites as understanding grows. |
| Extrinsic chain variance (non-determinism in intermediate hops) | Medium | Low temperature on chain hops. Optional multi-execution averaging. Accept some noise — GEPA's Pareto frontier is robust to it. |
| Extrinsic chain cost scaling | Low | Cap chain depth at 3 hops. Mix intrinsic/extrinsic cases. Cheap task models keep per-call cost negligible. |
| Optimization overfits to eval suite | Medium | Holdout validation set (20% of cases). Monitor generalization gap. Periodically refresh suites. |
| Cost overrun on large campaigns | Low | Budget caps via max_metric_calls. Cost tracking per campaign. Alerts at thresholds. |
| Reflection model quality affects mutation quality | Medium | Use strong reflection models (Sonnet/Opus). Different family than task model to avoid shared blind spots. |
| `execute_code` validation security (arbitrary Python in eval cases) | Medium | Sandboxed subprocess with timeout + restricted imports. Eval cases are human-validated, limiting injection risk. |
| Extrinsic eval tests wrong thing (chain failure vs. target failure) | Medium | GEPA's ASI logging captures each hop separately — reflector can distinguish target-caused vs. chain-caused failures. Good ASI design is critical. |

---

## 18. References

### Core Optimization Engine

| Ref | Source | Relevance |
|-----|--------|-----------|
| [1] | Agrawal, L.A. et al. "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning." arXiv:2507.19457, 2025. **ICLR 2026 (Oral).** https://arxiv.org/abs/2507.19457 | Primary optimization algorithm. Reflective evolutionary search with Pareto frontier. Outperforms MIPROv2 by 10+ pp, GRPO by 6-20% with 35× fewer rollouts. |
| [2] | GEPA GitHub Repository. https://github.com/gepa-ai/gepa | Implementation reference. `optimize_anything` API, adapter system, custom evaluator patterns, ASI logging. Production use at Shopify, Databricks, Dropbox, OpenAI, 50+ organizations. |
| [3] | GEPA `optimize_anything` Blog Post, Feb 2026. https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/ | Declarative API for optimizing any text artifact (prompts, code, configs). Three optimization modes: single-task search, multi-task search, generalization. |
| [4] | GEPA Documentation & Quick Start. https://gepa-ai.github.io/gepa/ | Adapter interface, Pareto tracker, cost model (~$0.90 per 150-eval campaign), configuration options. |

### Alternative Optimizers (Evaluated, Not Selected)

| Ref | Source | Relevance |
|-----|--------|-----------|
| [5] | Yang, C. et al. "Large Language Models as Optimizers" (OPRO). arXiv:2309.03409, 2023. https://arxiv.org/abs/2309.03409 | LLM-as-optimizer approach. Evaluated and rejected: no principled exploration strategy, requires strong optimizer models, outperformed by GEPA. |
| [6] | Guo, Q. et al. "EvoPrompt: Connecting LLMs with Evolutionary Algorithms Yields Powerful Prompt Optimizers." arXiv:2309.08532, 2023. https://arxiv.org/abs/2309.08532 | Evolutionary prompt optimization (GA/DE with LLM crossover). Evaluated and rejected: blind mutations without reflection, outperformed by GEPA. |
| [7] | Opsahl-Ong, K. et al. "Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs" (MIPROv2/DSPy). 2024. https://dspy.ai/api/optimizers/GEPA/overview/ | Bayesian surrogate optimization in DSPy. Evaluated and rejected: more sample-hungry, GEPA outperforms by 10+ pp across benchmarks. |
| [8] | Yuksekgonul, B. et al. "TextGrad." 2025. | Textual gradient descent for prompt optimization. Evaluated and rejected: better for single variables, less proven on multi-component systems. |
| [9] | Zehle et al. "CAPO: Cost-Aware Prompt Optimization." 2025. Referenced in promptolution survey (arXiv:2512.02840). | GA-based alternative using AutoML techniques. Noted in landscape survey. |
| [10] | promptolution framework. "A Unified, Modular Framework for Prompt Optimization." arXiv:2512.02840, 2025. https://arxiv.org/pdf/2512.02840 | Comprehensive survey comparing OPRO, EvoPrompt, CAPO, and others. Informed the algorithm landscape analysis in §2.1. |

### ADK Integration

| Ref | Source | Relevance |
|-----|--------|-----------|
| [11] | Google ADK `adk optimize` command and `GEPARootAgentPromptOptimizer`. https://adk.dev/optimize/ | ADK's built-in GEPA wrapper. Evaluated: only optimizes root agent instructions, Gemini-centric defaults, no sub-agent/skill/manifest support. Decision: use GEPA directly via `optimize_anything` for broader control. |
| [12] | ADK v1.27.0 release notes (GEPA integration). https://github.com/google/adk-docs/issues/1438 | Documents the `adk optimize` CLI command, `LocalEvalSampler`, and `GEPARootAgentPromptOptimizer` configuration options. |

### Eval Suite Design Patterns

| Ref | Source | Relevance |
|-----|--------|-----------|
| [13] | "GUIDE: Grading Using Iteratively Designed Exemplars." arXiv:2603.00465, 2026. https://arxiv.org/html/2603.00465 | Contrastive boundary pair methodology. Core insight: boundary pairs that look similar but require different decisions provide stronger learning signal than representative examples. Directly informs Pattern 1 (§8.1). |
| [14] | Cameron R. Wolfe. "The Anatomy of an LLM Benchmark" (Fluid Benchmarking / IRT). 2026. https://cameronrwolfe.substack.com/p/llm-bench | Item Response Theory applied to LLM evaluation. Dynamic difficulty selection based on model capability level. Directly informs Pattern 2 (§8.2). |
| [15] | Qi Qian et al. "Benchmark2: Systematic Evaluation of LLM Benchmarks." arXiv:2601.03986, 2026. https://arxiv.org/html/2601.03986v1 | Discriminability Score (DS) and Capability Alignment Deviation (CAD) metrics for benchmark quality. Informed eval case selection criteria and the principle of maximizing discriminative power per case. |
| [16] | "EvolveCoder: Evolving Test Cases via Adversarial Verification for Code." arXiv:2603.12698, 2026. https://arxiv.org/pdf/2603.12698 | Adversarial + discriminative test generation cycling for code evaluation. Pipeline alternates between adversarial test generation and discriminative test generation. Directly informs Pattern 3 (§8.3). |
| [17] | Anthropic. "Demystifying Evals for AI Agents." 2026. https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | Capability vs. regression eval distinction. Graduation of capability evals to regression suites. Practical methodology from Claude Code development. Directly informs Pattern 3 (§8.3) and regression tier design (§8.4). |

### Eval Methodology & Industry Practice

| Ref | Source | Relevance |
|-----|--------|-----------|
| [18] | Lemos, F. et al. "Is It Time To Treat Prompts As Code? A Multi-Use Case Study For Prompt Optimization Using DSPy." arXiv:2507.03620, 2025. https://arxiv.org/abs/2507.03620 | Empirical study of DSPy prompt optimization across five use cases. Demonstrated 46.2% → 64.0% accuracy improvement on prompt evaluation tasks. Validated the automated prompt optimization approach. |
| [19] | Pragmatic Engineer. "A Pragmatic Guide to LLM Evals for Devs." 2025. https://newsletter.pragmaticengineer.com/p/evals | Golden dataset methodology, open coding for failure discovery, flywheel of improvement pattern. Informed the eval suite generation approach (§9). |
| [20] | Braintrust. "What is Eval-Driven Development." 2026. https://www.braintrust.dev/articles/eval-driven-development | EDD methodology: define quality → encode as evals → use scores as oracle → measure every change. Regression thresholds and human review calibration. Informed the overall optimization lifecycle design. |
| [21] | OpenAI. "Eval Driven System Design — From Prototype to Production." 2025. https://developers.openai.com/cookbook/examples/partners/eval_driven_system_design/receipt_inspection | End-to-end eval-driven development cookbook. Business alignment of eval metrics, iterative improvement from production data. Informed cost-benefit framing and eval suite evolution approach. |
| [22] | Vach, M. "Speeding up a Sudoku solver with GEPA `optimize_anything`." Feb 2026. https://blog.mariusvach.com/posts/gepa-sudoku-solver | Practical walkthrough of `optimize_anything` API for non-prompt optimization (code artifacts). Demonstrates the evaluator + ASI pattern in practice. |

### Adversarial Evaluation

| Ref | Source | Relevance |
|-----|--------|-----------|
| [23] | Zhang, L. et al. "Adversarial Testing in LLMs: Insights into Decision-Making Vulnerabilities." arXiv:2505.13195, 2025. https://arxiv.org/abs/2505.13195 | Adversarial evaluation framework for stress-testing LLM decision-making. Methodology for exposing model-specific susceptibilities. Background research for adversarial-discriminative cycling pattern. |
| [24] | "Let's Measure Information Step-by-Step: LLM-Based Evaluation Beyond Vibes." arXiv:2508.05469, 2025. https://arxiv.org/html/2508.05469v1 | Information-theoretic evaluation mechanisms. Demonstrates that LLM judges fail catastrophically under adversarial conditions while bounded information measures maintain robustness. Reinforced the decision to use deterministic validation over LLM judges. |

---

*End of design notes. Ready for FRD and specification drafting.*
