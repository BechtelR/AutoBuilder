# Context Optimizer — Architecture, API & Data Model

*Split from context-optimizer-research.md (Sections 3–6)*
*Captured: 2026-04-12*

---

*[← Index](./00-index.md)*

## Contents

- [3. Architecture](#3-architecture)
  - [3.1 Design Principles](#31-design-principles)
  - [3.2 Evaluation Modes: Intrinsic vs. Extrinsic](#32-evaluation-modes-intrinsic-vs-extrinsic)
  - [3.3 System Context](#33-system-context)
  - [3.4 Component Overview](#34-component-overview)
- [4. API Design](#4-api-design)
  - [4.1 Eval Suite Endpoints](#41-eval-suite-endpoints)
  - [4.2 Campaign Endpoints](#42-campaign-endpoints)
  - [4.3 Result Endpoints](#43-result-endpoints)
- [5. Data Model](#5-data-model)
  - [5.1 Eval Suite](#51-eval-suite)
  - [5.2 Eval Case](#52-eval-case)
  - [5.3 Campaign](#53-campaign)
  - [5.4 Optimized Result](#54-optimized-result)
- [6. Worker Implementation](#6-worker-implementation)
  - [6.1 Campaign Execution](#61-campaign-execution)
  - [6.2 Validation Pipeline](#62-validation-pipeline)
  - [6.3 Cost Tracking](#63-cost-tracking)
  - [6.4 Concrete Examples](#64-concrete-examples)

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
