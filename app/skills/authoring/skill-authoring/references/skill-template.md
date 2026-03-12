# Skill Template

Complete SKILL.md template with all supported frontmatter fields and inline documentation.

---

```yaml
---
# REQUIRED FIELDS (Agent Skills standard)
name: my-skill-name                    # Must match parent directory name (lowercase, hyphens only)
description: >-                        # Third-person, specific trigger phrases, under 1024 chars
  This skill provides guidance for... Load when creating..., implementing...,
  or reviewing... Include concrete phrases that indicate this skill is relevant.

# OPTIONAL: AutoBuilder Extension Fields (top-level, NOT nested under metadata)
triggers:                              # At least one recommended for deterministic matching
  - deliverable_type: api_endpoint     # Exact match on deliverable type string
  - file_pattern: "*/routes/*.py"      # Glob match on any file in target_files
  - tag_match: security                # Set intersection with skill's tags list
  - explicit: my-skill-name           # Matches against requested_skills in session state
  - always: true                       # Unconditional match for agents in applies_to

tags: [api, http]                      # Used by tag_match trigger + keyword fallback
applies_to: [coder, reviewer]          # Agent roles that receive this skill (omit = all)
priority: 10                           # Higher loads first in assembled instructions (default: 0)

cascades:                              # Load these skills alongside this one when it matches
  - reference: error-handling
  - reference: logging-conventions
---
```

---

## Body Template

```markdown
# Skill Title

One or two sentences describing what this skill covers and when it applies.

## Core Concept One

Imperative/instructional content. Use verb-first sentences:
- Configure X before calling Y
- Always validate Z at the boundary
- Use W when implementing V

Include code examples for critical patterns inline:

\```python
# Short, essential example
result = service.create(request)
\```

## Core Concept Two

Keep sections focused. Each section should cover a single concept or practice area.

When a section would need extensive examples or detailed reference material,
reference a file in references/:

For the complete reference, read `references/detailed-guide.md`.

## Checklist

- Item one to verify
- Item two to verify
- Item three to verify

## Additional Resources

- **`references/detailed-guide.md`** — Extended patterns and examples
- **`references/template.md`** — Boilerplate template to adapt
```

---

## Notes on Trigger Selection

Choose triggers based on how the skill becomes relevant:

**Use `always`** when the skill is fundamental to a role's operation — governance rules, identity constraints, universal conventions. Combine with `applies_to` to limit to specific roles.

**Use `deliverable_type`** when the skill is specifically for a category of work — API endpoints, database migrations, research reports.

**Use `file_pattern`** when the skill applies to work on specific files — route files, migration files, test files. Good for refactoring scenarios where `deliverable_type` is generic but the files are specific.

**Use `tag_match`** when the deliverable has labels that indicate relevance — `security`, `performance`, `breaking-change`. The skill's `tags` list must overlap with the deliverable's tags.

**Use `explicit`** for skills that should only load when specifically requested — advanced techniques, experimental patterns, override behaviors.

Multiple triggers on one skill = OR logic. The skill loads if any trigger matches.

---

## Common Mistakes

**Wrong: extension fields nested under `metadata`**
```yaml
metadata:
  triggers:
    - always: true
  tags: [api]
```

**Correct: extension fields at top level**
```yaml
triggers:
  - always: true
tags: [api]
```

---

**Wrong: second-person body**
```
You should use the APIRouter with a prefix.
You need to validate all inputs.
```

**Correct: imperative body**
```
Use the APIRouter with a consistent prefix.
Validate all inputs at the boundary.
```

---

**Wrong: vague description**
```yaml
description: Provides API guidance.
```

**Correct: specific description with trigger context**
```yaml
description: This skill provides conventions for REST API endpoints in AutoBuilder's gateway layer. Load when implementing an API route, adding a new endpoint, or reviewing gateway code.
```
