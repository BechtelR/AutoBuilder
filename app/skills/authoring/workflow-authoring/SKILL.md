---
name: workflow-authoring
description: This skill provides guidance for composing workflow definitions in AutoBuilder, covering WORKFLOW.yaml manifest schema, pipeline composition, and workflow-specific agents and skills. Load when creating a new workflow, adding a workflow type to AutoBuilder, writing a WORKFLOW.yaml manifest, or composing a DeliverablePipeline for a new domain.
triggers:
  - always: true
tags: [authoring, workflows, pipeline]
applies_to: [coder, planner]
priority: 5
---

# Workflow Authoring Guide

This skill covers how to create new workflow definitions in AutoBuilder. A workflow is a named, self-contained pipeline configuration that handles a specific class of deliverable — for example, a `code` workflow for software implementation or a `research` workflow for document production.

## Workflow Directory Structure

Each workflow lives in its own directory under `app/workflows/`:

```
app/workflows/
└── code/
    ├── WORKFLOW.yaml        # Manifest: triggers, tools, config
    ├── pipeline.py          # ADK agent tree definition
    ├── agents/              # Workflow-specific agent overrides
    │   ├── planner.md
    │   └── coder.md
    └── skills/              # Workflow-specific skill overrides
        └── api-endpoint/
            └── SKILL.md
```

The directory name (`code`) is the workflow's unique identifier. WorkflowRegistry discovers workflows by scanning `app/workflows/` — no code registration required.

## WORKFLOW.yaml Manifest

The manifest declares the workflow's metadata, trigger conditions, required tools, and pipeline configuration. All fields except `name` are optional.

```yaml
name: code                           # Unique identifier, matches directory name

description: >-
  Software implementation workflow. Handles deliverables that require
  writing, modifying, or testing code.

# When this workflow handles a deliverable (PM selects the workflow)
triggers:
  - deliverable_type: api_endpoint
  - deliverable_type: database_migration
  - deliverable_type: unit_test
  - tag_match: code

# Tools the pipeline needs (gates which tool_role ceiling applies)
required_tools: [read, write, bash, search]
optional_tools: [mcp]

# Model defaults for this workflow (override global settings)
default_models:
  CODE: claude-3-5-sonnet-latest
  REVIEW: claude-3-5-sonnet-latest

# Pipeline configuration
pipeline:
  max_review_cycles: 3
  timeout_seconds: 300
```

### Manifest Trigger Types

Manifest triggers determine when the PM assigns a deliverable to this workflow:
- `deliverable_type: <type>` — deliverable type matches
- `tag_match: <tag>` — deliverable has this tag and the workflow's `triggers` list the tag
- `always: true` — fallback workflow when no other workflow matches

### Required vs Optional Tools

`required_tools` lists tools the pipeline cannot function without. If a project's security policy disallows a required tool, the pipeline fails fast with a meaningful error rather than producing partial output.

`optional_tools` lists tools used when available but not critical.

## Pipeline Composition

`pipeline.py` defines the ADK agent tree for the workflow. Import ADK agent types and define a `create_pipeline()` function that returns the root agent:

```python
from google.adk.agents import SequentialAgent
from app.agents.registry import AgentRegistry

def create_pipeline(ctx: PipelineContext) -> SequentialAgent:
    registry = AgentRegistry(ctx)
    return SequentialAgent(
        name="code_pipeline",
        sub_agents=[
            registry.build("skill-loader"),
            registry.build("planner"),
            registry.build("coder"),
            registry.build("reviewer"),
        ],
    )
```

Use `SequentialAgent` for ordered pipelines where each step depends on the previous. Use `ParallelAgent` only when steps are genuinely independent with no state dependencies.

`AgentRegistry.build()` resolves agent definitions from the three-scope cascade (global → workflow → project) and assembles instructions. Pass the agent role name as the first argument.

## Workflow-Specific Agents

Place agent definition overrides in `agents/` within the workflow directory. These follow the same format as global agents (Markdown with YAML frontmatter) but apply only when this workflow is executing.

Use workflow-scope overrides when:
- The agent needs different instructions for this workflow's domain
- A different model role is more appropriate for this workflow type
- The tool ceiling should be narrower than the global default

Workflow-scope agent definitions apply the same replacement semantics: a workflow-scope definition completely replaces the global definition of the same name.

## Workflow-Specific Skills

Place skill overrides in `skills/` within the workflow directory. Skills follow the same format as global skills (directory with SKILL.md). Workflow-scope skills replace global skills with the same name.

Use workflow-scope skills when:
- Global skill guidance is too generic for this workflow's domain
- The workflow has specific patterns that override global conventions
- New skills are relevant only within this workflow context

## WorkflowRegistry Discovery

WorkflowRegistry scans `app/workflows/` at startup. No code registration is required — creating the directory with a valid `WORKFLOW.yaml` is sufficient. The registry:

1. Scans all subdirectories of `app/workflows/`
2. Reads `WORKFLOW.yaml` from each subdirectory
3. Validates `name` field matches the directory name
4. Registers the workflow under its `name` key
5. Logs a warning and skips malformed manifests (does not fail startup)

## Checklist

- Directory name matches `name` in `WORKFLOW.yaml`
- `triggers` define when the PM routes deliverables to this workflow
- `required_tools` accurately reflects what the pipeline cannot work without
- `pipeline.py` exports `create_pipeline()` returning a valid ADK agent tree
- Workflow-scope agents and skills follow the same format as global definitions

## Additional Resources

- **`references/workflow-manifest.yaml`** — Complete WORKFLOW.yaml template with all fields and inline documentation
