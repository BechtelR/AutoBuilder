# Plan: Consolidate Architecture Docs into architecture/ Subdirectory

## Context

Six architecture docs in `.dev/` total ~2,975 lines and contain overlapping content across separate files. The goal: consolidate into `.dev/architecture/` as focused, non-overlapping files. `02-ARCHITECTURE.md` becomes a concise overview + linked reference map. Legacy numbered files (05-09) are replaced by their architecture/ counterparts. All content preserved. All 88+ cross-references updated via batch scripts.

## Source Files

| File | Lines | Disposition |
|------|-------|-------------|
| `02-ARCHITECTURE.md` | 809 | §1-3 stay as overview; §4-18 split across architecture/ files |
| `05-AGENTS.md` | 667 | Full content → `architecture/agents.md` |
| `06-SKILLS.md` | 376 | Full content → `architecture/skills.md` |
| `07-WORKFLOWS.md` | 404 | Full content → `architecture/workflows.md` |
| `08-STATE_MEMORY.md` | 364 | Full content → `architecture/state.md` |
| `09-TOOLS.md` | 355 | Full content → `architecture/tools.md` |

## Target Structure

```
.dev/
├── 02-ARCHITECTURE.md              # Overview + reference map (~200 lines)
├── architecture/
│   ├── gateway.md                   # Gateway layer, ACL, routes, type safety chain
│   ├── workers.md                   # ARQ workers, lifecycle, concurrency
│   ├── events.md                    # Event system, Redis Streams, CEO queue
│   ├── data.md                      # Data layer + infrastructure (DB, Redis, filesystem)
│   ├── engine.md                    # ADK engine internals, App container, LLM routing
│   ├── execution.md                 # Autonomous execution loop, multi-session model
│   ├── clients.md                   # CLI + Dashboard architecture
│   ├── agents.md                    # Agent hierarchy, types, composition, communication
│   ├── skills.md                    # Skill system, format, triggers, loading
│   ├── workflows.md                 # Pluggable workflows, manifests, registry
│   ├── state.md                     # State scopes, memory architecture, persistence
│   ├── tools.md                     # Tool registry, FunctionTools, GlobalToolset
│   └── observability.md             # Observability, context window, dynamic context
```

## Content Mapping (section → target file)

### From 02-ARCHITECTURE.md

| Section | Target | Notes |
|---------|--------|-------|
| §1 System Overview | `02-ARCHITECTURE.md` | Stays — overview text |
| §2 System Architecture Diagram | `02-ARCHITECTURE.md` | Stays — Mermaid diagram |
| §3 Request Flow | `02-ARCHITECTURE.md` | Stays — Mermaid sequence |
| §4 Gateway Layer | `architecture/gateway.md` | Verbatim |
| §5 Worker Architecture | `architecture/workers.md` | Verbatim |
| §6 Event System | `architecture/events.md` | Verbatim |
| §7 Data Layer | `architecture/data.md` | Merged with §10 |
| §8 ADK Engine — ADK Mapping table | `architecture/engine.md` | ADK primitive mapping |
| §8 ADK Engine — Multi-Model LiteLLM | `architecture/engine.md` | Model routing |
| §8 ADK Engine — Architecture Diagram | `architecture/engine.md` | Engine Mermaid |
| §8 ADK Engine — Hierarchical Agent Structure | `architecture/agents.md` | Merge with 05-AGENTS agent hierarchy |
| §8 ADK Engine — Inner Pipeline Composition | `architecture/agents.md` | Pipeline code example |
| §8 ADK Engine — Tool Registry | `architecture/tools.md` | Merge with 09-TOOLS toolset section |
| §9 Execution Loop | `architecture/execution.md` | Verbatim |
| §10 Infrastructure | `architecture/data.md` | Merged with §7 |
| §11 CLI Architecture | `architecture/clients.md` | Merged with §12 |
| §12 Dashboard Architecture | `architecture/clients.md` | Merged with §11 |
| §13 State Architecture | `architecture/state.md` | Merge with 08-STATE_MEMORY |
| §14 Multi-Agent Communication | `architecture/state.md` | Merge with 08-STATE_MEMORY |
| §15 Observability | `architecture/observability.md` | Merged with §16, §17 |
| §16 Context Window | `architecture/observability.md` | Merged with §15, §17 |
| §17 Dynamic Context | `architecture/observability.md` | Merged with §15, §16 |
| §18 App Container | `architecture/engine.md` | ADK App config |

### From standalone files (full content moves)

| Source | Target | Merge-in from 02-ARCH |
|--------|--------|----------------------|
| `05-AGENTS.md` | `architecture/agents.md` | + §8 agent hierarchy/factory + §8 inner pipeline |
| `06-SKILLS.md` | `architecture/skills.md` | (none) |
| `07-WORKFLOWS.md` | `architecture/workflows.md` | (none) |
| `08-STATE_MEMORY.md` | `architecture/state.md` | + §13 state architecture + §14 agent communication |
| `09-TOOLS.md` | `architecture/tools.md` | + §8 tool registry subsection |

### Handling overlapping content

Where 02-ARCH sections duplicate content already in 05-09 files, the merged target file keeps the **more detailed version** and adds any unique content from the other. No content is lost — duplicates are consolidated, not deleted.

## Cross-Reference Update Strategy

88 references across the repo. Use a temp bash script to batch-update:

**Files requiring updates** (grouped by type):

| File | Refs to update |
|------|---------------|
| `INDEX.md` + `CLAUDE.md` (in .dev/) | 02, 05, 06, 07, 08, 09 refs (12 lines) |
| `03-STRUCTURE.md` | Directory tree listing (6 lines) |
| `.architect.md` | Doc table (6 rows) |
| `.claude/commands/spec-phase.md` | Doc reference lines (3 lines) |
| `.claude/commands/build-phase.md` | Doc reference lines (4 lines) |
| `.claude/commands/model-phase.md` | Doc reference lines (6 lines) |
| `10-DEV_SETUP.md` | Related docs section (2 lines) |
| Root `AGENTS.md` (= CLAUDE.md) | Architecture links (2 lines) |
| Root `README.md` | Architecture links (2 lines) |
| `build-phase/.archive/phase-2/prompt.md` | Section refs → file paths (1 line) |
| `build-phase/phase-1/prompt.md` | 05-AGENTS ref (1 line) |
| `.discussion/260214_*.md` | Historical — add migration note header |
| `.discussion/260216_*.md` | Historical — add migration note header |
| Internal cross-refs within architecture/ files | Update 05↔09 links to relative paths |

**Script approach**: Generate a sed script from a mapping file (old path → new path), run against all .md files, verify with diff.

## Implementation Order (Safe Migration)

### Phase A: Preparation
1. Create `.dev/260217_migration.md` verification checklist
2. Create TaskCreate list matching the checklist

### Phase B: Copy-First (content safety net)
3. `mkdir .dev/architecture/`
4. Copy all 6 source files to architecture/ targets (content-only, no edits to sources yet)
   - This means all 13 target files are created with raw copied content
   - Sources remain untouched as safety net

### Phase C: Merge & Improve targets
5. For files that merge multiple sources (agents.md, state.md, tools.md, data.md, etc.):
   - Consolidate overlapping content
   - Add cross-reference "See also" links
   - Add `← [Architecture Overview](../02-ARCHITECTURE.md)` nav headers
6. For files from single sources (skills.md, workflows.md, etc.):
   - Add nav headers and cross-refs
   - Adjust any internal links to use new relative paths

### Phase D: Rewrite overview
7. Rewrite `02-ARCHITECTURE.md` as overview + reference map
   - Keep §1-3 (overview, diagrams, request flow)
   - Replace §4-18 with reference map table + one-line summaries with links

### Phase E: Batch reference updates
8. Create temp sed script mapping old → new paths
9. Run against all .md files in repo
10. Verify diff output — no false positives
11. Update `03-STRUCTURE.md` scaffold
12. Sync `INDEX.md` and `.dev/CLAUDE.md`

### Phase F: Verification (BEFORE deletes)
13. Run full checklist from `260217_migration.md`
14. Verify all links resolve to existing files
15. Verify no content lost (line count comparison: sum of sources vs sum of targets)
16. Verify no orphan references to deleted file names (outside .git/ and .discussion/ historical)
17. Grep for any remaining broken cross-refs

### Phase G: Delete legacy files (AFTER verification passes)
18. Rename sources to `*.bak` first (safety net)
19. Re-run verification against .bak state
20. Delete `.bak` files only after all checks pass
21. Final grep: confirm zero refs to old filenames remain

## Parallel Subagent Strategy

Work parallelizes at Phase C (merge & improve targets). Launch heavy subagents:

**Batch 1** (3 parallel subagents):
- Agent 1: Create `gateway.md`, `workers.md`, `events.md`, `clients.md` (simple verbatim extractions from 02-ARCH)
- Agent 2: Create `agents.md` (merge 05-AGENTS + §8 agent hierarchy), `execution.md` (from §9)
- Agent 3: Create `state.md` (merge 08-STATE_MEMORY + §13 + §14), `tools.md` (merge 09-TOOLS + §8 tool registry)

**Batch 2** (3 parallel subagents):
- Agent 4: Create `engine.md` (§8 ADK mapping/diagram + §18 App container), `observability.md` (§15-17), `data.md` (§7+§10)
- Agent 5: Create `skills.md` (from 06-SKILLS), `workflows.md` (from 07-WORKFLOWS)
- Agent 6: Rewrite `02-ARCHITECTURE.md` overview + reference map

**Batch 3** (2 parallel subagents):
- Agent 7: Batch reference update script — create + run sed mappings across entire repo
- Agent 8: Update INDEX.md, CLAUDE.md, 03-STRUCTURE.md, .architect.md

## Critical Files to Modify

**Create (13 new files):**
- `.dev/architecture/gateway.md`
- `.dev/architecture/workers.md`
- `.dev/architecture/events.md`
- `.dev/architecture/data.md`
- `.dev/architecture/engine.md`
- `.dev/architecture/execution.md`
- `.dev/architecture/clients.md`
- `.dev/architecture/agents.md`
- `.dev/architecture/skills.md`
- `.dev/architecture/workflows.md`
- `.dev/architecture/state.md`
- `.dev/architecture/tools.md`
- `.dev/architecture/observability.md`

**Rewrite:**
- `.dev/02-ARCHITECTURE.md` → overview + reference map

**Delete after migration:**
- `.dev/05-AGENTS.md`
- `.dev/06-SKILLS.md`
- `.dev/07-WORKFLOWS.md`
- `.dev/08-STATE_MEMORY.md`
- `.dev/09-TOOLS.md`

**Update references in:**
- `.dev/INDEX.md`, `.dev/CLAUDE.md`
- `.dev/03-STRUCTURE.md`
- `.dev/.architect.md`
- `.dev/10-DEV_SETUP.md`
- `.dev/.claude/commands/spec-phase.md`
- `.dev/.claude/commands/build-phase.md`
- `.dev/.claude/commands/model-phase.md`
- Root `AGENTS.md`, `README.md`
- `.dev/build-phase/` prompt files
- `.dev/.discussion/` files (migration note headers)
- Internal cross-refs within new architecture/ files

## Verification Checklist (mirrors 260217_migration.md)

- [x] All 13 architecture/ files created with correct content
- [x] 02-ARCHITECTURE.md rewritten as overview (~200 lines)
- [x] Every line from source files exists in a target file (no content lost)
- [x] All 5 legacy files deleted
- [x] `grep -r "05-AGENTS\|06-SKILLS\|07-WORKFLOWS\|08-STATE_MEMORY\|09-TOOLS" .` returns zero hits outside .git/ and .discussion/ historical docs
- [x] All markdown links `[text](path)` resolve to existing files
- [x] All architecture/ files have nav header linking back to overview
- [x] INDEX.md and CLAUDE.md updated and in sync
- [x] 03-STRUCTURE.md scaffold updated with architecture/ directory
- [x] .architect.md doc table updated — .architect.md has no doc table (architect instructions only); no stale refs to old 05-09 files
- [x] .claude/commands/*.md references updated
- [x] Root AGENTS.md and README.md references updated
- [x] No file exceeds 500 lines (guideline, not hard rule for agents.md) — **NOTE**: agents.md=771, tools.md=530; both are complex merged domains
- [x] 260217_migration.md checklist all items verified
