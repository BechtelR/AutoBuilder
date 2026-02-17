---
description: Build a roadmap phase — implements spec with quality gates, double review, and evidence-based completion.
argument-hint: <phase-number> [--go] [--review=double|single|none]
---

<objective>
Build Phase {$ARGUMENTS}. Implement the spec with quality gates, double review, and evidence-based completion.

This is a SESSION command — no file output. It drives implementation from spec.md + model.md through to verified, reviewed, roadmap-complete code.

CRITICAL: NOT done until Completion Protocol steps A-E are complete and every contract item shows PASS. Do not stop early. On blockers, ask the user.
</objective>

<context>
Parse phase number from arguments (if missing, ask). Flags:
- `--go` — skip plan approval, start building immediately
- `--review=double` (default) — two independent review passes
- `--review=single` — one review pass
- `--review=none` — skip review, quality gate only

Bootstrap (parallel reads):
- @.dev/build-phase/phase-{N}/spec.md — full spec (deliverables, decisions, requirements, build order)
- @.dev/build-phase/phase-{N}/model.md — architecture model (OPTIONAL — skip if not present)
- @.dev/03-STRUCTURE.md — file placement truth
- @.dev/02-ARCHITECTURE.md — five-layer architecture
- (.dev/INDEX.md automatically loaded via .dev/CLAUDE.md)

Selective reads (only what the phase touches, via INDEX.md):
- Agents → `architecture/agents.md` | Skills → `architecture/skills.md` | Workflows → `architecture/workflows.md`
- State/memory → `architecture/state.md` | Tools → `architecture/tools.md`
- Tech decisions → `04-TECH_STACK.md`

Skip `CLAUDE.md` and `.claude/rules/` (already in context).

If spec.md doesn't exist: stop and tell user to run `/spec-phase {N}` first.
If model.md doesn't exist: note it and proceed — model is optional for simple specs.
</context>

<delegation>
MUST DELEGATE work to parallel subagents to preserve context window:
- `subtask-heavy` — focused implementation requiring reasoning or domain expertise
- `subtask` — straightforward implementation tasks
- `reviewer` — code review (used in Double Review Gate)
- `reflector` — critique implementation against spec/model/standards
- `test-gates` — run quality validation (all checks)
- `garbage-cleanup` — dead code detection after refactors
- `Explore` — codebase research and pattern discovery
</delegation>

<process>
Steps 1-5 sequential. Announce each step. Use `TaskCreate` to create one task per step + one per batch in Step 2, chained with `blockedBy`. Mark each `in_progress` when starting, `completed` when done. This is the primary enforcement mechanism — do NOT skip tasks.

STEP 1 — PLAN

Gather everything needed to build. This step always runs — even with `--go`.

A. **Read existing code** — for every file the spec creates or modifies, read what's already there. Understand current patterns, imports, and conventions in the target modules. Use `Explore` agents for unfamiliar areas.

B. **Map the work** — for each deliverable, confirm:
   - Which model.md interfaces/types it implements (if model.md exists)
   - Which existing code it extends or depends on
   - The validation command that proves it's done

C. **Confirm the build order** — walk spec.md Build Order. Per batch: which deliverables, parallel or sequential, what deps must be satisfied first.

D. **Surface the plan:**

| Batch | Deliverables | Key Files | Validates With |
|-------|-------------|-----------|----------------|
| 1     | P{N}.D{x}, D{y} | `path/...` | `command` |

**Completion Contract** (from spec.md Traceability — ALL items, NONE omitted):
- [ ] {Contract item} → verify: `{command}`

**Without `--go` (default):** Stop and ask the user to approve the plan before proceeding.
**With `--go`:** Do NOT enter plan mode. Print the plan summary, then proceed directly to Step 2. Do NOT stop for approval.

STEP 2 — IMPLEMENT BY BATCH

Execute the Build Order from spec.md batch-by-batch. Each batch is one cycle:

1. **Delegate** — assign deliverables to subagents per `<delegation>`. Parallel batches → launch subagents in parallel. Sequential batches → one at a time.

   **Context injection per subagent** (progressive disclosure — give each agent only what it needs):
   - The deliverable's spec section (ID, files, description, requirements, validation)
   - Relevant model.md interfaces/types for that deliverable (if model.md exists)
   - Design decisions from spec.md that apply to this deliverable
   - Existing code in files being created/modified (from Step 1A findings)
   - Relevant `.dev/` doc sections based on files touched (e.g., gateway → `architecture/gateway.md`, agents → `architecture/agents.md`)

   **Skill injection** — check available skills (listed in system context with descriptions), match by frontmatter description to the deliverable's domain, and instruct subagents to invoke matched skills. Not every deliverable needs a skill — only inject when a skill's description is relevant to the work.

2. **Validate** — run each deliverable's validation command from spec.md. Failures → fix in-place and re-validate.
3. **Gate** — all deliverables in the batch pass validation before starting the next batch.

Repeat for every batch in Build Order. Do NOT skip batches or reorder.

STEP 3 — QUALITY GATE

ALL must pass before proceeding to review:
1. `uv run ruff check .` — zero errors
2. `uv run ruff format --check .` — formatted
3. `uv run pyright` — zero errors (strict)
4. `uv run pytest` — all pass (or 0 collected, 0 errors)

Fix and re-run until clean. Reviewers should see mechanically clean code.

STEP 4 — REVIEW GATE

Behavior depends on `--review` flag (default: `double`):

**`--review=none`:** Skip this step entirely. Proceed to Step 5.

**`--review=single` or `--review=double`:**

Launch parallel `reviewer` subagents scaled to spec size:

| Deliverables | Reviewers per pass |
|--------------|-------------------|
| 1-4          | 2                 |
| 5-8          | 3                 |
| 9+           | 4                 |

Split files evenly across reviewers. Each checks:
- Correctness against spec.md requirements
- Model conformance (interfaces, types, data flow match model.md — skip if no model.md)
- CLAUDE.md and `.claude/rules/` adherence
- Type safety (no `Any`, Pydantic at boundaries)
- Security (no hardcoded secrets, input validation)
- Code quality (no dead code, no debug logging, no over-engineering)

**Execution:**
1. **Pass 1**: Launch reviewers. Reviewers fix issues directly and report what they fixed and what they flagged.
2. **Pass 2** (`--review=double` only): Launch fresh reviewers (same instructions, same file splits). Fixes + flags collected.
3. **Consolidate**: Merge results into `.dev/build-phase/phase-{N}/review.md`. Deduplicate. Classify unresolved findings by severity (HIGH / MEDIUM / LOW).

**Unresolved Fix Loop:**
1. Fix all unresolved findings — HIGH, MEDIUM, and LOW (disputed items → get user confirmation)
2. Repeat until zero unresolved findings or all remaining confirmed false positives

Do NOT proceed to Step 5 until resolved.

STEP 5 — COMPLETION PROTOCOL

CRITICAL — Every checkbox requires EVIDENCE (command output or observable result). Never mark without proof.

**A. Verify Completion Contract**
Per item in Completion Contract: run verification command → read output → only mark `[x]` on proven success. Failures → fix and re-verify.

**B. Mark Spec Complete**
Open `.dev/build-phase/phase-{N}/spec.md`. Per deliverable: run validation → check off (`[x]`) only passing requirements. Unverifiable → leave unchecked, report to user.

**C. Mark Roadmap Complete**
Open `.dev/01-ROADMAP.md`:
1. `[x]` each deliverable checkbox — only if ALL corresponding spec requirements passed in B
2. `[x]` each contract checkbox — only if verification passed in A
3. Status: `IN PROGRESS` → `DONE`
4. Update top-level status to next phase

**D. Final Quality Gate**
Run directly (not via subagent):
```
uv run ruff check . && uv run ruff format --check . && uv run pyright
```
Fix and re-run until clean.

**E. Completion Summary**
Print evidence table:

| # | Contract Item | Status | Evidence |
|---|---------------|--------|----------|
| 1 | {item} | PASS/FAIL | {proof} |

NOT done until A-E complete and every row shows PASS.
</process>

<verification>
Before reporting done, verify:
1. All spec deliverables implemented (check off in spec.md)
2. Quality gate passes (ruff, pyright, pytest)
3. Review report exists at `.dev/build-phase/phase-{N}/review.md` (unless `--review=none`)
4. All findings resolved (unless `--review=none`)
5. Completion Protocol steps A-E all executed with evidence
6. Roadmap updated (status, checkboxes)
7. Evidence table printed with all rows PASS
</verification>

<success_criteria>
- All spec deliverables implemented and requirements checked off
- Quality gate clean (ruff + pyright + pytest)
- Review completed per `--review` flag (default: double), report at `.dev/build-phase/phase-{N}/review.md`
- Completion Protocol A-E executed with evidence
- Roadmap status updated to DONE
- Evidence table shows all PASS
</success_criteria>
