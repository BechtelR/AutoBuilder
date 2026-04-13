# ── THE HYBRID EVAL SUITE ──

```python

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
```

# ── SUITE EVOLUTION (between campaigns) ──

```python

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
```

# ── CONTRASTIVE PAIR GENERATION (the core innovation) ──

```python

def generate_contrastive_pair(target_principle: str, dimension: str) -> tuple[EvalCase, EvalCase]:
    """Generate two cases that look similar but require different decisions.
    The pair tests whether the context encodes a PRINCIPLE, not a pattern."""

    # Example for dimension=intelligence, principle="implicit dependencies"
    # Case A: surface cue suggests dependency, but there isn't one
    # Case B: no surface cue, but there IS a dependency
    # Getting BOTH right = understands the principle
    # Getting only one right = pattern matching on keywords

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
```

# ── FULL CAMPAIGN LIFECYCLE ──

```python
def run_full_lifecycle(target: str, seed_context: str):
    """End-to-end: generate suite → optimize → evolve → repeat."""

    # 1. Generate initial suite (one-time, human approves)
    suite = generate_initial_suite(
        target_context=seed_context,
        num_gate=4,
        num_core_pairs=12,    # 6 contrastive pairs = 12 cases
        num_frontier=10,
        dimensions=["intelligence", "compliance", "tool_discipline", "deliverable_quality"]
    )
    suite = human_review_and_approve(suite)

    # 2. Run optimization campaign
    result = run_gepa_campaign(
        suite=suite,
        seed_context=seed_context,
        task_lm="haiku",
        reflection_lm="sonnet",
        max_metric_calls=200
    )

    # 3. Human reviews result
    if human_approves(result):
        apply_context(result.best_context, target)

    # 4. Evolve suite for next campaign (model change, drift, etc.)
    suite = evolve_suite(result.best_context, suite)

    # 5. Next campaign uses evolved suite
    # Gate and regression persist. Core may have graduated some cases.
    # Frontier has new cases targeting newly-discovered weaknesses.
    # Repeat from step 2.
```