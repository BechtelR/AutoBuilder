# TODO: Create Standardized Project Initialization Bootstrap Process

## Goal

Define a repeatable, deterministic process that takes a project from raw design idea to fully documented, scaffolded codebase. This should be a reusable playbook — not AutoBuilder-specific — that any future project can follow.

## The Process We Actually Followed (Reverse-Engineered)

This session with AutoBuilder organically followed these phases:

### Phase 1: Vision & Problem Space
- User describes the idea, problems being solved, prior art
- Agent challenges assumptions, asks clarifying questions
- Output: `00-VISION.md`

### Phase 2: Framework & Core Tech Research
- Agent researches current ecosystem (web searches, docs)
- Evaluate framework candidates with structured comparison
- User + agent debate tradeoffs, make decisions
- Output: Framework selection, `03-TECH_STACK.md` (partial)

### Phase 3: Architecture Design
- Define system layers, data flow, component boundaries
- Debate transport (REST/SSE/GraphQL/gRPC), persistence, workers, events
- Agent proposes, user challenges, iterate until solid
- Output: `01-ARCHITECTURE.md`

### Phase 4: Infrastructure Decisions
- Database, ORM, task queue, event bus, cron, cache
- Worker model (in-process vs out-of-process)
- Type safety chain (end-to-end)
- Output: `03-TECH_STACK.md` (complete), updates to architecture

### Phase 5: Interface Layer Design
- CLI, API gateway, web dashboard
- Frontend stack, state management, styling, codegen
- Output: Updates across all docs

### Phase 6: Documentation Formalization
- Apply templates (agents.template.md, readme.template.md, etc.)
- Single source of truth for structure (`02-STRUCTURE.md`)
- Cross-reference consistency, deduplication
- Renumber, rename, clean up
- Output: Complete `.dev/` doc set, AGENTS.md, README.md

### Phase 7: Scaffold & Initialize
- Create `pyproject.toml`, directory structure, config files
- Initialize git, pre-commit hooks, CI skeleton
- Output: Working empty project that builds and passes lint/typecheck

## What Needs to Be Formalized

1. **Checklist/template** for each phase — what questions to ask, what outputs to produce
2. **Decision log template** — standardized format for recording decisions with rationale
3. **Quality gates** between phases — what must be true before moving on
4. **Parallel vs sequential** — which phases can overlap, which are blocking
5. **Agent workflow** — which phases benefit from research subagents, which need direct discussion
6. **Templates** — the `templates/*.md` files already exist; formalize when each applies
7. **Initialization script or skill** — automate Phase 7 (scaffold creation) once docs are done

## Deliverable

[ ] A reusable process document (maybe a skill or command) that:
    [ ] Walks through phases with the user
    [ ] Produces all `.dev/` docs from templates
    [ ] Records decisions in a changelog
    [ ] Creates the project scaffold
    [ ] Results in a project that's ready for Phase 1 MVP development

## Notes

- The process should be opinionated but adaptable (Python vs TS, monolith vs distributed, etc.)
- Each phase should have a clear "done" signal
- The user should feel like they're making decisions, not filling out forms
- Agent should bring expert researched recommendations with evidence, not menus of options
