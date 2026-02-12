# Model Context Protocol (MCP) Tools Documentation Summary

## Overview
MCP is an open standard enabling Large Language Models to communicate with external applications, data sources, and tools through a client-server architecture. The documentation covers two primary integration patterns with ADK (Agent Development Kit).

## Key Integration Patterns

### Pattern 1: ADK as MCP Client
The `McpToolset` class allows ADK agents to consume tools from external MCP servers. As described in the documentation: "When you include an `McpToolset` instance in your agent's `tools` list, it automatically handles the interaction with the specified MCP server."

**Connection Types:**
- **StdioConnectionParams**: Local process communication via standard input/output
- **SseConnectionParams**: Server-Sent Events for remote servers

### Pattern 2: MCP Server Exposing ADK Tools
Developers can wrap existing ADK tools in a custom MCP server, making them accessible to any MCP client. This involves:
- Instantiating ADK tools
- Implementing MCP `list_tools()` handler
- Implementing MCP `call_tool()` handler using the `adk_to_mcp_tool_type` conversion utility

## Critical Deployment Requirements

**Synchronous Agent Definition**: "When deploying agents with MCP tools, the agent and its McpToolset must be defined **synchronously** in your `agent.py` file."

Asynchronous patterns used in development environments (like `adk web`) don't work for production deployments on Cloud Run, GKE, or Vertex AI Agent Engine.

## Deployment Patterns

1. **Self-Contained Stdio**: Package MCP servers (npm or Python modules) directly in agent containers
2. **Remote HTTP Servers**: Deploy MCP as separate Cloud Run services using Streamable HTTP
3. **Kubernetes Sidecars**: Run MCP servers as sidecar containers in GKE deployments

## Security Best Practices

- Filter MCP tools using `tool_filter` to limit exposed functionality
- Restrict file paths for filesystem operations to specific directories
- Implement authentication headers for remote connections
- Monitor and validate tool inputs
- Use read-only tool filters in production environments

## Key Considerations

The documentation emphasizes that MCP establishes "stateful, persistent connections between a client and server instance" rather than stateless REST APIs, creating challenges for scaling and deployment requiring careful infrastructure considerations like load balancing and session affinity.

---

*Source: https://google.github.io/adk-docs/tools-custom/mcp-tools/*
*Downloaded: 2026-02-11*
