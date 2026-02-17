# Tools
> Base: https://google.github.io/adk-docs

- **Function tools** `/tools-custom/function-tools/` — Python function → FunctionTool; auto-generates schema from docstring
- **MCP tools** `/tools-custom/mcp-tools/` — Model Context Protocol server integration
- **OpenAPI tools** `/tools-custom/openapi-tools/` — auto-generate tools from OpenAPI spec
- **Authentication** `/tools-custom/authentication/` — OAuth2, API keys, credential management for tools
- **Performance** `/tools-custom/performance/` — tool caching, optimization strategies
- **Confirmation** `/tools-custom/confirmation/` — human-in-the-loop tool confirmation
- **Limitations** `/tools/limitations/` — tool count limits, naming constraints
- **Integrations** `/integrations/` — built-in Google service integrations

## Key Classes
`FunctionTool` `BaseTool` `MCPToolset` `OpenAPIToolset` `ToolContext`

## See Also
→ ERRATA.md #7: FunctionTool import path
→ callbacks.md: before_tool_callback / after_tool_callback
