# Workflow Agents Overview

Source: https://google.github.io/adk-docs/agents/workflow-agents/

## Core Concept

The documentation introduces **workflow agents** as specialized components that orchestrate the execution flow of sub-agents. According to the material, these agents "control the execution flow of its sub-agents" and manage "how and when other agents run."

## Key Characteristics

Workflow agents differ fundamentally from LLM agents in their operational approach:

- **Predefined Logic**: They operate based on predetermined rules rather than dynamic LLM reasoning
- **Deterministic Execution**: The documentation states they produce "deterministic and predictable execution patterns"
- **No LLM Consultation**: Unlike LLM agents, workflow agents don't consult language models for orchestration decisions

## Three Primary Types

The documentation identifies three workflow agent variants:

1. **Sequential Agents** - Execute sub-agents serially, one after another
2. **Loop Agents** - Repeatedly execute sub-agents until specific termination conditions are satisfied
3. **Parallel Agents** - Execute multiple sub-agents simultaneously

## Primary Benefits

The material emphasizes three advantages:

- **Predictability**: Execution flow is guaranteed based on agent type and configuration
- **Reliability**: Tasks run consistently in required patterns
- **Structure**: Enables complex process composition through clear control frameworks

## Implementation Flexibility

An important feature highlighted is that sub-agents within workflow agents can be any agent type, including LLM agents, allowing teams to "combine structured process control with flexible, LLM-powered task execution."

The documentation supports Python, TypeScript, Go, and Java implementations.
