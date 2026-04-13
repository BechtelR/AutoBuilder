# Context Optimizer — Research & Algorithm

*Split from context-optimizer-research.md (Sections 1–2)*
*Captured: 2026-04-12*

---

*[← Index](./00-index.md)*

## Contents

- [1. Problem Statement](#1-problem-statement)
- [2. Research Summary](#2-research-summary)
  - [2.1 Optimization Algorithm Landscape](#21-optimization-algorithm-landscape)
  - [2.2 Recommendation: GEPA](#22-recommendation-gepa-genetic-pareto)
  - [2.3 DSPy Integration Path](#23-dspy-integration-path)

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
