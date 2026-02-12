# Agents Overview

Source: https://google.github.io/adk-docs/agents/

## Main Content Summary

The Agents page introduces the foundational concepts of ADK agents. Per the documentation: "An **Agent** is a self-contained execution unit designed to act autonomously to achieve specific goals."

All agents in ADK extend from the `BaseAgent` class, with three primary categories:

### Core Agent Categories

1. **LLM Agents** (`LlmAgent`, `Agent`) - Leverage language models for reasoning, natural language understanding, and dynamic tool selection
2. **Workflow Agents** (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) - Control deterministic execution patterns without LLM-based flow control
3. **Custom Agents** - Direct `BaseAgent` extensions for specialized logic and unique integrations

## Sub-pages Under Agents Section

- LLM agents
- Workflow agents
  - Sequential agents
  - Loop agents
  - Parallel agents
- Custom agents
- Multi-agent systems
- Agent Config

## Key Navigation Structure

The Agents section sits within **Build Agents** and connects to related sections including Models for Agents, Tools and Integrations, and Custom Tools. The page emphasizes that sophisticated applications combine multiple agent types in multi-agent architectures for optimal capability.
