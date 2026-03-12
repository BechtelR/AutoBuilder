# CustomAgent Definition Template

Annotated template for defining a deterministic custom agent.

---

```yaml
---
# REQUIRED
name: skill-loader                   # Role identifier; matches filename (skill-loader.md)
description: >-
  Deterministic agent that resolves and loads relevant skills into session state
  before any LLM agent runs. Runs as the first step in every DeliverablePipeline.
type: custom                         # Deterministic Python class, no LLM call

# REQUIRED for custom type
class: app.agents.skill_loader.SkillLoaderAgent   # Python import path to the class

# OPTIONAL
tool_role: read_only                 # Tool ceiling (custom agents often need minimal tools)
output_key: loaded_skills            # Session state key for primary output
---
```

No body content for custom agents — instructions are embedded in the Python class itself.
The frontmatter is still required for registry discovery.

---

## Notes

- `type: custom` requires `class` field pointing to a Python class in the worker process
- Custom agents cannot be defined at project scope — they require deployed code
- Body content is optional for custom agents; typically omitted since behavior is hardcoded
- The `class` value must be importable in the worker process context
- Custom agents inherit from `BaseAgent` and implement `_run_async_impl`

## When to Use Custom vs LlmAgent

Use `custom` when:
- Behavior is fully deterministic (no judgment needed)
- Speed matters (no LLM latency)
- The operation reads/writes structured state
- Examples: SkillLoaderAgent, MemoryLoaderAgent, context recreation steps

Use `llm` when:
- The task requires language understanding or generation
- Output varies based on input content
- Domain knowledge or reasoning is needed
- Examples: planner, coder, reviewer, fixer
