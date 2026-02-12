# Agent Development Kit - Function Tools Documentation

## Overview

The Agent Development Kit (ADK) enables developers to create custom function tools that integrate tailored functionality into agents. The framework automatically inspects Python function signatures—including name, docstring, parameters, type hints, and default values—to generate schemas for LLM understanding.

## Key Function Tool Concepts

### Function Signatures

**Required Parameters**: Parameters with type hints but no default values must be provided by the LLM when calling the tool. Parameter descriptions derive from the function's docstring.

**Optional Parameters**: Parameters with default values are optional. The standard Python approach uses default values, while `typing.Optional[SomeType]` or Python 3.10's `| None` syntax also signals optionality.

**Variadic Arguments**: The `*args` and `**kwargs` patterns are ignored by the ADK framework and unavailable to the LLM—use explicitly defined parameters instead.

### Return Types

Dictionary returns are preferred, as they structure responses with key-value pairs for clarity. Non-dictionary returns are automatically wrapped in a dictionary with a "result" key. The framework expects the LLM to interpret results, so descriptive returns work better than numeric codes.

## Passing Data Between Tools

Tools within a single agent turn share an `InvocationContext` with temporary (`temp:`) state variables, enabling sequential tool data passing during execution.

## Long Running Function Tools

For operations requiring significant processing time, `LongRunningFunctionTool` initiates tasks without blocking agent execution:

- **Initiation**: Your function starts the operation and optionally returns an ID
- **Initial Updates**: Results are packaged in a `FunctionResponse` sent to the LLM
- **Agent Pause**: The agent run pauses, allowing client decision-making
- **Progress Queries**: Clients can check operation status and send intermediate or final responses

**Warning**: These tools manage long-running tasks but don't perform them—implement separate servers for actual long processing.

## Agent-as-a-Tool Pattern

Agents can be wrapped as tools for other agents via `AgentTool`, enabling delegation workflows. This differs from sub-agents through customizable configuration options.

## Best Practices

- Minimize parameter count for reduced complexity
- Favor primitive data types over custom classes
- Choose meaningful names reflecting function purpose and parameter meaning
- Design for asynchronous operation to improve performance during parallel execution
- Include "status" keys in return dictionaries for operation outcome clarity

## Supported Languages

Function tools are available across ADK implementations:
- Python v0.1.0
- TypeScript v0.2.0
- Go v0.1.0
- Java v0.1.0

---

*Source: https://google.github.io/adk-docs/tools-custom/function-tools/*
*Downloaded: 2026-02-11*
