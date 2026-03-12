---
name: agent-definition
description: This skill provides guidance for authoring agent definition files in AutoBuilder, covering the markdown-plus-YAML-frontmatter format, three-scope cascade, metadata fields, and body writing conventions. Load when creating a new agent definition, customizing agent behavior for a project, writing agent identity or instruction content, or overriding an existing agent at the workflow or project scope.
triggers:
  - always: true
tags: [authoring, agents, definitions]
applies_to: [coder, planner]
priority: 5
---

# Agent Definition Authoring

This skill covers how to create and override agent definition files in AutoBuilder. Agent definition files are the mechanism for shaping agent identity, behavior, and constraints — both for global agents shipped with AutoBuilder and for project-specific overrides.

## File Format

Agent definitions are **Markdown files with YAML frontmatter**. Unlike skills (which have a fixed filename `SKILL.md`), agent definition files are named after the agent role they define:

```
agents/
├── planner.md        # Defines the "planner" agent
├── coder.md          # Defines the "coder" agent
└── reviewer.md       # Defines the "reviewer" agent
```

The filename (without `.md`) is the agent's lookup key. The `name` field in frontmatter should match the filename.

## Frontmatter Fields

### Required Fields

**`name`** — String. The agent's unique role identifier. Must match the filename. Use the canonical normalized names: `planner`, `coder`, `reviewer`, `fixer`, `tester`, `linter`, `diagnostics`, `pm`, `director`.

**`description`** — String. A brief summary of the agent's role and responsibilities.

**`type`** — Either `llm` or `custom`. LLM agents use an LLM model to process and respond. Custom agents are deterministic Python classes with hardcoded logic.

### Optional Fields

**`class`** — Python import path for the implementation class. Required when `type: custom`. Ignored when `type: llm`.

```yaml
class: app.agents.skill_loader.SkillLoaderAgent
```

**`model_role`** — Which LLM to use. Maps to a model role key that resolves to an actual model via settings. Common values: `CODE`, `PLAN`, `REVIEW`, `FAST`. Applies to `type: llm` only.

```yaml
model_role: CODE
```

**`tool_role`** — Which tool set to provide. Determines the agent's capability ceiling. Common values: `full`, `read_only`, `write_only`, `search`. Higher scopes are superset of lower scopes.

```yaml
tool_role: full
```

**`output_key`** — Session state key where the agent writes its primary output. Used for inter-agent handoffs within a pipeline.

```yaml
output_key: implementation_result
```

## Body Content

The body of an agent definition file is the **instruction content** injected into the agent's system prompt. Write it as the agent's operational guidance — its identity, its role, its constraints, and its specific behavioral rules.

Write instructions in second person from the perspective of the agent:

```markdown
You are the Coder agent. Your role is to implement deliverables based on a
detailed implementation plan produced by the Planner.

## Core Responsibilities

Implement the plan step by step. Write code that is correct, tested, and
follows project conventions loaded from matched skills.

## Constraints

Never modify files outside the deliverable's declared scope.
Always write tests alongside implementation code.
```

The body combines with other instruction fragments (SAFETY, IDENTITY, GOVERNANCE, PROJECT, TASK) at assembly time. Focus the body on role-specific behavior — do not repeat safety or governance rules that apply to all agents.

## Three-Scope Cascade

Agent definitions exist at three scopes, resolved in order from lowest to highest precedence:

| Scope | Location | Purpose |
|-------|----------|---------|
| **Global** | `app/agents/` | Ships with AutoBuilder, applies to all projects |
| **Workflow** | `workflows/{name}/agents/` | Workflow-specific specializations |
| **Project** | `.agents/agents/` | Project-specific overrides |

**Full replacement by name**: When a definition at a higher scope has the same `name` as a lower scope definition, the higher scope definition completely replaces it. There is no merging of frontmatter or body content.

**Partial override (frontmatter-only)**: A definition file that contains only frontmatter and no body inherits the body from the next lower scope. Use this to change `model_role` or `tool_role` without rewriting the full instruction body.

```yaml
---
# Project-scope override: change the model, keep the global body
name: coder
type: llm
model_role: PLAN
---
```

## Project-Scope Restrictions

Agent definitions at the project scope (`.agents/agents/`) have restrictions:

- **`type: llm` only** — Project-scope definitions cannot introduce `custom` agents. Custom agents require Python code deployment.
- **`tool_role` ceiling** — Project-scope definitions cannot grant tool roles beyond the workflow's declared ceiling. A project cannot escalate its own agent permissions.

These restrictions prevent untrusted projects from injecting malicious agent behavior or escalating capabilities.

## Writing Agent Instructions

Effective agent instruction bodies follow these patterns:

**State the role clearly at the start.** The agent should know what it is and what it produces:

```markdown
You are the Planner agent. You receive a deliverable specification and produce
a detailed, step-by-step implementation plan for the Coder to execute.
```

**List core responsibilities as specific actions**, not general principles:

```markdown
- Analyze the deliverable spec and identify all files that need to be created or modified
- Break implementation into discrete steps ordered by dependency
- Flag ambiguities in the spec before planning rather than making assumptions
```

**State constraints explicitly.** What the agent must never do is as important as what it should do:

```markdown
Never write code in the plan — produce task descriptions, not implementations.
Never plan beyond the deliverable's declared scope.
```

**Reference session state keys** for inter-agent handoffs. The `output_key` frontmatter field sets where the agent writes, and the instruction body can reference what state keys it reads.

## Additional Resources

- **`references/llm-agent.md`** — Complete annotated template for an LlmAgent definition
- **`references/custom-agent.md`** — Complete annotated template for a CustomAgent definition
