# Tool Limitations - Agent Development Kit

## Overview
This documentation page addresses constraints when implementing ADK tools within agent workflows, specifically focusing on the "one tool per agent limitation."

## Key Limitation: One Tool Per Agent

**Scope**: Applies exclusively to ADK Python v1.15.0 and lower (resolved in v1.16.0+)

### Affected Tools
Three specific tools cannot coexist with other tools in a single agent:
- Code Execution (Gemini API)
- Google Search (Gemini API)
- Vertex AI Search

As stated: "use of specific tools within an agent excludes the use of any other tools in that agent."

### Unsupported Pattern Example
Combining restricted tools with custom functions in one agent is not permitted, such as instantiating `BuiltInCodeExecutor()` alongside regular tools.

## Workaround Solutions

### Solution 1: AgentTool.create() Method
The recommended approach uses multiple specialized agents wrapped within a parent agent:

- Create separate agents for each restricted tool (SearchAgent, CodeAgent)
- Use `AgentTool.create()` to wrap subordinate agents
- The root agent delegates to specialized sub-agents through AgentTool references

This architecture supports multiple restricted tools through agent composition rather than direct tool combination.

### Solution 2: bypass_multi_tools_limit Parameter
Available in ADK Python, setting `bypass_multi_tools_limit=True` provides built-in workaround functionality for `GoogleSearchTool` and `VertexAiSearchTool`.

## Additional Constraint
Built-in tools cannot function within sub-agents, with the exception of Google Search and Vertex AI Search tools (due to the bypass workaround mentioned above).

---

*Source: https://google.github.io/adk-docs/tools/limitations/*
*Downloaded: 2026-02-11*
