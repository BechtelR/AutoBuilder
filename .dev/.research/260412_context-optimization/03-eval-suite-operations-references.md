# Context Optimizer — Eval Suite Design, Operations & References

*Split from context-optimizer-research.md (Sections 7–18)*
*Captured: 2026-04-12*

---

*[← Index](./00-index.md)*

## Contents

- [7. Optimization Goal](#7-optimization-goal)
  - [7.1 Evaluation Dimensions](#71-evaluation-dimensions)
- [8. Eval Suite Design Patterns](#8-eval-suite-design-patterns)
  - [8.1 Pattern 1: Contrastive Boundary Pairs](#81-pattern-1-contrastive-boundary-pairs)
  - [8.2 Pattern 2: Adaptive Difficulty Calibration](#82-pattern-2-adaptive-difficulty-calibration-irt-inspired)
  - [8.3 Pattern 3: Adversarial-Discriminative Cycling](#83-pattern-3-adversarial-discriminative-cycling)
  - [8.4 The Hybrid: Recommended Suite Structure](#84-the-hybrid-recommended-suite-structure)
  - [8.5 Hybrid Suite — Implementation Pseudocode](#85-hybrid-suite--implementation-pseudocode)
- [9. Eval Suite Generation](#9-eval-suite-generation)
  - [9.1 Generation Flow](#91-generation-flow)
  - [9.2 Generation Model Selection](#92-generation-model-selection)
  - [9.3 Generation Endpoint](#93-generation-endpoint)
- [10. CLI Interface](#10-cli-interface)
- [11. Codebase Location](#11-codebase-location)
- [12. Cost Model](#12-cost-model)
- [13. Integration Points](#13-integration-points)
  - [13.1 Triggered by AutoBuilder](#131-triggered-by-autobuilder)
  - [13.2 Results Applied to AutoBuilder](#132-results-applied-to-autobuilder)
  - [13.3 Observability](#133-observability)
- [14. Phase Placement](#14-phase-placement)
- [15. Open Questions](#15-open-questions)
- [16. Key Dependencies](#16-key-dependencies)
- [17. Risk Assessment](#17-risk-assessment)
- [18. References](#18-references)

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
- **Via API**: `POST /optimizer/suites/generate` (payload described in §4.1 of the Architecture doc)
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
