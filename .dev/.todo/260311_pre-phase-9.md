# Pre-Phase 9 Deliverables

*Date: 2026-03-11*
*Context: Memory/skill injection asymmetry discovered during Phase 6 FRD review (Decision #69)*
*Priority: Must complete before or during Phase 9 (Memory System)*
*Status: PLANNED*

---

## Code Changes

- [ ] Add `FragmentType.MEMORY` to `app/models/enums.py`
- [ ] Add `memory_context` field to `InstructionContext` in `app/agents/assembler.py`
- [ ] Add MEMORY fragment assembly in `InstructionAssembler.assemble()` — between TASK and SKILL, with `escape_braces()` and source auditing
- [ ] Add per-agent `applies_to` filtering for memory (same pattern as skills) — reviewer may need different memory context than planner
- [ ] Remove `{memory_context}` ADK template placeholder from agent definition bodies (planner.md, coder.md, reviewer.md, etc.)
- [ ] Update `MemoryLoaderAgent` state output to include metadata for assembler filtering (parallel to skill `applies_to`)
- [ ] Update `app/agents/context_recreation.py` for assembler-based memory injection

## Back-Propagation: Architecture Docs

- [ ] `architecture/agents.md` — 15+ refs: update instruction composition diagram (line ~274 `{memory_context}` → assembler MEMORY fragment), data flow (line ~349, ~355), MemoryLoaderAgent section (line ~778-788), pipeline diagrams (line ~1035-1036, ~1105-1108), clarify `{memory_context}` is NOT used for LLM agents (parallel to `{loaded_skills}` clarification already done)
- [ ] `architecture/context.md` — 6 refs: update context assembly lifecycle (lines ~119-140), reassemble step (line ~245), MemoryLoaderAgent section (line ~182-184)
- [ ] `architecture/state.md` — 4 refs: update pipeline state flow diagram (lines ~249-266), state template references (line ~254, ~258, ~266), MemoryLoaderAgent entry (line ~68)
- [ ] `architecture/engine.md` — 1 ref: pipeline stage diagram (line ~66)
- [ ] `architecture/workflows.md` — 2 refs: pipeline composition (line ~277, ~301)

## Back-Propagation: Core Docs

- [ ] `01-PRD.md` — 1 ref: PR-15b (line ~136) — update to reflect assembler-based injection path, not just "deterministic pipeline step"
- [ ] `02-ARCHITECTURE.md` — verify Key Architectural Decisions section mentions memory/skill symmetry
- [ ] `08-ROADMAP.md` — 1 ref: Phase 5a contract item (line ~163) — no change needed (describes MemoryLoaderAgent behavior, not injection path). Phase 9 scope summary should mention assembler migration.
- [ ] `07-COMPONENTS.md` — 2 refs: A37 and M15 entries (lines ~216, ~464) — update dependency description from "BaseMemoryService (ADK)" to include InstructionAssembler dependency
- [ ] `03-STRUCTURE.md` — 1 ref: file listing (line ~75) — no change needed (file path unchanged)
- [ ] `.decision-log.md` — Decision #57 (line ~63) — no change needed (describes the agent, not injection path). Decision #69 already captures the migration.

## Back-Propagation: Phase Build Docs

- [ ] `build-phase/phase-5a/spec.md` — 2 refs (lines ~270-271): historical, no update needed
- [ ] `build-phase/phase-5a/model.md` — 5 refs: historical, no update needed
- [ ] `build-phase/phase-5a/frd.md` — 2 refs (lines ~84-85): historical, no update needed
- [ ] `build-phase/phase-5b/spec.md` — 2 refs (lines ~410-411): historical, no update needed
- [ ] `build-phase/phase-5b/model.md` — 2 refs (lines ~536, ~542): historical, no update needed
- [ ] `build-phase/phase-5b/frd.md` — 2 refs (lines ~113-114): historical, no update needed

**Note:** Phase 5a/5b build docs are historical records — they describe what was built at that time. Do NOT retroactively update them. The migration is a Phase 9 concern.

## Verification

- [ ] Grep all `.dev/` docs for `{memory_context}` — zero remaining references to ADK template path (except historical phase build docs)
- [ ] Verify agents.md, context.md, state.md all describe memory and skills using the same assembler-based injection pattern
- [ ] Verify no doc claims memory uses ADK Layer 4 template substitution (except historical)

## References

- Decision #69: Memory/skill injection unification
- Decision #57: MemoryLoaderAgent formalized
- Decision #50: InstructionAssembler fragment types
- Current path: `MemoryLoaderAgent` → `state["memory_context"]` → `{memory_context}` ADK Layer 4 template
- Target path: `MemoryLoaderAgent` → `state["memory_context"]` → `InstructionAssembler` MEMORY fragment (per-agent filtered)
- Impact scan: 75+ references across 22 files (5 architecture, 6 phase build, 4 core, 3 component/roadmap/structure, 4 other)
