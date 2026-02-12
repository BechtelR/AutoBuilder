# Model Context Protocol (MCP) - Agent Development Kit

## Overview

The Model Context Protocol (MCP) is an open standard that "standardizes how Large Language Models (LLMs) like Gemini and Claude communicate with external applications, data sources, and tools."

## How MCP Works

MCP employs a client-server architecture where "data (resources), interactive templates (prompts), and actionable functions (tools) are exposed by an MCP server and consumed by an MCP client."

## MCP Tools in ADK

The Agent Development Kit supports both using and building MCP tools:

- **Using Existing MCP Servers**: ADK agents can function as MCP clients, consuming tools from external MCP servers
- **Exposing ADK Tools via MCP**: Build MCP servers that wrap ADK tools for broader accessibility

Developers can find pre-built MCP tools in the Tools and Integrations section and design patterns in the MCP Tools documentation.

## FastMCP Integration

"ADK uses FastMCP to handle all the complex MCP protocol details and server management, so you can focus on building great tools." The framework is designed to be Pythonic, often requiring only function decoration.

## Google Cloud Genmedia MCP Servers

MCP Tools for Genmedia Services provides open-source MCP servers integrating Google Cloud generative media capabilities including Imagen, Veo, Chirp 3 HD voices, and Lyria. Both ADK and Genkit frameworks provide built-in support for these tools.

## Supported Languages

MCP functionality is supported across Python, TypeScript, Go, and Java implementations of ADK.

---

**Source**: https://google.github.io/adk-docs/mcp/
**Downloaded**: 2026-02-11
