# Phase 6 Spec: Skills System
*Generated: 2026-03-11*

## Overview

Phase 6 replaces the NullSkillLibrary stub (Phase 5a forward-dependency contract) with a production skill loading system. After Phase 6, agents receive task-relevant domain knowledge — conventions, patterns, strategies, review checklists — automatically based on deliverable context instead of generic instructions for every task.

The system implements the Agent Skills open standard file format (`SKILL.md` with YAML frontmatter) with AutoBuilder's deterministic trigger matching engine. Skills are discovered via filesystem scan, indexed by frontmatter metadata, cached in Redis, and loaded into agent instructions via the existing InstructionAssembler. Five trigger types (deliverable_type, file_pattern, tag_match, explicit, always) provide precise matching. A description keyword fallback ensures third-party skills work without modification.

The three-layer deterministic model applies across all agent tiers: (1) role-bound skills via `always` trigger + `applies_to` — Director always gets governance skills, PM always gets management skills; (2) context-matched skills via trigger matching against deliverable metadata — workers only, via SkillLoaderAgent; (3) explicit override via `requested_skills` in session state — rare, additive. Director and PM receive skills at agent build time; workers receive skills at pipeline runtime. Same matching engine, different call site.

Phase 6 also ships 17 global skills: 7 domain (code, review, test, planning), 4 authoring (skill, agent, workflow, project conventions), 4 file-editing (docx, xlsx, pptx, pdf including `scripts/` directories), and 2 role-bound supervision skills. It establishes the project-local override directory convention (`.agents/skills/`) and enables autonomous skill creation by agents.

## Prerequisites

| Prerequisite | Status | Evidence |
|---|---|---|
| Phase 5a: Agent Definitions & Pipeline | MET | SkillLoaderAgent defined, SkillLibraryProtocol established, NullSkillLibrary stub operational, pipeline wiring complete |
| Phase 5b: Supervision & Integration | MET | Director/PM build functions exist (`build_work_session_agents`, `build_chat_session_agent`), InstructionAssembler operational, context recreation preserves `loaded_skill_names` |

## Design Decisions

### DD-1: Frontmatter Extension Field Placement

AutoBuilder extension fields (`triggers`, `tags`, `applies_to`, `priority`, `cascades`) go at the **YAML top level** alongside `name`/`description` — NOT under a `metadata` key.

**Rationale:** The Agent Skills spec defines `metadata` as a string-to-string map. AutoBuilder's extensions are complex types (lists, objects, integers) that violate this constraint. Top-level placement keeps the standard `metadata` field spec-compliant for true string-value annotations while other parsers simply ignore unknown top-level keys. Per FRD rabbit hole resolution and model §SKILL.md Frontmatter Schema.

```yaml
---
name: api-endpoint                     # Standard field
description: REST API endpoint guide   # Standard field
triggers:                              # AutoBuilder extension (top-level)
  - deliverable_type: api_endpoint
tags: [api, http]                      # AutoBuilder extension (top-level)
applies_to: [coder, reviewer]          # AutoBuilder extension (top-level)
priority: 10                           # AutoBuilder extension (top-level)
cascades:                              # AutoBuilder extension (top-level)
  - reference: error-handling
---
```

### DD-2: SkillEntry Migration from Dataclass to Pydantic BaseModel

`SkillEntry` expands from a frozen dataclass (3 fields: `name`, `description`, `applies_to`) to a Pydantic `BaseModel` with `ConfigDict(frozen=True)`. New fields: `triggers`, `tags`, `priority`, `cascades`, `has_references`, `has_assets`, `has_scripts`, `path`.

**Rationale:** Pydantic provides validation, JSON serialization (for Redis cache), and lenient parsing (`model_config` with `extra="ignore"` for third-party skill tolerance). The frozen config maintains immutability. The existing `SkillContent` dataclass wrapping `SkillEntry + str` is preserved.

**Type locations:**
- `TriggerType` enum → `app/models/enums.py` (canonical enum location)
- `TriggerSpec`, `CascadeRef`, `SkillEntry` → `app/skills/library.py` (co-located with SkillLibrary)
- `SkillMatchContext`, `SkillContent` → `app/agents/protocols.py` (existing location, SkillMatchContext expanded)
- `LoadedSkillData` TypedDict → `app/agents/assembler.py` (near InstructionContext)
- `SkillCatalogEntry` → `app/gateway/models/skills.py` (gateway response model)

Import direction: `protocols.py` imports `SkillEntry` from `app.skills.library`. `library.py` does NOT import from `protocols.py`. No circular imports.

### DD-3: loaded_skills Type Change

Session state `loaded_skills` changes from `dict[str, str]` (name→content) to `dict[str, LoadedSkillData]` where `LoadedSkillData` is a TypedDict:

```python
class LoadedSkillData(TypedDict):
    content: str
    applies_to: list[str]        # empty = all agents
    matched_triggers: list[str]  # for observability (FR-6.37)
```

**Rationale:** The InstructionAssembler needs `applies_to` metadata to filter skills per agent (FR-6.27). The event stream needs `matched_triggers` for observability (FR-6.37). Carrying this alongside content in session state avoids a second lookup.

**Impact:** Breaking change to `InstructionContext.loaded_skills` type. All consumers (assembler SKILL fragment, context recreation, SkillLoaderAgent) updated together in P6.D5. Zero backwards-compat shims per engineering standards.

### DD-4: Description Keyword Fallback Strategy

Conservative matching for third-party skills without triggers: extract significant words from `description` (>4 chars, not in a stopword set), require ≥2 keywords to appear across `{deliverable_type, tags, file_patterns}` context strings.

**Rationale:** Single-keyword matching produces false positives (a skill mentioning "API" would match any API-related deliverable regardless of relevance). Requiring ≥2 keywords provides reasonable precision while keeping the fallback simple. Third-party skills that need precise matching can add triggers.

### DD-5: Gateway Skill Endpoints

Two operator-facing endpoints added (not in BOM as gateway routes; they implement S14 cache invalidation and FR-6.39 catalog inspection):
- `POST /skills/cache/invalidate` — triggers cache invalidation and rescan
- `GET /skills` — returns lightweight catalog (name + description for each indexed skill)

These are thin wrappers around `SkillLibrary` methods. No CRUD for individual skills — filesystem is the source of truth.

### DD-6: Role-Bound Skill Organization

Director and PM role-bound skills (S32) go under a new `app/skills/governance/` category with two skills:
- `director-oversight/SKILL.md` — `always` trigger, `applies_to: [director]`
- `pm-management/SKILL.md` — `always` trigger, `applies_to: [pm]`

**Rationale:** Top-level subdirectories are organizational conventions per architecture doc. A `governance/` category clearly communicates the supervisory nature of these skills. The structure doc's skill directory listing is illustrative, not exhaustive.

### DD-7: SkillLibrary Dependency Injection

`SkillLibrary` instance is created during gateway lifespan startup and stored on `app.state.skill_library`. A `get_skill_library` dependency is added to `app/gateway/deps.py`. Workers access it through the build functions (`build_work_session_agents`, etc.).

**Rationale:** Follows the existing pattern for Redis (`get_redis`) and DB session (`get_db_session`). Single instance per process, shared across requests/invocations.

## Deliverables

### P6.D1: Skill Types, Parser, and Validation
**Files:** `app/skills/__init__.py`, `app/skills/library.py` (types section), `app/skills/parser.py`, `app/models/enums.py`
**Depends on:** —
**Description:** Define the foundational types for the skill system: `TriggerType` enum in enums.py; `TriggerSpec`, `CascadeRef`, and expanded `SkillEntry` Pydantic models in library.py; `SkillMatchContext` expansion (add `requested_skills`) in protocols.py. Implement the frontmatter parser that extracts YAML from SKILL.md files with lenient parsing for third-party skills. Implement the validation function (`validate_skill_frontmatter`) callable by agents before writing skill files. Create the `app/skills/__init__.py` package init with public re-exports.
**BOM Components:** *(checked off during build when implemented)*
- [x] `S01` — `SkillEntry` Pydantic model
- [x] `S03` — Frontmatter parser (YAML from markdown)
- [x] `S17` — Skill validation function (callable by agents and indexer)
**Requirements:**
- [x] `TriggerType` enum defined in `app/models/enums.py` with values: `DELIVERABLE_TYPE`, `FILE_PATTERN`, `TAG_MATCH`, `EXPLICIT`, `ALWAYS`
- [x] `SkillEntry` is a Pydantic `BaseModel` with `ConfigDict(frozen=True)` containing: `name` (str, required), `description` (str), `triggers` (list[TriggerSpec]), `tags` (list[str]), `applies_to` (list[str]), `priority` (int, default 0), `cascades` (list[CascadeRef]), `has_references` (bool), `has_assets` (bool), `has_scripts` (bool), `path` (Path | None)
- [x] `TriggerSpec` model has `trigger_type: TriggerType` and `value: str` fields
- [x] `parse_skill_frontmatter(file_path: Path) -> SkillEntry | None` extracts YAML between `---` delimiters, returns `SkillEntry` on success, `None` on failure with warning log
- [x] Parser is lenient: unknown frontmatter fields are ignored (Pydantic `extra="ignore"`), non-standard metadata tolerated (FR-6.17)
- [x] Parser is strict on required fields: missing `name` or `description` → returns None with warning (FR-6.03)
- [x] `validate_skill_frontmatter(frontmatter: dict[str, object]) -> list[str]` returns list of error strings (empty = valid) — callable by agents (FR-6.52)
- [x] Frontmatter parsing is lenient for third-party skills (unknown fields ignored, non-standard metadata tolerated) but strict on required fields (`name`, `description`) (NFR-6.05)
- [x] `SkillMatchContext` in `protocols.py` gains `requested_skills: list[str]` field
- [x] `app/skills/__init__.py` exists and re-exports `SkillEntry`, `SkillLibrary` (forward ref), parser functions
- [x] No new external dependencies introduced — uses filesystem, Redis (existing), and PyYAML (existing transitive dependency) only (NFR-6.04)
- [x] All types pass pyright strict
**Validation:**
- `uv run pyright app/skills/ app/agents/protocols.py app/models/enums.py`
- `uv run pytest tests/skills/test_parser.py -v`

---

### P6.D2: Trigger Matchers
**Files:** `app/skills/matchers.py`
**Depends on:** P6.D1
**Description:** Implement the five trigger matcher strategies plus the description keyword fallback for third-party skill interoperability. Each matcher evaluates a single `TriggerSpec` against a `SkillMatchContext`. The `match_triggers` orchestrator function evaluates all triggers on a skill entry with OR logic and returns match status. The `DescriptionKeywordMatcher` provides conservative fallback matching for skills without triggers.
**BOM Components:**
- [x] `S04` — `deliverable_type` trigger matcher
- [x] `S05` — `file_pattern` trigger matcher (glob)
- [x] `S06` — `tag_match` trigger matcher (set intersection)
- [x] `S07` — `explicit` trigger matcher
- [x] `S08` — `always` trigger matcher
- [x] `S09` — Description keyword fallback (interop)
**Requirements:**
- [x] `deliverable_type` matcher: exact string match between trigger value and `context.deliverable_type` (FR-6.07)
- [x] `file_pattern` matcher: glob match using `fnmatch` — trigger pattern tested against each file in `context.file_patterns`; match if any file matches (FR-6.08)
- [x] `tag_match` matcher: set intersection between skill's `tags` and `context.tags`; match if any overlap (FR-6.09)
- [x] `explicit` matcher: skill's `name` checked against `context.requested_skills`; match if present (FR-6.10)
- [x] `always` matcher: unconditional match, always returns True (FR-6.11)
- [x] `match_triggers(entry: SkillEntry, context: SkillMatchContext) -> list[str]` returns list of matched trigger type names (empty = no match). OR logic: any single trigger match is sufficient (FR-6.12)
- [x] `DescriptionKeywordMatcher.matches_description(description, context) -> bool`: extracts significant words (>4 chars, not stopwords), requires ≥2 to appear across context strings (FR-6.15, FR-6.16)
- [x] Keyword fallback is used ONLY when skill has no triggers defined (FR-6.15)
**Validation:**
- `uv run pyright app/skills/matchers.py`
- `uv run pytest tests/skills/test_matchers.py -v`

---

### P6.D3: SkillLibrary Core
**Files:** `app/skills/library.py` (SkillLibrary class)
**Depends on:** P6.D1, P6.D2
**Description:** Implement the `SkillLibrary` class: recursive filesystem scanning to build an in-memory index, two-tier scan (global first, project-local overrides by name), deterministic trigger matching via matchers, full body loading from disk, and transitive cascade resolution with cycle detection. The library implements the `SkillLibraryProtocol` structurally (duck typing). Index keyed by skill `name`.
**BOM Components:**
- [x] `S02` — `SkillLibrary` class
- [x] `S10` — Two-tier scan (global + project-local override)
- [x] `S15` — Skill cascade resolution
- [x] `S20` — `app/skills/` directory structure
- [x] `S21` — `.agents/skills/` project-local directory support
**Requirements:**
- [x] `SkillLibrary.__init__(global_dir: Path, project_dir: Path | None = None, redis: ArqRedis | None = None)` — stores configuration, does not scan on init
- [x] `scan()` recursively finds all `SKILL.md` files in configured directories, parses frontmatter via `parse_skill_frontmatter`, builds `_index: dict[str, SkillEntry]` (FR-6.01)
- [x] Scan order: global directory first, then project-local directory. Project-local entries overwrite global entries with same name (FR-6.18, FR-6.21)
- [x] Duplicate names within same scan scope: first found wins, warning logged (FR-6.06)
- [x] Name vs directory mismatch: warning logged, frontmatter `name` used (FR-6.04)
- [x] `references/`, `assets/`, and `scripts/` subdirectory existence recorded in `SkillEntry.has_references` / `has_assets` / `has_scripts` (FR-6.05). Agents access scripts via file tools (`file_read`, `bash_exec`) — no automatic execution
- [x] Project-local override logged: skill name, which scope won (FR-6.21)
- [x] No project-local directory configured: operates with global skills only, no errors (FR-6.20)
- [x] `match(context: SkillMatchContext) -> list[SkillEntry]` evaluates all indexed skills against context using trigger matchers; skills without triggers use description keyword fallback; results sorted by priority desc then name asc (FR-6.13)
- [x] When no skills match: returns empty list (pipeline continues normally per FR-6.14)
- [x] Project-local skills with unique names (not present in global set) are added to the index alongside global skills (FR-6.19)
- [x] `load(entry: SkillEntry) -> SkillContent` reads full markdown body (below frontmatter) from `entry.path`; logs warning if body exceeds 3000 words recommending content be moved to `references/` (NFR-6.03)
- [x] `resolve_cascades(entries: list[SkillEntry]) -> list[SkillEntry]` transitively resolves cascade references via visited-name tracking (FR-6.22, FR-6.23)
- [x] Circular cascade references detected and broken with warning log (FR-6.24)
- [x] Missing cascade references: warning logged, resolution continues (FR-6.25)
- [x] Cascaded skills respect two-tier override (FR-6.26)
- [x] `get_index() -> dict[str, SkillEntry]` returns full index for inspection (FR-6.39)
- [x] Library structurally implements `SkillLibraryProtocol` (match + load signatures compatible)
- [x] Full filesystem scan + frontmatter parsing completes in under 2 seconds for 100 skills (NFR-6.01)
- [x] Trigger matching against the full index completes in under 10 milliseconds per context — O(n) in indexed skills with constant-time per-trigger evaluation (NFR-6.02)
**Validation:**
- `uv run pyright app/skills/library.py`
- `uv run pytest tests/skills/test_library.py -v`

---

### P6.D4: Skill Index Redis Cache
**Files:** `app/skills/library.py` (cache methods on SkillLibrary)
**Depends on:** P6.D3
**Description:** Add Redis caching to the SkillLibrary: serialize/deserialize the in-memory index to/from Redis, implement atomic invalidation, and add periodic mtime-based change detection. Cache is optional — library operates without Redis (filesystem-only mode). Cache key format: `autobuilder:skill_index:{scope_hash}` where scope_hash encodes the global+project directory combination.
**BOM Components:**
- [x] `S13` — Skill index Redis cache
- [x] `S14` — Skill cache invalidation (file change + gateway API)
- [x] `M21` — Skill index cache (long TTL)
**Requirements:**
- [x] `save_to_cache()` serializes the index to Redis as JSON (Path→string conversion). Atomic: old index serves until new SET completes (FR-6.31, NFR-6.06)
- [x] `load_from_cache() -> bool` deserializes index from Redis. Returns True on cache hit, False on miss (FR-6.31)
- [x] `invalidate_cache()` deletes the cached index key. Next access triggers filesystem rescan (FR-6.33)
- [x] Cache unavailable or expired: falls back to filesystem scan, no error (FR-6.34)
- [x] `check_for_changes() -> bool` compares cached file modification timestamps against current disk state; returns True if changes detected (FR-6.32)
- [x] When changes detected, cache is invalidated and rebuilt (FR-6.32)
- [x] Cache key uses deterministic hash of configured directory paths
- [x] Redis is optional: `redis=None` → cache methods are no-ops, library works filesystem-only
- [x] All cache operations are async
**Validation:**
- `uv run pyright app/skills/library.py`
- `uv run pytest tests/skills/test_cache.py -v`

---

### P6.D5: Pipeline Integration — SkillLoaderAgent Update and InstructionAssembler Filtering
**Files:** `app/agents/custom/skill_loader.py`, `app/agents/assembler.py`, `app/agents/protocols.py`
**Depends on:** P6.D3
**Description:** Update the SkillLoaderAgent to call `resolve_cascades()` after matching and write `LoadedSkillData` (with `applies_to` and `matched_triggers` metadata) to session state. Update the InstructionAssembler SKILL fragment to filter `loaded_skills` by `applies_to` per agent — only skills where `applies_to` is empty or contains the current agent name are included. Update `InstructionContext.loaded_skills` type from `dict[str, str]` to `dict[str, LoadedSkillData]`. Update `NullSkillLibrary` for type compatibility. Publish skill loading events to event stream via existing state_delta event mechanism.
**BOM Components:**
- [x] `S12` — `InstructionAssembler` skill injection with `applies_to` filtering
**Requirements:**
- [x] `SkillLoaderAgent._run_async_impl` calls `library.resolve_cascades(matched)` after initial `match()` (FR-6.22)
- [x] SkillLoaderAgent writes `loaded_skills: dict[str, LoadedSkillData]` to state with `content`, `applies_to`, and `matched_triggers` per skill (FR-6.35, FR-6.36, FR-6.37)
- [x] SkillLoaderAgent writes `loaded_skill_names: list[str]` to state (FR-6.35)
- [x] When no skills match, SkillLoaderAgent emits `loaded_skill_names: []` and `loaded_skills: {}` — pipeline continues normally (FR-6.14); a warning event is published to the event stream identifying the deliverable and context that produced no matches (FR-6.38)
- [x] `InstructionContext.loaded_skills` type changed to `dict[str, LoadedSkillData]`
- [x] `LoadedSkillData` TypedDict defined with `content: str`, `applies_to: list[str]`, `matched_triggers: list[str]`
- [x] InstructionAssembler SKILL fragment: for each skill in `ctx.loaded_skills`, include only if `applies_to` is empty OR contains `ctx.agent_name` (FR-6.27, FR-6.28)
- [x] Included skills appear in assembled instructions in the order returned by `SkillLibrary.match()` (priority desc, name asc — sorting is performed at match time, assembler preserves order) (FR-6.29)
- [x] Curly braces in skill content that are not state template references are escaped (FR-6.30)
- [x] `NullSkillLibrary.load()` returns `SkillContent` compatible with expanded `SkillEntry`
- [x] Skill loading event published to event stream via existing state_delta mechanism — the state_delta containing `loaded_skills` flows through EventPublisher naturally (FR-6.37, FR-6.38)
- [x] Existing tests updated for type changes; new tests for applies_to filtering
**Validation:**
- `uv run pyright app/agents/assembler.py app/agents/custom/skill_loader.py app/agents/protocols.py`
- `uv run pytest tests/agents/test_assembler.py tests/agents/custom/test_skill_loader.py -v`

---

### P6.D6: Build-Time Skill Resolution and Gateway Endpoints
**Files:** `app/workers/adk.py`, `app/gateway/routes/skills.py`, `app/gateway/models/skills.py`, `app/gateway/deps.py`, `app/gateway/main.py`
**Depends on:** P6.D3, P6.D4, P6.D5
**Description:** Add Director and PM skill resolution at agent build time. When the Director is constructed (in `build_chat_session_agent`, `build_work_session_agents`, `run_director_turn`), call `skill_library.match()` with a Director-specific context and create a Director-specific `InstructionContext`. Separately, when PM is constructed, resolve PM-specific skills. Each tier gets independently resolved skills baked into instructions at construction time. Add gateway skill endpoints: `POST /skills/cache/invalidate` and `GET /skills` for operator use. Add `get_skill_library` dependency. Wire SkillLibrary creation into gateway lifespan.
**BOM Components:**
- [x] `S16` — Supervision-tier skill resolution (Director/PM build-time matching)
**Requirements:**
- [x] `build_chat_session_agent()` accepts `skill_library` parameter; resolves Director skills via `skill_library.match(SkillMatchContext(agent_role="director"))` and creates Director-specific `InstructionContext` with resolved skills (FR-6.46)
- [x] `build_work_session_agents()` resolves Director and PM skills independently — separate `SkillMatchContext` per tier, separate `InstructionContext` per agent (FR-6.46, FR-6.47, FR-6.48)
- [x] `run_director_turn()` resolves Director skills at build time (FR-6.46, FR-6.49)
- [x] Skills with `always` trigger + `applies_to: [director]` load for every Director invocation regardless of session type (FR-6.49)
- [x] Skills with `always` trigger + no `applies_to` load for ALL agents across all tiers (FR-6.50)
- [x] `SkillCatalogEntry` Pydantic model defined in `app/gateway/models/skills.py` with: name, description, triggers, tags, applies_to, priority, has_references, has_assets, has_scripts
- [x] `POST /skills/cache/invalidate` triggers `skill_library.invalidate_cache()` and returns acknowledgment (FR-6.33)
- [x] `GET /skills` returns `list[SkillCatalogEntry]` from `skill_library.get_index()` (FR-6.39)
- [x] `get_skill_library` dependency added to `app/gateway/deps.py` reading from `app.state.skill_library`
- [x] Skills router registered in `app/gateway/main.py`
- [x] Gateway lifespan creates `SkillLibrary` instance, calls `scan()`, stores on `app.state`
**Validation:**
- `uv run pyright app/workers/adk.py app/gateway/routes/skills.py app/gateway/models/skills.py`
- `uv run pytest tests/workers/test_adk.py tests/gateway/routes/test_skills.py -v`

---

### P6.D7: Initial Skill Library — Domain Skills
**Files:** `app/skills/code/api-endpoint/SKILL.md`, `app/skills/code/data-model/SKILL.md`, `app/skills/code/database-migration/SKILL.md`, `app/skills/review/security-review/SKILL.md`, `app/skills/review/performance-review/SKILL.md`, `app/skills/test/unit-test-patterns/SKILL.md`, `app/skills/planning/task-decomposition/SKILL.md`
**Depends on:** P6.D1
**Description:** Author 7 domain skills covering common development patterns. Each skill follows the Agent Skills open standard: SKILL.md with YAML frontmatter in a named directory. Skills have AutoBuilder trigger declarations for precise matching. Writing style is imperative/instructional. Body content under 3000 words with detailed content in `references/` where needed. Descriptions written in third-person with specific trigger phrases. Remove `.gitkeep` files from existing directories.
**BOM Components:**
- [x] `S22` — Skill: `code/api-endpoint`
- [x] `S23` — Skill: `code/data-model`
- [x] `S24` — Skill: `code/database-migration`
- [x] `S25` — Skill: `review/security-review`
- [x] `S26` — Skill: `review/performance-review`
- [x] `S27` — Skill: `test/unit-test-patterns`
- [x] `S28` — Skill: `planning/task-decomposition`
**Requirements:**
- [x] Each skill has a named directory containing `SKILL.md` per Agent Skills standard (FR-6.42)
- [x] Each skill's frontmatter contains `name` and `description` (required), plus `triggers`, `tags`, `applies_to`, `priority` as appropriate (FR-6.42)
- [x] `api-endpoint` skill: triggers on `deliverable_type: api_endpoint` and `file_pattern: "*/routes/*.py"`, applies_to includes `coder` and `reviewer`
- [x] `data-model` skill: triggers on `deliverable_type: data_model` and `file_pattern: "*/models/*.py"`, applies_to includes `coder` and `reviewer`
- [x] `database-migration` skill: triggers on `deliverable_type: migration` and `file_pattern: "*/migrations/*.py"`, applies_to includes `coder`
- [x] `security-review` skill: triggers on `tag_match` with security-related tags, applies_to `reviewer`
- [x] `performance-review` skill: triggers on `tag_match` with performance-related tags, applies_to `reviewer`
- [x] `unit-test-patterns` skill: triggers on `deliverable_type: test` and `file_pattern: "*/tests/*.py"`, applies_to `coder`
- [x] `task-decomposition` skill: `always` trigger, applies_to `planner`
- [x] All descriptions written in third-person (FR-6.43)
- [x] All body content in imperative/instructional style (FR-6.43)
- [x] Body content under 3000 words per skill (NFR-6.03)
- [x] `.gitkeep` files removed from `app/skills/code/`, `app/skills/review/`, `app/skills/test/`, `app/skills/planning/`
- [x] All skills pass `validate_skill_frontmatter()` validation
**Validation:**
- `uv run pytest tests/skills/test_skill_files.py -v` (validates all shipped skills have valid frontmatter)

---

### P6.D8: Initial Skill Library — Authoring Skills
**Files:** `app/skills/authoring/skill-authoring/SKILL.md`, `app/skills/authoring/skill-authoring/references/skill-template.md`, `app/skills/authoring/agent-definition/SKILL.md`, `app/skills/authoring/workflow-authoring/SKILL.md`, `app/skills/authoring/project-conventions/SKILL.md`
**Depends on:** P6.D1
**Description:** Author 4 authoring skills that teach agents how to create system artifacts. The skill-authoring skill is the most detailed — it includes a validation checklist and a `references/skill-template.md` with all supported frontmatter fields annotated. The agent-definition skill teaches agent definition file authoring. The workflow-authoring skill teaches WORKFLOW.yaml manifest creation. The project-conventions skill teaches project-level override configuration. These skills enable autonomous skill creation (CAP-11).
**BOM Components:**
- [x] `S33` — Skill: `authoring/skill-authoring` (+ `references/skill-template.md`)
- [x] `S34` — Skill: `authoring/agent-definition`
- [x] `S35` — Skill: `authoring/workflow-authoring`
- [x] `S36` — Skill: `authoring/project-conventions`
**Requirements:**
- [x] Each skill has a named directory containing `SKILL.md` per Agent Skills standard (FR-6.42)
- [x] `skill-authoring` includes validation checklist covering: frontmatter structure, required fields, trigger design, progressive disclosure, writing style, resource referencing (FR-6.44)
- [x] `skill-authoring` includes `references/skill-template.md` with all supported frontmatter fields annotated (FR-6.45)
- [x] `skill-authoring` provides sufficient guidance for an agent to produce a valid SKILL.md file (FR-6.53)
- [x] `agent-definition` covers: markdown + YAML frontmatter format, 3-scope cascade, metadata fields, body writing conventions
- [x] `workflow-authoring` covers: WORKFLOW.yaml manifest schema, pipeline.py interface contract, agents/ and skills/ subdirectories
- [x] `project-conventions` covers: `.agents/` directory structure, project-scope agent overrides, project-local skills, configuration patterns
- [x] All authoring skills use `always` trigger with appropriate `applies_to` fields (e.g., `applies_to: [coder, planner]` or all agents)
- [x] All skills pass `validate_skill_frontmatter()` validation
**Validation:**
- `uv run pytest tests/skills/test_skill_files.py -v`

---

### P6.D9: Director/PM Role-Bound Skills
**Files:** `app/skills/governance/director-oversight/SKILL.md`, `app/skills/governance/pm-management/SKILL.md`
**Depends on:** P6.D1
**Description:** Author 2 role-bound supervision skills using `always` trigger + `applies_to`. The Director oversight skill covers governance responsibilities, brief-shaping, CEO communication patterns, and operational identity. The PM management skill covers project orchestration, batch management, quality gates, and escalation patterns. These skills demonstrate the Layer 1 role-bound loading model and ensure supervision agents get contextual knowledge on every invocation.
**BOM Components:**
- [x] `S32` — Director/PM role-bound skills (governance, oversight, management)
**Requirements:**
- [x] `director-oversight` skill: `always` trigger, `applies_to: [director]`, high priority (FR-6.49)
- [x] `director-oversight` content covers: governance responsibilities, formation/brief-shaping guidance, CEO queue communication patterns, cross-project oversight principles
- [x] `pm-management` skill: `always` trigger, `applies_to: [pm]`, high priority
- [x] `pm-management` content covers: batch management strategy, deliverable lifecycle, quality gate enforcement, escalation decision framework, inter-batch reasoning
- [x] Both skills load for every invocation of their respective agents — Director and PM do NOT receive each other's role-bound skills (FR-6.48)
- [x] Both skills pass `validate_skill_frontmatter()` validation
**Validation:**
- `uv run pytest tests/skills/test_skill_files.py -v`

---

### P6.D10: File-Editing Skills
**Files:** `app/skills/files/docx/SKILL.md`, `app/skills/files/docx/scripts/`, `app/skills/files/xlsx/SKILL.md`, `app/skills/files/xlsx/scripts/`, `app/skills/files/pptx/SKILL.md`, `app/skills/files/pptx/editing.md`, `app/skills/files/pptx/pptxgenjs.md`, `app/skills/files/pptx/scripts/`, `app/skills/files/pdf/SKILL.md`, `app/skills/files/pdf/forms.md`, `app/skills/files/pdf/reference.md`, `app/skills/files/pdf/scripts/`
**Depends on:** P6.D1
**Description:** Ship 4 file-editing skills. Original skill content (body, scripts, references) is preserved. AutoBuilder trigger declarations are added to each skill's frontmatter so they match via the deterministic trigger system — not the keyword fallback. Each skill includes a `scripts/` directory with Python helper scripts that agents invoke via `bash_exec` / file tools. The skills share an `office/` scripts subdirectory (pack, unpack, validate, soffice wrappers). Placed under a new `app/skills/files/` category.
**BOM Components:**
- [x] *(no BOM component — additive to FR-6.40 initial library scope)*
**Requirements:**
- [x] `docx` skill copied with SKILL.md + `scripts/` directory (includes `accept_changes.py`, `comment.py`, `office/` shared scripts, `templates/`); AutoBuilder triggers added: `file_pattern: "*.docx"`, `file_pattern: "*.doc"`, tags: `[document, word, docx]`, applies_to: `[coder]`
- [x] `xlsx` skill copied with SKILL.md + `scripts/` directory (includes `recalc.py`, `office/` shared scripts); AutoBuilder triggers added: `file_pattern: "*.xlsx"`, `file_pattern: "*.xls"`, `file_pattern: "*.csv"`, tags: `[spreadsheet, excel, xlsx]`, applies_to: `[coder]`
- [x] `pptx` skill copied with SKILL.md + `references/editing.md` + `references/pptxgenjs.md` + `scripts/` directory (includes `add_slide.py`, `clean.py`, `thumbnail.py`, `office/` shared scripts); AutoBuilder triggers added: `file_pattern: "*.pptx"`, `file_pattern: "*.ppt"`, tags: `[presentation, powerpoint, pptx]`, applies_to: `[coder]`
- [x] `pdf` skill copied with SKILL.md + `references/forms.md` + `references/reference.md` + `scripts/` directory (includes form-filling, validation, and conversion scripts); AutoBuilder triggers added: `file_pattern: "*.pdf"`, tags: `[pdf, document]`, applies_to: `[coder]`
- [x] Each skill's SKILL.md has valid frontmatter with `name`, `description`, and AutoBuilder trigger declarations — passes `validate_skill_frontmatter()`
- [x] Skills match via deterministic file_pattern and tag_match triggers (not keyword fallback)
- [x] `SkillEntry.has_scripts` is True for all 4 skills after indexing
- [x] `SkillEntry.has_references` is True for pptx and pdf (which have `references/` subdirectories with additional .md files)
- [x] ~~LICENSE.txt preserved in each skill directory~~ — removed per user directive (Claude products, license not applicable)
- [x] All skills indexed successfully by `SkillLibrary.scan()`
**Validation:**
- `uv run pytest tests/skills/test_skill_files.py -v`

---

## Build Order

```
Batch 1 (sequential): P6.D1
  D1: Skill types, parser, validation — app/skills/library.py (types), parser.py, app/models/enums.py

Batch 2 (parallel): P6.D2, P6.D7, P6.D8, P6.D9, P6.D10
  D2: Trigger matchers — app/skills/matchers.py; depends D1
  D7: Domain skills (7 files) — app/skills/{code,review,test,planning}/*/SKILL.md; depends D1 (format)
  D8: Authoring skills (4 files + references) — app/skills/authoring/*/SKILL.md; depends D1 (format)
  D9: Role-bound skills (2 files) — app/skills/governance/*/SKILL.md; depends D1 (format)
  D10: File-editing skills app/skills/files/*/; depends D1 (format)

Batch 3 (sequential): P6.D3
  D3: SkillLibrary core — app/skills/library.py (class); depends D1, D2

Batch 4 (parallel): P6.D4, P6.D5
  D4: Redis cache — app/skills/library.py (cache methods); depends D3
  D5: Pipeline integration — assembler.py, skill_loader.py, protocols.py; depends D3

Batch 5 (sequential): P6.D6
  D6: Build-time resolution + gateway — adk.py, routes/skills.py, deps.py, main.py; depends D3, D4, D5
```

## Completion Contract Traceability

### FRD Coverage

| Capability | FRD Requirement | Deliverable(s) |
|---|---|---|
| CAP-1: Skill File Discovery and Indexing | FR-6.01 | P6.D3 |
| *(same)* | FR-6.02 | P6.D1, P6.D3 |
| *(same)* | FR-6.03 | P6.D1 |
| *(same)* | FR-6.04 | P6.D3 |
| *(same)* | FR-6.05 | P6.D1, P6.D3 |
| *(same)* | FR-6.06 | P6.D3 |
| CAP-2: Context-Aware Trigger Matching | FR-6.07 | P6.D2 |
| *(same)* | FR-6.08 | P6.D2 |
| *(same)* | FR-6.09 | P6.D2 |
| *(same)* | FR-6.10 | P6.D2 |
| *(same)* | FR-6.11 | P6.D2 |
| *(same)* | FR-6.12 | P6.D2 |
| *(same)* | FR-6.13 | P6.D3 |
| *(same)* | FR-6.14 | P6.D3, P6.D5 |
| CAP-3: Third-Party Skill Interoperability | FR-6.15 | P6.D2 |
| *(same)* | FR-6.16 | P6.D2 |
| *(same)* | FR-6.17 | P6.D1 |
| CAP-4: Two-Tier Override | FR-6.18 | P6.D3 |
| *(same)* | FR-6.19 | P6.D3 |
| *(same)* | FR-6.20 | P6.D3 |
| *(same)* | FR-6.21 | P6.D3 |
| CAP-5: Skill Cascade Resolution | FR-6.22 | P6.D3, P6.D5 |
| *(same)* | FR-6.23 | P6.D3 |
| *(same)* | FR-6.24 | P6.D3 |
| *(same)* | FR-6.25 | P6.D3 |
| *(same)* | FR-6.26 | P6.D3 |
| CAP-6: Agent-Filtered Skill Injection | FR-6.27 | P6.D5 |
| *(same)* | FR-6.28 | P6.D5 |
| *(same)* | FR-6.29 | P6.D5 |
| *(same)* | FR-6.30 | P6.D5 |
| CAP-7: Skill Index Caching | FR-6.31 | P6.D4 |
| *(same)* | FR-6.32 | P6.D4 |
| *(same)* | FR-6.33 | P6.D4, P6.D6 |
| *(same)* | FR-6.34 | P6.D4 |
| CAP-8: Observability | FR-6.35 | P6.D5 |
| *(same)* | FR-6.36 | P6.D5 |
| *(same)* | FR-6.37 | P6.D5 |
| *(same)* | FR-6.38 | P6.D5 |
| *(same)* | FR-6.39 | P6.D6 |
| CAP-9: Initial Skill Library | FR-6.40 | P6.D7, P6.D10 |
| *(same)* | FR-6.41 | P6.D8 |
| *(same)* | FR-6.42 | P6.D7, P6.D8, P6.D10 |
| *(same)* | FR-6.43 | P6.D7, P6.D8 |
| *(same)* | FR-6.44 | P6.D8 |
| *(same)* | FR-6.45 | P6.D8 |
| CAP-10: Supervision-Tier Skill Resolution | FR-6.46 | P6.D6 |
| *(same)* | FR-6.47 | P6.D6 |
| *(same)* | FR-6.48 | P6.D6 |
| *(same)* | FR-6.49 | P6.D6, P6.D9 |
| *(same)* | FR-6.50 | P6.D6 |
| CAP-11: Autonomous Skill Creation | FR-6.51 | P6.D4 |
| *(same)* | FR-6.52 | P6.D1 |
| *(same)* | FR-6.53 | P6.D8 |
| *(same)* | FR-6.54 | P6.D4 |
| *(same)* | FR-6.55 | P6.D3 |
| Non-Functional Requirements | NFR-6.01 | P6.D3 |
| *(same)* | NFR-6.02 | P6.D3 |
| *(same)* | NFR-6.03 | P6.D3, P6.D7, P6.D8 |
| *(same)* | NFR-6.04 | P6.D1 |
| *(same)* | NFR-6.05 | P6.D1 |
| *(same)* | NFR-6.06 | P6.D4 |

### BOM Coverage

| BOM ID | Component | Deliverable |
|---|---|---|
| S01 | `SkillEntry` Pydantic model | P6.D1 |
| S02 | `SkillLibrary` class | P6.D3 |
| S03 | Frontmatter parser (YAML from markdown) | P6.D1 |
| S04 | `deliverable_type` trigger matcher | P6.D2 |
| S05 | `file_pattern` trigger matcher (glob) | P6.D2 |
| S06 | `tag_match` trigger matcher (set intersection) | P6.D2 |
| S07 | `explicit` trigger matcher | P6.D2 |
| S08 | `always` trigger matcher | P6.D2 |
| S09 | Description keyword fallback (interop) | P6.D2 |
| S10 | Two-tier scan (global + project-local override) | P6.D3 |
| S12 | `InstructionAssembler` skill injection with `applies_to` filtering | P6.D5 |
| S13 | Skill index Redis cache | P6.D4 |
| S14 | Skill cache invalidation (file change + gateway API) | P6.D4 |
| S15 | Skill cascade resolution | P6.D3 |
| S16 | Supervision-tier skill resolution (Director/PM build-time matching) | P6.D6 |
| S17 | Skill validation function (callable by agents and indexer) | P6.D1 |
| S20 | `app/skills/` directory structure | P6.D3 |
| S21 | `.agents/skills/` project-local directory | P6.D3 |
| S22 | Skill: `code/api-endpoint` | P6.D7 |
| S23 | Skill: `code/data-model` | P6.D7 |
| S24 | Skill: `code/database-migration` | P6.D7 |
| S25 | Skill: `review/security-review` | P6.D7 |
| S26 | Skill: `review/performance-review` | P6.D7 |
| S27 | Skill: `test/unit-test-patterns` | P6.D7 |
| S28 | Skill: `planning/task-decomposition` | P6.D7 |
| S32 | Director/PM role-bound skills (governance, oversight, management) | P6.D9 |
| S33 | Skill: `authoring/skill-authoring` (+ `references/skill-template.md`) | P6.D8 |
| S34 | Skill: `authoring/agent-definition` | P6.D8 |
| S35 | Skill: `authoring/workflow-authoring` | P6.D8 |
| S36 | Skill: `authoring/project-conventions` | P6.D8 |
| M21 | Skill index cache (long TTL) | P6.D4 |

### Contract Coverage

| # | Roadmap Completion Contract Item | Covered By | Validation |
|---|---|---|---|
| 1 | `SkillLoaderAgent` loads relevant skills for a given deliverable context | P6.D2, P6.D3, P6.D5 | `uv run pytest tests/agents/custom/test_skill_loader.py tests/skills/test_library.py -v` |
| 2 | Skills appear in unified event stream | P6.D5 | `uv run pytest tests/agents/custom/test_skill_loader.py -v -k event` |
| 3 | `loaded_skill_names` in state shows exactly which skills loaded | P6.D5 | `uv run pytest tests/agents/custom/test_skill_loader.py -v -k loaded_skill_names` |
| 4 | Project-local skills override globals with same name | P6.D3 | `uv run pytest tests/skills/test_library.py -v -k override` |
| 5 | Director and PM receive independently resolved skills at build time (not pipeline runtime) | P6.D6 | `uv run pytest tests/workers/test_adk.py -v -k skill` |
| 6 | `applies_to` filtering delivers per-agent skill content in assembled instructions | P6.D5 | `uv run pytest tests/agents/test_assembler.py -v -k applies_to` |
| 7 | Agents can create valid skill files; new skills indexed on cache rebuild | P6.D1, P6.D4, P6.D8 | `uv run pytest tests/skills/test_parser.py -v -k validate` |
| 8 | ~320 lines core implementation (skill content and tests additional) | All code deliverables | `find app/skills -name '*.py' -exec cat {} + \| wc -l` |

## Research Notes

### Existing Interface Signatures (Phase 5a/5b)

**SkillLibraryProtocol** (`app/agents/protocols.py`):
```python
class SkillLibraryProtocol(Protocol):
    def match(self, context: SkillMatchContext) -> list[SkillEntry]: ...
    def load(self, entry: SkillEntry) -> SkillContent: ...
```

**Current SkillEntry** (frozen dataclass, 3 fields):
```python
@dataclass(frozen=True)
class SkillEntry:
    name: str
    description: str = ""
    applies_to: list[str] = field(default_factory=lambda: list[str]())
```

**Current InstructionContext.loaded_skills**: `dict[str, str]`

**SkillLoaderAgent constructor**: `skill_library: object = NullSkillLibrary()` (passed as override kwarg via `AgentRegistry.build()`)

### YAML Frontmatter Parsing

Python stdlib `yaml` module (PyYAML) handles YAML parsing. The frontmatter is extracted by splitting on `---` delimiters. Pattern:
```python
import yaml
parts = content.split("---", 2)  # [before, frontmatter, body]
metadata = yaml.safe_load(parts[1])
body = parts[2] if len(parts) > 2 else ""
```

PyYAML is already a transitive dependency via multiple packages. No new dependency needed (NFR-6.04). Verify with `uv run python -c "import yaml"`.

### Redis Cache Key Pattern

Existing Redis key patterns in AutoBuilder use `autobuilder:` prefix (e.g., `autobuilder:stream:workflow:{id}`). Skill cache key follows: `autobuilder:skill_index:{scope_hash}`. The scope_hash is a short hash of `f"{global_dir}:{project_dir or ''}"`.

### InstructionAssembler Brace Escaping

The assembler already escapes `{` and `}` in PROJECT and SKILL fragments to prevent ADK state template injection. Pattern: `content.replace("{", "{{").replace("}", "}}")` — but must NOT escape legitimate `{key}` template references. Current implementation escapes ALL braces. For skill content, this is correct: skill body content should not contain state template references (skill authors should use explicit text, not `{variable_name}` patterns).

### Context Recreation Compatibility

`loaded_skill_names` is already in `_CRITICAL_KEY_PREFIXES` and `STAGE_COMPLETION_KEYS` in `context_recreation.py`. The `loaded_skills` dict persists naturally as a session state key. The type change from `dict[str, str]` to `dict[str, LoadedSkillData]` is transparent to context recreation — it copies state values without type inspection.

### Build-Time Resolution Call Sites

Three functions in `app/workers/adk.py` need skill resolution:
1. `build_chat_session_agent()` — Director for chat sessions
2. `build_work_session_agents()` — Director + PM for work sessions
3. `run_director_turn()` — Director for queue processing

Each currently creates a single shared `InstructionContext`. Phase 6 splits this: each agent gets its own `InstructionContext` with independently resolved skills.

### Pipeline Stage Order (Unchanged)

```python
PIPELINE_STAGE_NAMES = [
    "skill_loader",      # ← Phase 6 fills this in
    "memory_loader",
    "planner",
    "coder",
    "formatter",
    "linter",
    "tester",
    "diagnostics",
    "review_cycle",
]
```

SkillLoaderAgent runs first, before any LLM agent. This is already wired from Phase 5a.
