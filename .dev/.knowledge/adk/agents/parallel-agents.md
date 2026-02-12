# Parallel Agents

Source: https://google.github.io/adk-docs/agents/workflow-agents/parallel-agents/

## Overview

The `ParallelAgent` is a workflow agent that "executes its sub-agents _concurrently_," enabling significant performance improvements for independent tasks.

## Key Characteristics

**Purpose**: "Use `ParallelAgent` when: For scenarios prioritizing speed and involving independent, resource-intensive tasks"

**Deterministic Execution**: Unlike LLM agents, parallel workflow agents operate deterministically, focusing purely on orchestration rather than decision-making logic.

## How It Functions

When `run_async()` is invoked, the parallel agent:

1. **Concurrent Launch**: Initiates all sub-agents simultaneously rather than sequentially
2. **Independent Branches**: Each sub-agent operates autonomously without automatic state sharing
3. **Result Collection**: Aggregates results after completion; order may be non-deterministic

## State Management Considerations

Critical insight: "sub-agents within a `ParallelAgent` run independently. If you _need_ communication or data sharing between these agents, you must implement it explicitly."

### Communication Approaches

- **Shared InvocationContext**: Pass a common data store with careful concurrency control
- **External State Management**: Leverage databases or message queues
- **Post-Processing**: Coordinate results after execution completes

## Practical Example Architecture

The documentation demonstrates a parallel web research system combining:
- Three independent `LlmAgent` researchers (renewable energy, EVs, carbon capture)
- A `ParallelAgent` orchestrating concurrent execution
- A synthesis `LlmAgent` merging results sequentially

This pattern leverages parallel execution for research tasks, then synthesizes findings afterward—"significantly reducing overall processing time."

## Supported Platforms

Available in Python (v0.1.0+), TypeScript (v0.2.0+), Go (v0.1.0+), and Java (v0.2.0+).
