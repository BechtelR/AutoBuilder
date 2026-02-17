# Callbacks
> Base: https://google.github.io/adk-docs

- **Overview** `/callbacks/` — callback system architecture, when callbacks fire
- **Types** `/callbacks/types-of-callbacks/` — before/after model, before/after tool, before/after agent
- **Design patterns** `/callbacks/design-patterns-and-best-practices/` — guard rails, logging, modification patterns
- **Context caching** `/context/caching/` — LLM context caching for cost reduction
- **Context compaction** `/context/compaction/` — automatic context window management

## Key Classes
`CallbackContext` `BeforeModelCallback` `AfterModelCallback` `BeforeToolCallback` `AfterToolCallback`

## See Also
→ safety.md: callbacks for content filtering
→ agents.md: agent-level callback configuration
