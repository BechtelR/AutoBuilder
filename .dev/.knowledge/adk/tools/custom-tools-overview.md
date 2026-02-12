# Custom Tools for ADK - Documentation Summary

## Overview
Custom Tools in ADK are programming functions with structured input/output that agents call to perform actions. They extend agent capabilities by enabling database queries, API requests, web searches, code execution, and RAG operations.

## Key Characteristics
Tools are "action-oriented" components that "execute predefined logic" without independent reasoning. The agent's LLM decides *which* tool to use and *when*, while the tool executes its designated function.

## Tool Types Supported
1. **Function Tools** - User-created custom functions, long-running async operations, or agents-as-tools
2. **Built-in Tools** - Framework-provided tools (Google Search, Code Execution, RAG)
3. **Third-Party Tools** - Integrated external library tools

## Agent Workflow
The agent follows a 5-step process: reasoning about available tools → selection based on docstrings → invocation with LLM-generated arguments → observation of output → incorporation into ongoing reasoning.

## Tool Context Features
The ToolContext parameter provides access to:
- **State Management** - Read/write session state with prefixes (app:*, user:*, session-specific, temp:*)
- **Event Actions** - Control agent flow (skip_summarization, transfer_to_agent, escalate)
- **Authentication** - Handle credentials and auth flows
- **Data Access** - list/load/save artifacts and search memory

## Best Practices
- Reference tools by function name in agent instructions
- Provide clear docstrings describing tool purpose and return values
- Explicitly instruct agents how to handle different return values (success/error)
- Describe sequential tool usage workflows in instructions
- Don't include tool_context in docstrings since it's framework-injected

## Toolsets
The BaseToolset interface enables grouping and dynamically providing tools to agents, allowing contextual tool selection based on application state.

---

*Source: https://google.github.io/adk-docs/tools-custom/*
*Downloaded: 2026-02-11*
