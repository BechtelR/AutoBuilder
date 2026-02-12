# Custom Agents

Source: https://google.github.io/adk-docs/agents/custom-agents/

## Overview

Custom agents in the Agent Development Kit provide "ultimate flexibility" by allowing developers to inherit directly from `BaseAgent` and implement their own orchestration logic beyond predefined workflow patterns.

## Core Concept

A custom agent implements the `_run_async_impl` method (or language equivalent) as an asynchronous generator that:
- Calls sub-agents and yields their events
- Manages session state for inter-agent communication
- Implements conditional logic and dynamic agent selection

## Key Use Cases

Custom agents address scenarios including:
- **Conditional Logic**: Executing different sub-agents based on runtime results
- **Complex State Management**: Sophisticated data flow between workflow steps
- **External Integrations**: Incorporating API calls and custom libraries
- **Dynamic Agent Selection**: Choosing which agents run based on evaluation
- **Unique Patterns**: Orchestration beyond sequential, parallel, or loop structures

## Implementation Pattern

The documentation provides a `StoryFlowAgent` example demonstrating:

1. **Initialization**: Store sub-agents as instance attributes; pass top-level agents to parent constructor
2. **Custom Logic**: Implement control flow using standard language constructs
3. **State Management**: Read/write `ctx.session.state` for inter-agent data passing
4. **Conditional Execution**: Check state values to determine workflow branches

## Practical Example

The StoryFlowAgent workflow:
- Generates initial story
- Runs critic-reviser loop (2 iterations)
- Performs grammar and tone checks sequentially
- **Conditionally regenerates** if tone is negative

This demonstrates the power of custom agents: conditional regeneration based on evaluation results, which standard workflows cannot express natively.

## Language Support

Custom agents are supported across: Python (v0.1.0+), TypeScript (v0.2.0+), Go (v0.1.0+), and Java (v0.1.0+).
