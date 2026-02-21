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

Bootstrap (parallel reads):
- @.dev/build-phase/phase-{N}/spec.md — full spec (deliverables, BOM components, decisions, requirements, build order)
- @.dev/build-phase/phase-{N}/frd.md — functional requirements (FR-{N}.{nn} IDs for verification — OPTIONAL, skip if absent)
- @.dev/build-phase/phase-{N}/model.md — architecture model (OPTIONAL — skip if not present)
- @.dev/03-STRUCTURE.md — file placement truth
- @.dev/02-ARCHITECTURE.md — system architecture (conformance target)
- (.dev/INDEX.md automatically loaded via .dev/CLAUDE.md)

Selective reads (only what the phase touches, via INDEX.md):
- Agents → `architecture/agents.md` | Skills → `architecture/skills.md` | Workflows → `architecture/workflows.md`
- State/memory → `architecture/state.md` | Tools → `architecture/tools.md`
- Tech decisions → `04-TECH_STACK.md`

Skip `CLAUDE.md` and `.claude/rules/` (already in context).

If spec.md doesn't exist: stop and tell user to run `/spec-phase {N}` first.
If model.md doesn't exist: note it and proceed — model is optional for simple specs.
If frd.md doesn't exist: note it and proceed — FRD requirement verification will be skipped.
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
Steps 1-5 sequential. Announce each step.

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
If frd.md exists: for each FR-{N}.{nn}, find the deliverable(s) that cover it (via spec.md FRD Coverage table), run those deliverables' validation commands → read output → mark `[x]` in `frd.md` only on proven success. Failures → fix and re-verify. Skip if no frd.md.

**B. Verify Deliverables**
Open `.dev/build-phase/phase-{N}/spec.md`. Per deliverable:
1. `[x]` each BOM Component — only if implemented and confirmed
2. `[x]` each Requirement — only if proven by validation command output
3. Unverifiable items → leave unchecked, report to user

**C. Verify Contract Items**
Open `.dev/08-ROADMAP.md`:
1. `[x]` each contract checkbox — run verification command from spec.md Contract Coverage table, mark only on proven success
2. Status: `IN PROGRESS` → `DONE`
3. Update top-level status to next phase

**D. Final Quality Gate**
Run directly (not via subagent):
```
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
```
Fix and re-run until clean.

**E. Completion Summary**
Print evidence table covering all three layers:

| # | Item | Layer | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | FR-{N}.{nn}: {description} | FRs | PASS/FAIL | {command + output} |
| 2 | P{N}.D{n}: {title} requirements | Deliverables | PASS/FAIL | {command + output} |
| 3 | {contract item} | Contract | PASS/FAIL | {command + output} |

NOT done until A-E complete and every row shows PASS.
</process>

<verification>
Before reporting done, verify all three layers:
1. **FRs**: every FR-{N}.{nn} checked off in frd.md with evidence (if frd.md exists)
2. **Deliverables**: every BOM component and requirement checked off in spec.md with evidence
3. **Contract items**: every contract checkbox marked in 08-ROADMAP.md with evidence
4. Quality gate passes (ruff, pyright, pytest)
5. Review report exists at `.dev/build-phase/phase-{N}/review.md` (unless `--review=none`)
6. All review findings resolved (unless `--review=none`)
7. Roadmap status updated to DONE
8. Evidence table printed with all rows PASS across all three layers
</verification>

<success_criteria>
- All FR checkboxes marked in frd.md with evidence (if frd.md exists)
- All spec deliverable BOM components and requirements checked off with evidence
- All roadmap contract items checked off with evidence; status updated to DONE
- Quality gate clean (ruff + pyright + pytest)
- Review completed per `--review` flag (default: double), report at `.dev/build-phase/phase-{N}/review.md`
- Completion Protocol A-E executed
- Evidence table shows all PASS
</success_criteria>
