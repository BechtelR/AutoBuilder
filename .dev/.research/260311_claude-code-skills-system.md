# Claude Code Skills System -- Research Summary

**Date**: 2026-03-11
**Sources**: agentskills.io (official spec), github.com/anthropics/skills, github.com/Piebald-AI/claude-code-system-prompts, claude-plugins.dev

---

## 1. The Agent Skills Open Standard (agentskills.io)

### File Format: SKILL.md

A skill is a **directory** containing a `SKILL.md` file (YAML frontmatter + Markdown body):

```
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation
├── assets/           # Optional: templates, resources
```

### Frontmatter Fields

| Field           | Required | Purpose |
|-----------------|----------|---------|
| `name`          | Yes      | 1-64 chars, lowercase + hyphens, must match parent dir name |
| `description`   | Yes      | Max 1024 chars. Drives activation/triggering decisions |
| `license`       | No       | License name or reference to bundled file |
| `compatibility` | No       | Max 500 chars. Environment requirements |
| `metadata`      | No       | Arbitrary key-value map (author, version, etc.) |
| `allowed-tools` | No       | Space-delimited pre-approved tool patterns (experimental) |

### Claude Code Extensions to Frontmatter

Claude Code adds fields beyond the base spec:

| Field              | Purpose |
|--------------------|---------|
| `when_to_use`      | Detailed trigger description with example phrases |
| `argument-hint`    | Shows argument placeholder format |
| `arguments`        | List of argument names |
| `context`          | `inline` (default) or `fork` (subagent execution) |

### Name Constraints

- Lowercase alphanumeric + hyphens only
- No leading/trailing hyphens, no consecutive hyphens
- Must match parent directory name

---

## 2. Progressive Disclosure (The Core Pattern)

This is the single most important architectural pattern. Three tiers:

| Tier | What's loaded | When | Token cost |
|------|--------------|------|------------|
| 1. Catalog | name + description only | Session start | ~50-100 tokens/skill |
| 2. Instructions | Full SKILL.md body | When skill activated | <5000 tokens recommended |
| 3. Resources | scripts/, references/, assets/ | When instructions reference them | Varies |

**Key insight**: An agent with 20 skills pays only ~1000-2000 tokens at startup. Full instruction sets load only when needed. Reference files load only when the instructions say to read them.

**Recommendation for SKILL.md**: Keep under 500 lines. Move detailed reference material to separate files.

---

## 3. Discovery

### Scan Locations (Two-Scope Convention)

| Scope   | Path | Purpose |
|---------|------|---------|
| Project | `<project>/.claude/skills/` | Client-specific |
| Project | `<project>/.agents/skills/` | Cross-client interop |
| User    | `~/.claude/skills/` | Personal, cross-repo |
| User    | `~/.agents/skills/` | Cross-client interop |

### Name Collision Resolution

Project-level overrides user-level. Within same scope, first-found or last-found (be consistent). Log warnings on collisions.

### Trust Model

Project-level skills come from potentially untrusted repos. Gate project-level skill loading on a trust check. This prevents repo-injected instruction attacks.

---

## 4. Activation Mechanisms

### Model-Driven Activation
The model reads the catalog, decides a skill is relevant, and loads it. Two implementation paths:

1. **File-read activation**: Model uses its standard Read tool to load the SKILL.md path. Simplest approach.
2. **Dedicated tool activation**: Register a tool (e.g., `Skill`) that takes a skill name and returns content. Advantages: strip frontmatter, wrap in tags, list resources, enforce permissions, track analytics.

### User-Explicit Activation
Slash commands (`/skill-name`) or mention syntax that the harness intercepts. The harness handles lookup and injection.

### Claude Code's Implementation (from system prompts)

```
/<skill-name> (e.g., /commit) is shorthand for users to invoke a user-invocable skill.
When executed, the skill gets expanded to a full prompt. Use the Skill tool to execute them.
```

The `Skill` tool:
- Takes `skill` name and optional `args`
- Supports fully qualified names: `ms-office-suite:pdf`
- **BLOCKING REQUIREMENT**: Must invoke skill BEFORE generating any other response
- Skills listed in `<available-skills>` system-reminder messages
- If `<command-name>` tag already present, skill is already loaded -- follow instructions directly

---

## 5. Context Management

### Protecting Skill Content from Compaction
Skill instructions are **exempt from context pruning**. They are durable behavioral guidance. Losing them mid-conversation silently degrades performance.

### Structured Wrapping
Wrap activated skill content in identifying tags:
```xml
<skill_content name="pdf-processing">
  [instructions]
  <skill_resources>
    <file>scripts/extract.py</file>
  </skill_resources>
</skill_content>
```
Benefits: distinguishable from conversation, preservable during compaction, resource enumeration.

### Deduplication
Track which skills are activated per session. Skip re-injection if already in context.

### Subagent Delegation
Advanced pattern: run skill in a separate subagent session. Subagent gets skill instructions, performs task, returns summary. Useful for complex self-contained workflows.

---

## 6. Skill Triggering: What Makes a Good Description

### Principles from agentskills.io

1. **Use imperative phrasing**: "Use this skill when..." not "This skill does..."
2. **Focus on user intent, not implementation**: Match what user asks for
3. **Be pushy**: Explicitly list trigger contexts, including indirect references
4. **Include keywords the agent won't infer**: "even if they don't explicitly mention 'CSV'"
5. **Stay under 1024 characters**

### Claude Code's `when_to_use` Field

More detailed than `description`. Examples from real skills:

```yaml
when_to_use: >
  Use when the user wants to cherry-pick a PR to a release branch.
  Examples: 'cherry-pick to release', 'CP this PR', 'hotfix'.
```

### Eval-Driven Optimization

The spec recommends a formal eval loop:
1. Create ~20 queries (10 should-trigger, 10 should-not-trigger)
2. Run each 3x (nondeterministic model behavior)
3. Compute trigger rates
4. Use train/validation split to avoid overfitting
5. Iterate description based on failure analysis
6. ~5 iterations usually sufficient

---

## 7. Skill Composition Patterns (from Claude Code System Prompts)

### Built-in Skills

Claude Code ships with several internal skills that demonstrate composition:

**`simplify`**: Launched automatically by workers after implementing changes. Spawns 3 parallel review subagents (reuse, quality, efficiency) then aggregates findings.

**`loop`**: Parses interval + prompt, converts to cron expression, schedules recurring task. Shows skill-to-tool composition.

**`skillify`**: Meta-skill that captures a session's repeatable process as a new SKILL.md. 4-phase interview (analyze, confirm, detail, generate).

**Verifier skills**: Created by `create-verifier-skills` skill. Specialized per-project verification (Playwright, CLI, API). Self-updating -- if verification fails due to stale instructions, skill offers to edit its own SKILL.md.

### Worker Pipeline

Claude Code workers follow a post-implementation pipeline:
1. Invoke `/simplify` skill for code review
2. Run unit tests
3. Run e2e tests
4. Commit and push
5. Report

This shows skills as **composable pipeline stages**, not just standalone capabilities.

### Subagent Patterns

Two delegation styles:
1. **Context-inheriting fork** (omit `subagent_type`): Agent inherits full conversation. Prompt is a directive, not a briefing.
2. **Fresh subagent** (specify `subagent_type`): Agent starts from zero. Must brief it like "a smart colleague who just walked into the room."

Key rule: **"Never delegate understanding."** Don't write "based on your findings, fix the bug." Include file paths, line numbers, specifics.

---

## 8. Scripts in Skills

### Self-Contained Scripts with Inline Dependencies

Skills can bundle executable scripts. Best practice: use inline dependency declarations so scripts need no separate install step.

- Python: PEP 723 (`# /// script` blocks), run with `uv run`
- Deno: `npm:` import specifiers
- Ruby: `bundler/inline`

### Design for Agentic Use

- **No interactive prompts** (hard requirement -- agents can't respond to TTY)
- **`--help` output** is how the agent learns the interface
- **Helpful error messages**: say what went wrong, what was expected, what to try
- **Structured output** (JSON/CSV) over free-form text
- **Idempotent**: agents may retry
- **Predictable output size**: agents truncate large output

---

## 9. The Registry/Marketplace (claude-plugins.dev)

- Community registry at claude-plugins.dev, auto-indexes public GitHub skills
- Official skills from `@anthropics/skills` repo (90.7k stars)
- Installation via `/plugin install` or `/plugin marketplace add`
- Tracks downloads, stars, sorting by relevance
- Skills discoverable by the `skills-discovery` meta-skill within Claude Code itself

---

## 10. Patterns AutoBuilder Should Adopt

### High-Priority Adoptions

1. **Progressive disclosure is essential**. AutoBuilder's InstructionAssembler already has fragment types (SAFETY, IDENTITY, GOVERNANCE, PROJECT, TASK, SKILL). Map these to the 3-tier model:
   - Tier 1 (catalog): skill name + description in system prompt at session start
   - Tier 2 (instructions): full skill body loaded when assembler activates skill
   - Tier 3 (resources): scripts/references loaded on demand by agent

2. **The SKILL.md format is the right choice**. AutoBuilder already decided on Agent Skills open standard (Decision #37). The spec confirms: YAML frontmatter + Markdown body, `scripts/`, `references/`, `assets/` directories. Our existing `.agents/skills/` path convention aligns with the cross-client interop standard.

3. **Description-driven activation**. The `description` field (and Claude Code's extended `when_to_use`) is the primary trigger mechanism. AutoBuilder's SkillLibraryProtocol `match()` method should implement description-based matching. The eval-driven optimization loop is worth considering for skill quality.

4. **Context protection**. Activated skill content must survive context compaction. AutoBuilder's context recreation pipeline should treat skill content as durable -- equivalent to how Claude Code exempts skill tool outputs from pruning.

5. **Structured wrapping**. Wrap activated skill content in identifying tags so it can be distinguished during context recreation. Aligns with AutoBuilder's InstructionAssembler fragment model.

6. **Trust boundaries**. Project-scope skills from potentially untrusted repos need gating. AutoBuilder already has Decision #58 (project-scope = `type: llm` only, `tool_role` ceiling). The spec's trust model validates this approach.

### Medium-Priority Adoptions

7. **Self-updating skills**. Claude Code's verifier skills offer to self-update when their instructions are stale. AutoBuilder could support this for project-scope skills -- agents propose edits to SKILL.md when they detect drift.

8. **`allowed-tools` field**. Maps directly to AutoBuilder's tool_role ceiling concept. The space-delimited pattern format (`Bash(git:*)`, `Read`) is simple and expressive.

9. **`context: fork` for subagent delegation**. Skills that are self-contained can run in a separate agent session. This aligns with AutoBuilder's worker agent model -- some skills are better executed as isolated tasks.

10. **Skillify pattern**. The meta-skill that captures a session as a reusable skill is powerful for user-driven skill creation. AutoBuilder's Settings conversation could support a similar workflow.

### Patterns to Avoid

11. **Over-complex frontmatter**. The base spec keeps frontmatter minimal (name, description, license, compatibility, metadata). Claude Code adds several fields (when_to_use, arguments, argument-hint, context). AutoBuilder should start minimal and extend only when proven necessary.

12. **Eager resource loading**. Never load scripts/ and references/ upfront. The progressive disclosure model is critical for token economy.

13. **Hardcoded skill activation logic**. The spec explicitly warns against harness-side keyword matching. Let the model decide activation based on the catalog. AutoBuilder's SkillLoaderAgent should follow this -- deterministic loading, but model-driven activation decisions.

---

## 11. Key Differences from AutoBuilder's Current Design

| Aspect | Agent Skills Spec | AutoBuilder Current (Decision #37, #50) |
|--------|-------------------|----------------------------------------|
| Discovery | Filesystem scan at session start | 3-scope cascade (global, workflow, project) |
| Activation | Model reads catalog, decides | SkillLoaderAgent (deterministic CustomAgent) |
| Loading | File-read or dedicated tool | InstructionAssembler SKILL fragment |
| Composition | Subagent delegation (optional) | Pipeline stages within workflow |
| Security | Trust gating on project-level | Tier-prefixed state keys, tool_role ceiling |

AutoBuilder's multi-scope cascade (global > workflow > project) is a superset of the spec's two-scope model (user > project). This is fine -- more scopes, same precedence logic.

AutoBuilder's SkillLoaderAgent as a deterministic CustomAgent is a reasonable approach. The spec supports both model-driven and harness-driven activation. Since AutoBuilder's agents run in worker processes, deterministic skill loading at pipeline start makes sense -- the PM or Director has already decided which skills are relevant.

---

## 12. Source Files Referenced

- Spec: https://agentskills.io/specification
- Client implementation guide: https://agentskills.io/client-implementation/adding-skills-support
- Description optimization: https://agentskills.io/skill-creation/optimizing-descriptions
- Scripts in skills: https://agentskills.io/skill-creation/using-scripts
- Official skills repo: https://github.com/anthropics/skills
- Anthropic skill-creator (33KB, eval/iterate loop, subagent grading): https://github.com/anthropics/skills/tree/main/skills/skill-creator
- Claude Code skill-development skill (local, 638 lines): `/home/dmin/.agents/skills/skill-development/SKILL.md` — 6-step creation process, progressive disclosure, imperative writing style, validation checklist. Informed CAP-9 (FR-6.43, FR-6.44, FR-6.45) and CAP-11 (FR-6.53).
- System prompts archive: https://github.com/Piebald-AI/claude-code-system-prompts
