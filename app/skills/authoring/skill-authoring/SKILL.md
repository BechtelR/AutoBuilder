---
name: skill-authoring
description: This skill provides comprehensive guidance for creating SKILL.md files following the Agent Skills open standard, including frontmatter structure, trigger design, writing conventions, and validation checklist. Load when creating a new skill, writing a SKILL.md file, authoring agent knowledge, encoding project conventions as a skill, or building reusable guidance for agents.
triggers:
  - always: true
tags: [authoring, skills, agent-skills]
applies_to: [coder, planner]
priority: 5
---

# Skill Authoring Guide

This skill provides the complete specification for creating valid SKILL.md files in AutoBuilder's skill system. Skills encode domain knowledge, project conventions, and reusable patterns as structured files that agents load deterministically based on task context.

## File Format

A skill is a **named directory** containing a `SKILL.md` file. The directory name should match the `name` field in frontmatter (a mismatch triggers a warning but the frontmatter `name` is used):

```
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── references/       # Optional: detailed documentation, templates
└── assets/           # Optional: files used in output
```

The `SKILL.md` file has two sections:
1. **YAML frontmatter** between `---` delimiters — lightweight metadata parsed for matching
2. **Markdown body** — instructions loaded only when the skill matches a task

## Required Frontmatter Fields

### `name`

String. Must match the parent directory name exactly. Lowercase alphanumeric characters and hyphens only. No leading/trailing hyphens, no consecutive hyphens. Maximum 64 characters.

```yaml
name: api-endpoint
```

### `description`

String. Maximum 1024 characters. Written in **third-person** with specific trigger phrases. The description drives catalog-level discovery — make it explicit about when this skill applies.

```yaml
description: This skill provides conventions for implementing REST API endpoints, including route structure, request/response models, and error handling. Load when implementing an API route, adding a gateway endpoint, or reviewing API code.
```

Avoid vague descriptions ("This skill helps with APIs"). Include concrete trigger contexts and specific phrases an agent would encounter.

## Optional AutoBuilder Extension Fields

These fields appear at the **top level** of the YAML frontmatter, alongside `name` and `description`. They are AutoBuilder-specific extensions to the Agent Skills standard.

### `triggers`

List of trigger specifications. A skill matches if **any** trigger matches (OR logic). At least one trigger is recommended for deterministic matching.

Five trigger types:

| Type | Format | Matches When |
|------|--------|--------------|
| `deliverable_type` | `- deliverable_type: api_endpoint` | Deliverable type exactly equals the value |
| `file_pattern` | `- file_pattern: "*/routes/*.py"` | Any target file matches the glob pattern |
| `tag_match` | `- tag_match: security` | Any deliverable tag intersects with the skill's `tags` list |
| `explicit` | `- explicit: my-skill-name` | Skill name appears in `requested_skills` session state |
| `always` | `- always: true` | Unconditional — loads for every invocation for agents in `applies_to` |

### `tags`

List of strings. Used by the `tag_match` trigger type — when a deliverable has overlapping tags, the skill matches. Also serves as keyword fallback for description matching.

```yaml
tags: [api, http, routing, fastapi]
```

### `applies_to`

List of agent role names. If specified, only those agents receive this skill's content after it matches. If omitted or empty, all agents receive the skill.

```yaml
applies_to: [coder, reviewer]  # Only coder and reviewer get this skill
```

Valid agent roles: `director`, `pm`, `planner`, `coder`, `reviewer`, `fixer`, `tester`, `linter`, `diagnostics`.

### `priority`

Integer, default 0. Higher priority skills load before lower priority skills in assembled instructions. Use priority to ensure foundational skills (governance, conventions) appear before domain skills.

```yaml
priority: 10  # Loads before skills with priority 0-9
```

### `cascades`

List of skill references. When this skill matches, the listed skills are also loaded automatically. Use for skills that always pair together.

```yaml
cascades:
  - reference: error-handling
  - reference: logging-conventions
```

## Writing Conventions

### Body Style

Write the body in **imperative/instructional style**. Use verb-first sentences. Avoid second person ("you should").

```
# Correct
Use X when implementing Y.
Always validate Z before calling W.
Configure the router with prefix and tags.

# Incorrect
You should use X when implementing Y.
You need to always validate Z.
The router should be configured with...
```

### Frontmatter Description Style

Write descriptions in **third-person** with specific trigger phrases.

```
# Correct
This skill provides guidance for... Load when creating... or implementing...

# Incorrect
Use this skill when you want to...
Load when working with...
```

### Body Length

Keep the body under **3000 words**. The body loads into agent context on every match — every word costs tokens. Move detailed reference content to `references/` subdirectory files. Agents can read those files on demand when instructions reference them.

### No Template Syntax

Do not use `{variable}` syntax in skill body text. The InstructionAssembler escapes curly braces for ADK template processing. If showing a template pattern, escape the braces or use code blocks.

### Code Blocks

Include code examples directly in the body for critical patterns. Move lengthy code examples to `references/` files.

## Directory Structure

```
app/skills/
├── code/
│   └── api-endpoint/
│       ├── SKILL.md
│       └── references/      # Optional: detailed patterns
└── authoring/
    └── skill-authoring/
        ├── SKILL.md
        └── references/
            └── skill-template.md   # Full annotated template
```

Global skills ship in `app/skills/`. Project-local skills live in `.agents/skills/` at the project root. A project-local skill with the same `name` as a global skill replaces the global entirely — no merging.

## Progressive Disclosure

Skills follow a three-level disclosure model:

1. **Catalog** (always in context): `name` + `description` only, ~50-100 tokens per skill
2. **Body** (on match): Full SKILL.md markdown, loads when skill is activated
3. **References** (on demand): Files in `references/` and `assets/`, read by agents when instructions reference them

This means the body of a SKILL.md is the "second tier" — it loads when the skill matches but before any reference files are read. Keep the body focused on essential patterns that the agent always needs. Put exhaustive detail, extended examples, and reference templates in `references/`.

## Validation Checklist

Before finalizing a SKILL.md:

- [ ] `name` field present and should match directory name (lowercase, hyphens only)
- [ ] `description` field present, third-person, specific trigger phrases, under 1024 characters
- [ ] At least one trigger defined (or `description` is keyword-rich for fallback matching)
- [ ] `applies_to` lists specific agent roles if the skill is role-specific (omit for all agents)
- [ ] Body is imperative/instructional style (verb-first, not "you should")
- [ ] Body under 3000 words
- [ ] Detailed content in `references/` if body would exceed limit
- [ ] No `{variable}` template syntax in body text
- [ ] Extension fields at top level of frontmatter (not nested under `metadata`)
- [ ] All files referenced in body actually exist in the skill directory

## Additional Resources

For a complete annotated template showing all frontmatter fields with inline documentation:

- **`references/skill-template.md`** — Full SKILL.md template with all supported fields, examples, and inline notes
