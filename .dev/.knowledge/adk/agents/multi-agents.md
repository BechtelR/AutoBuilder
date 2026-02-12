# Multi-Agent Systems in ADK

**Source:** https://google.github.io/adk-docs/agents/multi-agents/
**Downloaded:** 2026-02-11

## Core Concepts

The Agent Development Kit enables building sophisticated applications by composing multiple `BaseAgent` instances into coordinated systems. This approach offers enhanced modularity, specialization, reusability, and structured control flows.

## 1. ADK Primitives for Agent Composition

### Agent Hierarchy (Parent-Child Relationships)

The foundation involves creating tree structures through `sub_agents` parameters. Key rules:
- ADK automatically sets the `parent_agent` attribute on children during initialization
- Each agent instance can only have one parent (attempting multiple assignments raises `ValueError`)
- Hierarchy defines scope for workflow agents and influences delegation targets

### Workflow Agents as Orchestrators

Three specialized agent types manage sub-agent execution:

**SequentialAgent**: Executes sub-agents sequentially in listed order
- "Passes the _same_ `InvocationContext` sequentially"
- Enables straightforward data passing via shared state
- Use case: Multi-step pipelines where later stages depend on earlier results

**ParallelAgent**: Runs sub-agents concurrently
- Modifies `InvocationContext.branch` for each child
- All children access the same shared `session.state`
- Use case: Independent parallel tasks that should complete faster together

**LoopAgent**: Executes sub-agents repeatedly
- Continues until `max_iterations` reached or escalate flag triggered
- Maintains same context across iterations
- Use case: Polling, iterative refinement, condition-based repetition

### Interaction & Communication Mechanisms

**Shared Session State (`session.state`)**
- Most fundamental communication method for agents sharing invocations
- One agent writes values; subsequent agents read them
- `output_key` property automatically saves LlmAgent final responses to state
- Ideal for sequential and loop workflows

**LLM-Driven Delegation (Agent Transfer)**
- Leverages LLM understanding for dynamic task routing
- LLM generates specific function call: `transfer_to_agent(agent_name='target')`
- AutoFlow intercepts and routes execution using `find_agent()`
- Requires clear agent descriptions and coordinator instructions
- Provides flexible, LLM-interpreted routing

**Explicit Invocation (AgentTool)**
- Wraps agent instances as callable tools in another agent's `tools` list
- When invoked, AgentTool executes the target agent and returns results
- Synchronous, explicit, controlled like any other tool
- Requires importing and manually wrapping agents

## 2. Common Multi-Agent Patterns

### Coordinator/Dispatcher Pattern
Central `LlmAgent` manages specialized `sub_agents`, routing requests appropriately. Uses LLM-driven delegation or explicit invocation with clear agent descriptions.

### Sequential Pipeline Pattern
`SequentialAgent` containing ordered agents where outputs feed forward. Earlier agents write results (via `output_key`); later agents read and process them from shared state.

### Parallel Fan-Out/Gather Pattern
`ParallelAgent` executes multiple agents concurrently (fan-out), then a subsequent sequential agent aggregates results (gather). Sub-agents write to distinct state keys; the aggregator reads multiple keys.

### Hierarchical Task Decomposition
Multi-level agent trees where higher-level agents break complex goals into sub-tasks delegated to lower-level agents. Results flow back up the hierarchy through tool responses or state modifications.

### Review/Critique Pattern (Generator-Critic)
`SequentialAgent` with a Generator producing content (saved via `output_key`) and a Critic reviewing it (reading from state). Provides quality assurance through specialized review agents.

### Iterative Refinement Pattern
`LoopAgent` repeatedly executes agents working on stored state until quality targets are met or iteration limits reached. Progressively improves outputs through multiple passes.

### Human-in-the-Loop Pattern
Incorporates human decision-making between agent steps, often with configurable approval policies for sensitive operations.

### Combining Patterns
Complex systems combine multiple patterns—for example, nesting `ParallelAgent` within `SequentialAgent` for sophisticated workflows balancing parallelism with sequential dependencies.

## Key Design Principles

- **Modularity**: Each agent handles specialized responsibilities
- **Reusability**: Agents function independently or within hierarchies
- **State Management**: Leverage shared `session.state` for passive communication
- **Explicit Control**: Use workflow agents for deterministic execution flows
- **Dynamic Routing**: Enable LLM-driven delegation for adaptive systems

This composable architecture enables building everything from simple tool-calling agents to complex multi-level systems managing intricate business processes.
