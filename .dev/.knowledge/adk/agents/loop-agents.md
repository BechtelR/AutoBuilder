# Loop Agents

Source: https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/

## Overview

The `LoopAgent` is a workflow agent that "**_repeatedly runs_ a sequence of agents** for a specified number of iterations or until a termination condition is met." It's designed for workflows requiring iterative refinement, such as revising code or improving documents.

## Key Characteristics

**Deterministic Execution**: Unlike LLM-powered agents, workflow agents execute deterministically based on their configuration, not language model decisions.

**Termination Mechanisms**: The LoopAgent requires explicit termination strategies:
- **Max Iterations**: Sets a hard limit on loop cycles
- **Escalation from Sub-agents**: Sub-agents can signal completion through custom events, flags, or return values

## How It Works

When `RunAsync` is called, the LoopAgent:

1. Iterates through sub-agents sequentially
2. Calls each sub-agent's `RunAsync` method
3. Checks termination conditions before continuing

## Practical Example: Document Refinement

A common use case involves two agents in a loop:

- **Writer Agent** (LlmAgent): Generates or refines drafts
- **Critic Agent** (LlmAgent): Evaluates quality and signals completion

The critic can return a "STOP" signal when quality thresholds are met, preventing infinite loops.

## Language Support

Implementations available for: Python, TypeScript, Go, and Java (versions v0.1.0+)

## Core Configuration

```
LoopAgent(sub_agents=[Agent1, Agent2], max_iterations=5)
```

The `max_iterations` parameter acts as a safety boundary, ensuring the process terminates regardless of other conditions.
