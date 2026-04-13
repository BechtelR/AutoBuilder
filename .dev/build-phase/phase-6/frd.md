# Phase 6 FRD: Skills System
*Generated: 2026-03-11*

## Objective

Replace the NullSkillLibrary stub (Phase 5a forward-dependency contract) with a production skill loading system. After Phase 6, agents receive task-relevant domain knowledge — conventions, patterns, strategies, review checklists — automatically based on deliverable context instead of generic instructions for every task. Skills follow the Agent Skills open standard file format for cross-platform interoperability while using AutoBuilder's deterministic trigger matching for guaranteed knowledge injection. Agents and users can also create new skills autonomously, validated and indexed on creation. Traces to PR-31, PR-32, PR-33, PR-5a.

## Consumer Roles

| Role | Description | E2E Boundary |
|------|-------------|--------------|
| **Pipeline System** | The DeliverablePipeline that invokes SkillLoaderAgent as its first step before any LLM agent runs | Deliverable context in session state → relevant skills matched via deterministic triggers → skill content loaded into session state → downstream agents receive filtered skill content in their assembled instructions |
| **Skill Author** | Developer or agent creating SKILL.md files to encode domain knowledge, project conventions, or reusable patterns | Skill file written to disk (manually or via file tools) → system discovers, parses frontmatter, validates, and indexes → skill matches when relevant deliverable context appears → skill content appears in appropriate agent instructions |
| **Operator** | Developer inspecting, debugging, or managing skill behavior across projects | Can observe which skills loaded for any deliverable execution via session state and event stream, inspect the full skill index, verify matching behavior, trigger cache invalidation |
| **Gateway Caller** | API consumer managing skill index cache or inspecting indexed skills | API call triggers cache invalidation → next pipeline execution uses fresh index; API call returns indexed skill catalog for inspection |

## Appetite

**M (3-5 days)** — per roadmap. Core implementation ~335 lines. Most infrastructure (SkillLoaderAgent, InstructionAssembler SKILL integration, pipeline wiring, SkillLibraryProtocol) already exists from Phase 5a. Phase 6 fills in the real SkillLibrary, trigger matchers, initial skill content, and autonomous creation capability. The ~320 line estimate in the roadmap covers core library code; skill file content and tests are additional.

---

## Capabilities

### CAP-1: Skill File Discovery and Indexing

The system automatically discovers SKILL.md files by recursively scanning configured directories, parses YAML frontmatter from each file, validates required fields, and builds an in-memory index keyed by skill name. Malformed files (invalid YAML, missing required `name` field, unrecognized structure) are excluded from the index with a warning log — they do not cause the system to fail. The index contains only lightweight metadata (frontmatter fields); full skill body content is not loaded until a skill matches.

**Requirements:**

- [x] **FR-6.01**: When the system starts or the skill index is rebuilt, it recursively scans all configured skill directories for files named `SKILL.md`, parses their YAML frontmatter, and builds an in-memory index keyed by the `name` field.
- [x] **FR-6.02**: When a SKILL.md file has valid frontmatter containing at minimum a `name` and `description` field, the system indexes it with all parsed metadata (triggers, tags, applies_to, priority, cascades).
- [x] **FR-6.03**: When a SKILL.md file has invalid YAML frontmatter, is missing the required `name` field, or is missing the required `description` field, the system excludes it from the index and logs a warning identifying the file path and the validation failure.
- [x] **FR-6.04**: When a SKILL.md file's `name` value does not match the name of its parent directory, the system logs a warning but still indexes the skill using the frontmatter `name` value.
- [x] **FR-6.05**: When a skill directory contains a `references/`, `assets/`, or `scripts/` subdirectory, the system records their existence in the index but does not load their contents during indexing. Agents access scripts via file tools (`file_read`, `bash_exec`) — no automatic execution on skill load.
- [x] **FR-6.06**: When two SKILL.md files in the same scan scope have the same `name`, the system indexes only the first one found and logs a warning about the duplicate.

---

### CAP-2: Context-Aware Trigger Matching

Given a deliverable's execution context (type, target files, tags, explicitly requested skill names, agent role), the system deterministically matches relevant skills using structured trigger rules. No LLM call is involved in matching. A skill matches if ANY of its declared triggers match the current context (OR logic). Five trigger types are supported. When no skill matches for a deliverable, execution continues normally and a warning event is emitted to the event stream.

**Requirements:**

- [x] **FR-6.07**: When a skill declares a `deliverable_type` trigger and the current deliverable's type exactly matches the trigger value, the skill matches.
- [x] **FR-6.08**: When a skill declares a `file_pattern` trigger and any file in the deliverable's target file list matches the glob pattern, the skill matches.
- [x] **FR-6.09**: When a skill declares a `tag_match` trigger and any of the deliverable's tags intersect with the skill's `tags` list, the skill matches.
- [x] **FR-6.10**: When a skill declares an `explicit` trigger and the skill's name appears in the deliverable's `requested_skills` list (set via session state by PM, Director, or user), the skill matches.
- [x] **FR-6.11**: When a skill declares an `always` trigger, the skill matches unconditionally for every deliverable execution.
- [x] **FR-6.12**: When a skill declares multiple triggers, the skill matches if ANY single trigger matches (OR logic). All triggers need not be satisfied.
- [x] **FR-6.13**: When multiple skills match the same deliverable context, all matched skills are returned, sorted by their `priority` field (higher priority first, then alphabetically by name for equal priority).
- [x] **FR-6.14**: When no skills match a deliverable's context via trigger matching AND no mandatory skills were assigned (see CAP-10), the pipeline continues execution normally and a warning event is published to the event stream identifying the deliverable and context that produced no matches.

---

### CAP-3: Third-Party Skill Interoperability

Skills following the Agent Skills open standard that lack AutoBuilder-specific trigger declarations still work via a description keyword fallback. When a SKILL.md file has no triggers defined, the system extracts keywords from its `description` field and matches them against the deliverable's context strings. This ensures community-authored skills are usable without modification, though explicit triggers provide more precise matching.

**Requirements:**

- [x] **FR-6.15**: When a SKILL.md file has a valid `name` and `description` but no trigger declarations, the system falls back to matching keywords from the `description` field against the deliverable's type, tags, and file patterns.
- [x] **FR-6.16**: When a third-party skill's `description` contains keywords that match the current deliverable context via the fallback mechanism, the skill matches and loads identically to a trigger-matched skill.
- [x] **FR-6.17**: When a third-party skill has technically imperfect YAML frontmatter (e.g., extra unknown fields, non-standard metadata values), the system parses leniently — extracting known fields and ignoring unknown ones rather than rejecting the file.

---

### CAP-4: Two-Tier Override

Skills exist at two scopes: global (shipped with the platform) and project-local (in the user's repository). Project-local skills with the same name as a global skill replace the global skill entirely — no merging of content, triggers, or metadata. Project-local skills with unique names are additive. The scan order is deterministic: global first, project-local second (project-local overwrites).

**Requirements:**

- [x] **FR-6.18**: When both a global skill and a project-local skill exist with the same `name`, the project-local skill completely replaces the global skill in the index — the global skill's content, triggers, and metadata are not used.
- [x] **FR-6.19**: When a project-local skill has a unique `name` not present in the global skill set, it is added to the index alongside global skills.
- [x] **FR-6.20**: When no project-local skills directory exists or is configured, the system operates with global skills only and does not emit errors or warnings about the missing directory.
- [x] **FR-6.21**: When a project-local skill overrides a global skill, the override is logged (skill name, which scope won) for debugging purposes.

---

### CAP-5: Skill Cascade Resolution

Skills can declare dependencies on other skills via a `cascades` field. After primary trigger matching, the system transitively resolves all cascaded skill references — loading the cascaded skills alongside the directly-matched skills. Cascaded skills respect two-tier override rules and circular references are prevented.

**Requirements:**

- [x] **FR-6.22**: When a matched skill declares `cascades` referencing other skills by name, those cascaded skills are loaded alongside the directly-matched skills regardless of whether the cascaded skills' own triggers match the current context.
- [x] **FR-6.23**: When a cascaded skill itself declares further cascades, the system resolves them transitively (cascades of cascades) until no new skills are added.
- [x] **FR-6.24**: When cascade resolution encounters a circular reference (skill A cascades to B, B cascades to A), the system detects the cycle via visited-name tracking, breaks it, and logs a warning identifying the cycle chain.
- [x] **FR-6.25**: When a cascade references a skill name that does not exist in the index, the system logs a warning and continues — the missing cascade does not prevent other skills from loading.
- [x] **FR-6.26**: When a cascaded skill has both a global and project-local version, the project-local version is used (two-tier override applies to cascaded skills identically to directly-matched skills).

---

### CAP-6: Agent-Filtered Skill Injection

Not all agents need all skills. The `applies_to` field on each skill controls which agents in the pipeline receive that skill's content. The InstructionAssembler filters loaded skills per agent during instruction composition. Skills without an `applies_to` field are delivered to all agents. Skills are ordered by priority in the assembled instructions.

**Requirements:**

- [x] **FR-6.27**: When a skill specifies `applies_to: [coder, reviewer]`, only the `coder` and `reviewer` agents receive that skill's content in their assembled instructions. Other agents in the pipeline do not.
- [x] **FR-6.28**: When a skill omits the `applies_to` field entirely, all agents in the pipeline receive that skill's content.
- [x] **FR-6.29**: When multiple skills are loaded, they appear in assembled instructions ordered by `priority` (higher first), then alphabetically by name for equal priority.
- [x] **FR-6.30**: When a loaded skill's content contains curly braces that are not state template references, the braces are escaped to prevent unintended template substitution.

---

### CAP-7: Skill Index Caching

The skill index is cached for fast access across worker invocations without re-scanning the filesystem on every pipeline execution. The cache is invalidated when skill files change (detected via file modification timestamps during periodic rescans) and can be explicitly invalidated via a gateway endpoint.

**Requirements:**

- [x] **FR-6.31**: When the skill index is built, it is cached so that subsequent pipeline executions within the same worker or across workers retrieve the index without re-scanning the filesystem.
- [x] **FR-6.32**: When a periodic rescan detects that skill files have been added, removed, or modified (via file modification timestamps), the cache is invalidated and rebuilt.
- [x] **FR-6.33**: When a gateway API call triggers explicit cache invalidation, the next pipeline execution rebuilds the index from disk.
- [x] **FR-6.34**: When the cache is unavailable or expired, the system falls back to scanning the filesystem directly — cache failure does not prevent skill loading.

---

### CAP-8: Observability

Skill loading is fully observable through the event stream and session state. Every pipeline execution that loads skills publishes the resolution details. Operators can determine exactly which skills loaded, why they matched, and what the full index contains.

**Requirements:**

- [x] **FR-6.35**: When skills are loaded for a deliverable pipeline execution, the `loaded_skill_names` key in session state contains the list of all loaded skill names (including cascaded skills).
- [x] **FR-6.36**: When skills are loaded, the `loaded_skills` key in session state contains a mapping of skill name to skill body content for all loaded skills.
- [x] **FR-6.37**: When skills are loaded, a skill loading event is published to the event stream (Redis Streams) containing the deliverable identifier, the matched skill names, and the trigger types that caused each match.
- [x] **FR-6.38**: When no skills match a deliverable context, a warning event is published to the event stream identifying the deliverable and the context that produced no matches (same as FR-6.14).
- [x] **FR-6.39**: When the skill index is built or rebuilt, a lightweight skill catalog (name and description only for each indexed skill) is available for inspection — either via session state or gateway endpoint.

---

### CAP-9: Initial Skill Library

A curated set of global skills ships with the platform covering common development patterns. These skills are immediately useful out of the box and serve as examples of well-authored skills. The set includes both domain skills (code, review, testing, planning) and authoring skills that teach agents how to create system artifacts (skills, agent definitions, workflows, project conventions).

**Requirements:**

- [x] **FR-6.40**: The platform ships with global skills covering: API endpoint conventions, data model patterns, database migration patterns, security review checklist, performance review checklist, unit test patterns, task decomposition guidance, and file-editing skills for common document formats (docx, xlsx, pptx, pdf) including helper scripts.
- [x] **FR-6.41**: The platform ships with authoring skills covering: how to author SKILL.md files (skill-authoring), how to author agent definition files (agent-definition), how to author workflows (workflow-authoring), and how to configure project-level overrides (project-conventions).
- [x] **FR-6.42**: Each shipped skill follows the Agent Skills open standard file format: SKILL.md with YAML frontmatter in a named directory, with optional `references/`, `assets/`, and `scripts/` subdirectories.
- [x] **FR-6.43**: Each shipped skill has a `description` field written in third-person with specific trigger phrases (e.g., "This skill provides guidance when the deliverable involves..."), imperative/instructional writing style in the body, and body content under 3000 words with detailed content moved to `references/` files.
- [x] **FR-6.44**: The skill-authoring skill includes a validation checklist covering: frontmatter structure, required fields, trigger design, progressive disclosure (body size limits, references/ usage), writing style (imperative form, third-person description), and resource referencing.
- [x] **FR-6.45**: The skill-authoring skill includes a `references/skill-template.md` providing a complete SKILL.md template with all supported frontmatter fields annotated.

---

### CAP-10: Supervision-Tier Skill Resolution

The Director and PM operate outside the DeliverablePipeline — they run in chat sessions and work sessions where no SkillLoaderAgent executes. Yet they need skills just as deterministically as workers do. The Director needs governance, oversight, brief-shaping, and CEO communication skills every time it's invoked. The PM needs project-management, task-orchestration, and quality-gate skills for every project session.

The same matching engine handles all tiers. The difference is **when** matching runs: at build time for Director/PM (skills are static for the session, baked into instructions), at pipeline runtime for workers (skills vary per deliverable). No separate mechanism — same `SkillLibrary.match()`, same trigger system, different call site.

The complete deterministic skill loading model across all tiers:

1. **Role-bound skills** — `always` trigger + `applies_to` field. Structural. Director always gets governance skills. PM always gets management skills. Planner always gets decomposition skills. Configured in skill frontmatter, not assigned per-task.
2. **Context-matched skills** — trigger-matched against deliverable metadata (type, tags, files). Automatic via SkillLoaderAgent for workers. Not applicable to Director/PM (they don't process deliverables).
3. **Explicit override** — `requested_skills` in session state, matched via the `explicit` trigger. Rare, additive. For edge cases where the supervisor knows something metadata doesn't capture.

No tier assigns skill lists to another tier. The work itself — role, deliverable metadata, or explicit override — determines the skills. Deterministically, every time.

**Requirements:**

- [x] **FR-6.46**: When the Director agent is constructed (for chat session or work session), the system resolves skills by calling the same matching engine with a Director-specific context (agent role = director, no deliverable metadata). Matched skills are passed into the Director's instruction assembly. The Director receives its skills at build time, not at pipeline runtime.
- [x] **FR-6.47**: When the PM agent is constructed for a work session, the system resolves skills by calling the same matching engine with a PM-specific context (agent role = pm, no deliverable metadata). Matched skills are passed into the PM's instruction assembly. The PM receives its skills at build time, separately from the Director.
- [x] **FR-6.48**: When Director and PM are built in the same work session, each receives its own independently resolved skill set — the Director's role-bound skills are not the same as the PM's role-bound skills. They do not share a single skill context.
- [x] **FR-6.49**: When a skill declares `always` trigger with `applies_to: [director]`, it loads every time the Director is invoked — whether for a chat session, work session, or Director queue processing. The skill is part of the Director's operational identity.
- [x] **FR-6.50**: When a skill declares `always` trigger with no `applies_to` field, it loads for ALL agents across all tiers — Director, PM, and every worker in every pipeline. This is the mechanism for project-wide conventions that apply universally.

---

### CAP-11: Autonomous Skill Creation

Agents (Director, PM, or workers guided by the skill-authoring skill) can create new skills during execution. The system validates created skill files, indexes them, and makes them available to subsequent pipeline executions. Skill creation by agents follows the same validation rules as manually authored skills. This capability enables the system to encode learned patterns as reusable knowledge without human intervention.

**Requirements:**

- [x] **FR-6.51**: When an agent writes a SKILL.md file to the project-local skills directory via file tools, the system can index the new skill on the next cache rebuild or explicit invalidation — no restart or manual registration required.
- [x] **FR-6.52**: When a skill file is created, the system validates its frontmatter against the same rules used during indexing (FR-6.02, FR-6.03) — the validation logic is available as a callable function that agents or tools can invoke before writing.
- [x] **FR-6.53**: When the skill-authoring skill is loaded by an agent, it provides sufficient guidance for the agent to produce a valid SKILL.md file including: correct frontmatter structure, appropriate trigger design for the use case, body content following progressive disclosure principles, and proper resource referencing.
- [x] **FR-6.54**: When an agent creates a skill and triggers cache invalidation, the new skill is available to all subsequent pipeline executions in the same project — including the current work session's remaining deliverables.
- [x] **FR-6.55**: When an agent creates a skill with a `name` that conflicts with an existing global skill, the project-local override rules apply normally — the new skill replaces the global skill for that project.

---

## Non-Functional Requirements

- [x] **NFR-6.01**: Skill index building (full filesystem scan + frontmatter parsing) completes in under 2 seconds for a library of 100 skills.
- [x] **NFR-6.02**: Trigger matching against the full index completes in under 10 milliseconds per deliverable context — matching is O(n) in the number of indexed skills with constant-time per-trigger evaluation.
- [x] **NFR-6.03**: Individual skill body content (L2) is under 3000 words (~5000 tokens). Skills exceeding this are valid but log a warning recommending content be moved to `references/` files.
- [x] **NFR-6.04**: The skill system introduces no new external dependencies — it uses only the filesystem, Redis (already available), and Python standard library for YAML parsing and glob matching.
- [x] **NFR-6.05**: Skill frontmatter parsing is lenient for third-party skills (unknown fields ignored, non-standard metadata tolerated) but strict for required fields (`name`, `description`).
- [x] **NFR-6.06**: Cache invalidation is atomic — at no point does a pipeline execution see a partially rebuilt index. The old index serves requests until the new index is fully built.

---

## Rabbit Holes

- **Agent Skills `metadata` spec compliance**: The standard defines `metadata` as a string-to-string map. AutoBuilder's triggers, tags, applies_to, priority, and cascades are complex types (lists, objects, integers). The architect must decide whether to place AutoBuilder extension fields at the YAML top level (alongside `name`/`description`, ignored by other parsers) or accept the spec divergence under `metadata`. Top-level placement keeps `metadata` compliant for true string-value annotations. Decision to be resolved during build.

- **ADK compaction and skill content**: Skills are injected into agent instructions via the InstructionAssembler, which means they're part of the system instruction string. ADK's `LlmEventSummarizer` compacts conversation events, not the system instruction — so skills should survive compaction. However, this assumption must be verified. If ADK compaction does touch instructions, skill content will need identifiable markers and re-injection via `before_model_callback`. Context recreation (Phase 5b) already reloads skills from scratch, so recreation is safe.

- **Description keyword fallback precision**: Simple substring matching against `description` for third-party skills may produce false positives (skill description mentions "API" → matches any deliverable mentioning "API"). Keep matching conservative — multiple keywords should appear, not just any single one. But don't over-engineer: this is an interop fallback, not the primary matching path. Third-party skills that need precise matching can add triggers.

- **SkillEntry expansion from Phase 5a stub**: The existing `SkillEntry` dataclass has only `name`, `description`, `applies_to`. Phase 6 must expand it with `triggers`, `tags`, `priority`, `cascades`, and `path`. The `SkillMatchContext` must add `requested_skills` for the explicit trigger type. These are interface changes to the Phase 5a protocol — existing tests will need updating.

- **Director/PM skill resolution call site**: Director and PM currently share a single `InstructionContext` in `build_work_session_agents()`. Phase 6 must split this so each tier gets independently resolved skills. The build-time `skill_library.match()` call is ~5-10 lines per call site, but the `InstructionContext` separation requires touching `run_director_turn()`, `build_chat_session_agent()`, and `build_work_session_agents()`.

- **`applies_to` filtering in InstructionAssembler**: Both architects found that the current assembler does NOT filter loaded skills by `applies_to` — it dumps all `ctx.loaded_skills` into every agent's SKILL fragment. Phase 6 must add this filtering. The skill content in session state needs to carry `applies_to` metadata alongside the body text so the assembler can filter per-agent at assembly time. This is a type change to `loaded_skills` in session state.

- **Role-name coupling for `applies_to`**: Skills declare `applies_to: [coder, reviewer]` using agent names. If a custom workflow uses different agent names (e.g., `researcher` instead of `coder`), skills won't reach the right agents. Acceptable for Phase 6 (only auto-code workflow with fixed names). Phase 7a should add role aliases in agent definitions to decouple skill routing from agent names.

- **Redis cache serialization**: The skill index must serialize to Redis. `SkillEntry` with its trigger specs, lists, and path objects needs a clean serialization format. Use JSON with Path→string conversion. Keep it simple — the index is small (frontmatter only, not bodies).

---

## No-Gos

- **Workflow-tier skills (three-tier merge)** — Phase 7a. Requires WorkflowRegistry to provide the middle scope. Two-tier (global + project-local) is the Phase 6 boundary.
- **Automatic `scripts/` execution** — Deferred. The Agent Skills standard marks `allowed-tools` as experimental. Skills include `scripts/` directories and the system discovers them (`has_scripts` on SkillEntry), but agents invoke scripts via existing tools (`bash_exec`, `file_read`) — no automatic execution triggered by skill loading.
- **Self-updating skills** — Phase 7a+. The Anthropic skill-creator pattern where skills edit their own SKILL.md based on performance feedback is valuable but out of scope.
- **Skill versioning and deprecation** — Not needed until the skill library is mature. Files on disk are the source of truth; git provides version history.
- **Marketplace / registry / discovery service** — Phase 13+ at earliest. The file format IS the interop layer. Drop SKILL.md files in the project directory.
- **User-level skills** (`~/.agents/skills/`) — The standard recommends this scan scope. Defer until there's a demonstrated need for user-wide (not project-specific) skills.
- **Description optimization eval loop** — The Anthropic skill-creator's automated trigger-testing system is sophisticated but unnecessary when deterministic triggers are the primary matching mechanism. Defer.
- **Skill effectiveness metrics** — Tracking which skills improve deliverable outcomes is valuable but requires completed pipeline runs with comparison data. Phase 11+ (observability hardening).
- **L3 automatic loading** — `references/`, `assets/`, and `scripts/` files are available on disk and agents can read them via file tools. Automatic injection of L3 content into agent context is deferred.

---

## Traceability

### PRD Coverage

| FRD Requirement | PRD Requirement | Domain |
|-----------------|-----------------|--------|
| FR-6.01, FR-6.02, FR-6.03, FR-6.05 | PR-31 (Skills implement Agent Skills open standard: SKILL.md with YAML frontmatter, references/, assets/) | Skills file format |
| FR-6.04, FR-6.17 | PR-31 (Agents load frontmatter by default; full body on activation) | Progressive disclosure |
| FR-6.07, FR-6.08, FR-6.09, FR-6.10, FR-6.11, FR-6.12 | PR-32 (Skill activation is automatic: exact metadata.triggers match) | Trigger matching |
| FR-6.13, FR-6.14 | PR-32 (When no skill matches, execution continues and a warning event is emitted) | Match behavior |
| FR-6.15, FR-6.16, FR-6.17 | PR-33 (Third-party skills install without code changes; metadata.* namespace for extensions) | Interoperability |
| FR-6.18, FR-6.19, FR-6.20, FR-6.21 | PR-33 (Third-party skills install without code changes) | Override semantics |
| FR-6.22 through FR-6.26 | PR-32 (Skill activation is automatic) | Cascade resolution |
| FR-6.27, FR-6.28, FR-6.29, FR-6.30 | PR-5a (InstructionAssembler composes fragments; skills load progressively based on deliverable context) | Skill injection |
| FR-6.31 through FR-6.34 | PR-31 (Agents load only frontmatter by default) | Caching |
| FR-6.35, FR-6.36, FR-6.37, FR-6.38, FR-6.39 | PR-34 (Every project has a persistent, replayable event stream) | Observability |
| FR-6.40 through FR-6.45 | PR-31 (Skills implement Agent Skills open standard), PR-33 (metadata.* namespace) | Initial library |
| FR-6.46 through FR-6.50 | PR-5 (PM assembles appropriate agent configuration per stage; skills scoped per stage), PR-13 (Director is the user's executive partner — needs skills for governance, brief-shaping, CEO communication), PR-14 (PM owns delivery loop — needs management skills) | Supervision-tier skill resolution |
| FR-6.51 through FR-6.55 | PR-5a (Skills load progressively), PR-33 (Third-party skills install without code changes) | Autonomous creation |
| NFR-6.01, NFR-6.02 | NFR-2 (System overhead is not a meaningful contributor to stage duration) | Performance |
| NFR-6.03 | PR-31 (Agents load frontmatter by default — progressive disclosure) | Token budget |
| NFR-6.04 | NFR-6 (Runs fully on a single machine with no cloud dependencies) | Dependencies |
| NFR-6.05 | PR-33 (Third-party skills install without code changes) | Lenient parsing |
| NFR-6.06 | NFR-3 (Crash recovery; reliability) | Cache atomicity |

### Roadmap Contract Coverage

| # | Contract Item | Covered By |
|---|---------------|------------|
| 1 | SkillLoaderAgent loads relevant skills for a given deliverable context | CAP-1 (FR-6.01, FR-6.02), CAP-2 (FR-6.07 through FR-6.14), CAP-3 (FR-6.15, FR-6.16), CAP-5 (FR-6.22 through FR-6.26), CAP-6 (FR-6.27 through FR-6.30) |
| 2 | Skills appear in unified event stream | CAP-8 (FR-6.37, FR-6.38) |
| 3 | `loaded_skill_names` in state shows exactly which skills loaded | CAP-8 (FR-6.35) |
| 4 | Project-local skills override globals with same name | CAP-4 (FR-6.18, FR-6.21) |
| 5 | Director and PM receive independently resolved skills at build time (not pipeline runtime) | CAP-10 (FR-6.46 through FR-6.50) |
| 6 | `applies_to` filtering delivers per-agent skill content in assembled instructions | CAP-6 (FR-6.27, FR-6.28, FR-6.29) |
| 7 | Agents can create valid skill files; new skills indexed on cache rebuild | CAP-11 (FR-6.51 through FR-6.55) |
| 8 | ~320 lines core implementation (skill content and tests additional) | Appetite constraint; core library code budget |

---

## References

- **Agent Skills open standard**: https://agentskills.io/specification — file format, progressive disclosure, `metadata.*` extension point
- **Anthropic skill-creator**: https://github.com/anthropics/skills/tree/main/skills/skill-creator — eval/iterate loop, subagent grading, description optimization. Informed No-Gos (self-updating skills, description optimization eval loop).
- **Claude Code skill-development skill**: `/home/dmin/.agents/skills/skill-development/SKILL.md` — 6-step creation process, progressive disclosure, imperative writing style, validation checklist. Informed CAP-9 (FR-6.43, FR-6.44, FR-6.45) and CAP-11 (FR-6.53).
- **Research summary**: `.dev/.research/260311_claude-code-skills-system.md`
- **Architecture**: `.dev/architecture/skills.md` (v4.0)
