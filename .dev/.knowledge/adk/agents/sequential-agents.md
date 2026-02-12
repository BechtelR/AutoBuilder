# Sequential Agents

Source: https://google.github.io/adk-docs/agents/workflow-agents/sequential-agents/

## Overview
Sequential agents are workflow components from Google's Agent Development Kit that execute sub-agents in a strict, predetermined order. As stated in the documentation, "The `SequentialAgent` is a workflow agent that executes its sub-agents in the order they are specified."

## Key Characteristics

**Deterministic Execution**: These agents follow a fixed sequence without LLM-based decision-making. The documentation notes that "workflow agents are not powered by an LLM, and is thus deterministic in how it executes."

**Shared Context**: All sub-agents receive the same invocation context, enabling data sharing through session state and temporary namespaces.

## How It Works

The sequential execution process follows three steps:
1. Iterates through sub-agents in specified order
2. Calls each sub-agent's Run Async method sequentially
3. Passes output from each agent to the next via state using Output Key parameters

## Example Use Case

The documentation provides a code development pipeline with three stages:
- **Code Writer Agent**: Generates initial code from specifications
- **Code Reviewer Agent**: Evaluates generated code for quality
- **Code Refactorer Agent**: Improves code based on review feedback

This demonstrates how "output from each sub-agent is passed to the next by storing them in state."

## Implementation Languages

Supported across Python (v0.1.0), TypeScript (v0.2.0), Go (v0.1.0), and Java (v0.2.0).
