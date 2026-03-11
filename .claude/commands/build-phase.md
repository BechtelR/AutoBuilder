---
description: Build a roadmap phase — implements spec with quality gates, double review, and evidence-based completion.
argument-hint: <phase-number> [--go] [--review=double|single|none]
---

<objective>
Build Phase {$ARGUMENTS}. Implement the spec with quality gates, double review, and evidence-based completion.

This is a SESSION command — no file output. It drives implementation from spec.md + model.md through to verified, reviewed, roadmap-complete code.

CRITICAL: NOT done until Completion Protocol steps A-E are complete and every item across all three verification layers shows PASS. Do not stop early. On blockers, ask the user.
</objective>

<context>
Parse phase number from arguments (if missing, ask). Flags:
- `--go` — skip plan approval, start building immediately
- `--review=double` (default) — two independent review passes
- `--review=single` — one review pass
- `--review=none` — skip review, quality gate only

Bootstrap — read into main context (parallel reads):
- @.dev/build-phase/phase-{N}/spec.md — full spec (deliverables, BOM components, decisions, requirements, build order)
- @.dev/build-phase/phase-{N}/frd.md — functional requirements (FR-{N}.{nn} IDs for verification — OPTIONAL, skip if absent)
- @.dev/build-phase/phase-{N}/model.md — architecture model (OPTIONAL — skip if not present)
- @.dev/03-STRUCTURE.md — file placement truth
- @.dev/02-ARCHITECTURE.md §4 only (lines 99-131) — architecture reference map for routing subagents to the right domain docs
- (.dev/INDEX.md automatically loaded via .dev/CLAUDE.md)

Do NOT read into main context:
- Full `02-ARCHITECTURE.md` — subagents read domain-specific sections as needed
- Selective `architecture/` files — subagents read these, not the orchestrator
- `04-TECH_STACK.md` — inject into subagents that need tech decisions
- Source code files — subagents read what they need (see context hygiene)

Skip `CLAUDE.md` and `.claude/rules/` (already in context).

If spec.md doesn't exist: stop and tell user to run `/spec-phase {N}` first.
If model.md doesn't exist: note it and proceed — model is optional for simple specs.
If frd.md doesn't exist: note it and proceed — FRD requirement verification will be skipped.
</context>

<context-hygiene>
The main context is an ORCHESTRATOR — it holds routing knowledge, not working knowledge. Target: complete the phase with at most 1 compaction (200k window).

Rules:
1. **Never read source code in main context.** Delegate all code reading to `Explore` or implementation subagents. The orchestrator needs file paths and patterns, not file contents.
2. **Architecture docs go to subagents.** The orchestrator holds only the §4 reference map to know which doc to inject into which subagent.
3. **Subagent prompts are data, not output.** Do not echo the full subagent prompt in main context — summarize what was delegated.
4. **Validation output stays in subagents.** `test-gates` runs commands and returns pass/fail + error summaries. Raw pytest/pyright output never enters main context unless fixing a failure directly.
5. **Summaries bubble up, details stay down.** Each subagent returns: what was done, what passed, what failed (with brief error context). Not full diffs or command transcripts.
6. **Re-reads are wasteful.** If a file was read in a subagent, don't re-read it in main context. Trust subagent results.
</context-hygiene>

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
Steps 1-5 sequential. Announce each step.

STEP 1 — PLAN

Gather everything needed to build. This step always runs — even with `--go`.

A. **Survey existing code** — launch `Explore` agent(s) to read every file the spec creates or modifies. The Explore agent returns a brief summary per file: exists/not, key patterns, imports, conventions. Do NOT read source files directly in main context.

B. **Map the work** — for each deliverable, confirm:
   - Which model.md interfaces/types it implements (if model.md exists)
   - Which existing code it extends or depends on (from Explore summary)
   - The validation command that proves it's done

C. **Confirm the build order** — walk spec.md Build Order. Per batch: which deliverables, parallel or sequential, what deps must be satisfied first.

D. **Surface the plan:**

| Batch | Deliverables | Key Files | Validates With |
|-------|-------------|-----------|----------------|
| 1     | P{N}.D{x}, D{y} | `path/...` | `command` |

**Verification Layers** (surface all three — preview of Step 5):

FRs (from frd.md, if exists — ALL FRs, NONE omitted):
- [ ] FR-{N}.{nn}: {description} → verify via deliverable validation commands

Deliverables (from spec.md — ALL deliverables, NONE omitted):
- [ ] P{N}.D{n}: {title} — BOM: {component IDs} → validate: `{command}`

Contract Items (from spec.md Traceability — ALL items, NONE omitted):
- [ ] {Contract item} → verify: `{command}`

**Without `--go` (default):** Stop and ask the user to approve the plan before proceeding.
**With `--go`:** Do NOT enter plan mode. Print the plan summary, then proceed directly to Step 2. Do NOT stop for approval.

E. **Create task list** — after plan is approved (or immediately with `--go`), use `TaskCreate` to create one task per step (Steps 2-5) + one per batch within Step 2, chained with `blockedBy`. Mark each `in_progress` when starting, `completed` when done. This is the primary enforcement mechanism — do NOT skip tasks.

STEP 2 — IMPLEMENT BY BATCH

Execute the Build Order from spec.md batch-by-batch. Each batch is one cycle:

1. **Delegate** — assign deliverables to subagents per `<delegation>`. Parallel batches → launch subagents in parallel. Sequential batches → one at a time.

   **Context injection per subagent** (progressive disclosure — give each agent only what it needs):
   - The deliverable's spec section (ID, files, description, BOM components, requirements, validation)
   - Relevant model.md interfaces/types for that deliverable (if model.md exists)
   - Design decisions from spec.md that apply to this deliverable
   - File paths from Step 1A survey — subagent reads the actual files itself
   - Relevant `.dev/` domain docs — use `02-ARCHITECTURE.md` §4 reference map to identify which `architecture/` file(s) to tell the subagent to read

   **Skill injection** — check available skills (listed in system context with descriptions), match by frontmatter description to the deliverable's domain, and instruct subagents to invoke matched skills. Not every deliverable needs a skill — only inject when a skill's description is relevant to the work.

2. **Validate** — run each deliverable's validation command from spec.md. Failures → fix in-place and re-validate.
3. **Gate** — all deliverables in the batch pass validation before starting the next batch.

Repeat for every batch in Build Order. Do NOT skip batches or reorder.

STEP 3 — QUALITY GATE

Delegate to `test-gates` subagent. It runs all checks and returns pass/fail summary:
1. `uv run ruff check .` — zero errors
2. `uv run ruff format --check .` — formatted
3. `uv run pyright` — zero errors (strict)
4. `uv run pytest` — all pass (or 0 collected, 0 errors)

If failures: `test-gates` returns error details. Fix in main context or delegate fixes, then re-run `test-gates` until clean. Reviewers should see mechanically clean code.

STEP 4 — REVIEW GATE

Behavior depends on `--review` flag (default: `double`):

**`--review=none`:** Skip this step entirely. Proceed to Step 5.

**`--review=single` or `--review=double`:**

Launch parallel `reviewer` subagents scaled to spec size:

| Deliverables | Reviewers per pass |
|--------------|-------------------|
| 1-4          | 2                 |
| 5-8          | 3                 |
| 9-19         | 4                 |
| 20+          | 6                 |

Split files evenly across reviewers. Each checks:
- Correctness against spec.md requirements
- Model conformance (interfaces, types, data flow match model.md — skip if no model.md)
- CLAUDE.md and `.claude/rules/` adherence
- Type safety (no `Any`, Pydantic at boundaries)
- Security (no hardcoded secrets, input validation)
- FRD requirement conformance (every FR-{N}.{nn} from frd.md satisfied — skip if no frd.md)
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

Three independent verification layers — all required, all can fail independently:

| Layer | Question | Artifact | Verified In |
|-------|----------|----------|-------------|
| **FRs** | Did it work correctly? | `frd.md` FR-{N}.{nn} checkboxes | Step A |
| **Deliverables** | Was it built right? | `spec.md` BOM + requirement checkboxes | Step B |
| **Contract items** | Was the phase scope completed? | `08-ROADMAP.md` contract checkboxes | Step C |

Passing FRs does not guarantee deliverable conformance. Checking off deliverables does not guarantee contract completion.

**A. Verify FRs**
Delegate to `test-gates` subagent: pass it the frd.md FR list and spec.md FRD Coverage table. It runs each deliverable's validation commands and returns pass/fail per FR. Mark `[x]` in `frd.md` only for confirmed PASS. Failures → fix and re-verify. Skip if no frd.md.

**B. Verify Deliverables**
Open `.dev/build-phase/phase-{N}/spec.md`. Per deliverable:
1. `[x]` each BOM Component — only if implemented and confirmed
2. `[x]` each Requirement — only if proven by validation command output (from Step A subagent results or direct run)
3. Unverifiable items → leave unchecked, report to user

**C. Verify Contract Items**
Open `.dev/08-ROADMAP.md`:
1. `[x]` each contract checkbox — verification evidence from Steps A/B, run additional commands only if not already covered
2. Status: `IN PROGRESS` → `DONE`
3. Update top-level status to next phase

**D. Final Quality Gate**
Run directly (not via subagent) — this is the orchestrator's own verification, not delegated:
```
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```
If clean (common case): minimal context cost, move on. If failures: delegate fixes to `test-gates` subagent, then re-run directly until clean.

**E. Completion Summary**
Print evidence table covering all three layers:

| # | Item | Layer | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | FR-{N}.{nn}: {description} | FRs | PASS/FAIL | {command + result summary} |
| 2 | P{N}.D{n}: {title} requirements | Deliverables | PASS/FAIL | {command + result summary} |
| 3 | {contract item} | Contract | PASS/FAIL | {command + result summary} |

NOT done until A-E complete and every row shows PASS.
</process>

<verification>
Before reporting done — all must be true (see Step 5 for execution details):
1. Completion Protocol steps A-E all executed (not skipped)
2. All three verification layers pass (FRs + Deliverables + Contract items) with evidence
3. Quality gate clean (ruff, pyright, pytest)
4. Review completed per `--review` flag, report at `.dev/build-phase/phase-{N}/review.md` (unless `--review=none`), all findings resolved
5. Roadmap status updated to DONE
6. Evidence table printed with all rows PASS
</verification>
