# Terminology Alignment, Skills Standard, PM Architecture
*Date: 2026-02-16*
*Status: DECIDED*

---

## 1. Tool/Agent Terminology — Align with ADK Taxonomy

### Problem
Our docs conflate "deterministic agents" and "tools." `09-TOOLS.md` is titled "Tools & Deterministic Agents" and describes both `FunctionTool` wrappers and `BaseAgent` subclasses in one document. ADK's official taxonomy separates these clearly:

- **Tools** (`FunctionTool`, `BaseTool`): Callable functions with no reasoning. Passive — the LLM decides when to call them.
- **Agents** (`BaseAgent`, `LlmAgent`): Orchestration participants with lifecycle. Active — pipeline structure determines when they run.

### Decision
Align with ADK's taxonomy. Deterministic `BaseAgent` subclasses (LinterAgent, TestRunnerAgent, SkillLoaderAgent, etc.) are **agents**, not tools. They belong in `05-AGENTS.md`. `09-TOOLS.md` covers only `FunctionTool` wrappers and the tool registry.

### Changes
- `09-TOOLS.md`: Remove deterministic agent sections (SkillLoaderAgent, LinterAgent, TestRunnerAgent, FormatterAgent, DependencyResolverAgent, RegressionTestAgent, ContextBudgetAgent). Retitle to "Tools" or "FunctionTools & Tool Registry."
- `05-AGENTS.md`: Already has deterministic agent content. Verify completeness after `09-TOOLS.md` cleanup.
- Stop using the phrase "deterministic agent" as a tool synonym. Use "custom agent" (ADK term) or "deterministic custom agent" when emphasizing the non-LLM nature.

---

## 2. Skills System — Adopt Agent Skills Open Standard

### Problem
We designed a custom skills system (`06-SKILLS.md`). ADK has its own experimental skills implementation (`SkillToolset`, v1.25.0+). Should we use ADK's?

### Evaluation

| Aspect | Our Design | ADK Skills | Agent Skills Standard |
|--------|-----------|------------|----------------------|
| **Maturity** | Designed, not built | Experimental, incomplete (scripts not supported) | Open specification |
| **Loading** | Deterministic (`SkillLoaderAgent`) — LLM cannot skip | Tool-based (`SkillToolset`) — LLM decides when to use | N/A (spec only) |
| **Matching** | Trigger-based (deliverable_type, file_pattern, tag_match, explicit, always) | Manual — developer specifies which skills to load | N/A |
| **File format** | Markdown + YAML frontmatter (custom schema) | `SKILL.md` + `references/` + `assets/` + `scripts/` | `SKILL.md` with frontmatter, L1/L2/L3 progressive disclosure |
| **Integration** | State injection via `{loaded_skills}` template | Agent `tools=[]` list | N/A |

### Decision
- **Continue with custom deterministic loading** — our `SkillLoaderAgent` approach is correct. Skills must load deterministically; the LLM cannot be allowed to skip project conventions.
- **Adopt the Agent Skills open standard file format** ([agentskills.io/specification](https://agentskills.io/specification)) — use `SKILL.md` naming, L1/L2/L3 progressive disclosure structure, and the standard frontmatter schema. This ensures interoperability if the ecosystem converges on this standard.
- **Do NOT use ADK's `SkillToolset` runtime** — it's experimental, tool-based (LLM-discretionary), and lacks matching. Our runtime is better for our use case.

### Impact
- `06-SKILLS.md` needs updating to reference the Agent Skills standard for file format
- Frontmatter schema should align with the standard where possible (name, description, triggers map to standard fields)
- Directory convention: `SKILL.md` (not arbitrary filenames), with `references/` and `assets/` subdirectories per skill

---

## 3. PM Absorbs BatchOrchestrator

### Problem
After the hierarchical supervision decision (#29-35), the docs described BatchOrchestrator as "PM-Level Outer Loop" which was ambiguous — does BatchOrchestrator = PM? Is it a sub-agent of PM?

### Analysis
BatchOrchestrator's loop is purely mechanical:
```
while incomplete deliverables exist:
    select ready batch (topological sort)
    construct ParallelAgent
    run batch
    collect results
    run regressions
    checkpoint
```

Making this a separate `CustomAgent` beneath the PM creates problems:
1. If BatchOrchestrator runs the entire loop, PM never reasons between batches — defeating the purpose of an LlmAgent PM
2. If it runs one batch at a time, it's a glorified function call with extra indirection
3. It's a single-use abstraction (violates "abstract only after third occurrence")

### Decision
**PM IS the outer loop.** No separate BatchOrchestrator agent.

The mechanical operations become **tools** the PM calls:
- `select_ready_batch()` — dependency-aware batch selection (topological sort)
- `run_regression_tests()` — cross-deliverable regression suite
- `checkpoint_project()` — persist project state for resume

Deterministic safety via **callbacks**, not a separate agent:
- `after_agent_callback` on each `DeliverablePipeline` — monitors completion, flags critical failures
- `before_agent_callback` — injects context, verifies preconditions

### Oversight Model

| When | Who | How |
|------|-----|-----|
| Before batch | PM (LLM) | Reasons about batch composition, sets strategy |
| During batch | Callbacks (deterministic) | `after_agent_callback` monitors each pipeline, flags failures |
| After batch | PM (LLM) | Observes results, decides retry/skip/escalate/continue |
| Between batches | PM (LLM) | Full reasoning — reorder, adjust, checkpoint, escalate to Director |

### Hierarchy (Updated)
```
Director (LlmAgent, opus) — root_agent
  └── PM (LlmAgent, sonnet) — per-project, IS the outer loop
        ├── tools: select_ready_batch, run_regression, checkpoint
        ├── after_agent_callback: verify_batch_completion
        └── sub_agents: DeliverablePipeline instances (workers)
```

### P4 Retrospective
P4 validated that dynamic `ParallelAgent` batch construction with dependency ordering works. This pattern is still used — it's the implementation technique the PM employs via tools. P4's validation holds; it just maps to PM's tool usage, not a separate agent.

### Phase 5 Prototype
Add a PM prototype to Phase 5 spec: validate that an LlmAgent PM reliably manages a batch loop with tools + callbacks. Similar to how P4 validated the mechanical pattern.

---

## Decisions Summary

| # | Decision | Rationale |
|---|----------|-----------|
| 36 | Tool/Agent terminology aligned with ADK taxonomy | ADK separates tools (passive, LLM-discretionary) from agents (active, pipeline-structured); our docs conflated them |
| 37 | Skills system adopts Agent Skills open standard file format | Interoperability with emerging standard; our deterministic runtime stays custom |
| 38 | PM absorbs BatchOrchestrator — no separate orchestrator agent | Single-use abstraction; PM needs inter-batch reasoning; mechanical parts become tools |
| 39 | Batch oversight via PM tools + deterministic callbacks | PM manages strategy; `after_agent_callback` provides intra-batch safety net |
