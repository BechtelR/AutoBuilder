# Agents
> Base: https://google.github.io/adk-docs

- **LLM agents** `/agents/llm-agents/` — core agent type; system_instruction, output_key, tools, sub_agents
- **Custom agents** `/agents/custom-agents/` — subclass BaseAgent, override _run_async_impl; yields Event stream
- **Sequential** `/agents/workflow-agents/sequential-agents/` — ordered pipeline, each agent runs in turn
- **Parallel** `/agents/workflow-agents/parallel-agents/` — concurrent execution, all agents run simultaneously
- **Loop** `/agents/workflow-agents/loop-agents/` — repeats sub-agent until escalation or max iterations
- **Multi-agent** `/agents/multi-agents/` — agent transfer, delegation, hierarchy patterns
- **Agent config** `/agents/config/` — AgentConfig, output schema, generate_content_config
- **Skills** `/skills/` — Agent Skills open standard, skill files, progressive loading

## Key Classes
`LlmAgent` `BaseAgent` `SequentialAgent` `ParallelAgent` `LoopAgent` `InvocationContext`

## See Also
→ ERRATA.md #1: state_delta persistence in CustomAgent
→ api-reference.md: google.adk.agents module
