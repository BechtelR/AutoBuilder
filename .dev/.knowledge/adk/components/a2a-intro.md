# Introduction to A2A - Agent Development Kit

## Overview

The Agent2Agent (A2A) Protocol enables specialized agents to collaborate in complex agentic systems. ADK simplifies building and connecting agents using this standardized communication framework.

## When to Use A2A vs. Local Sub-Agents

### A2A Use Cases

Consider A2A when:
- Agents operate as "separate, standalone services"
- Different teams or organizations maintain the agent
- Integration across "different programming languages or agent frameworks" is needed
- A "strong, formal contract" between components is desired

**Concrete Examples:**
- Integrating third-party services (e.g., external financial data providers)
- Microservices architecture with independent services (Order Processing, Inventory, Shipping)
- Cross-language communication (Python core with Java legacy systems)
- Platform-level API enforcement across teams

### Local Sub-Agent Use Cases

Prefer local sub-agents for:
- Internal code organization and modular functions
- "High-frequency, low-latency operation" tightly coupled with main agent execution
- Direct access to shared memory and internal state
- Simple helper functions within the same agent

## A2A Workflow in ADK

**Two-Step Process:**

1. **Exposing:** Convert an existing ADK agent into an A2AServer, making it accessible over a network
2. **Consuming:** Use RemoteA2aAgent component to connect to the exposed agent as a client-side proxy

From the developer's perspective, "interacting with the remote agent feels just like interacting with a local tool or function."

## Architecture Components

**Exposing Side:**
- A2A Server (ADK Component)
- Your Agent Code (Now Accessible)

**Consuming Side:**
- Root Agent (Existing Code)
- RemoteA2aAgent (ADK Client Proxy)

## Practical Example: Customer Service & Product Catalog

**Before A2A:** Disconnected agents lacking standardized communication

**After A2A:** Customer Service Agent uses RemoteA2aAgent to query Product Catalog Agent seamlessly through A2A Server

This arrangement enables "clear separation of concerns and easy integration of specialized agents."

## Next Steps

Progress to the Quickstart: Exposing Your Agent guide for implementation details across Python, TypeScript, Go, and Java.

---

**Source**: https://google.github.io/adk-docs/a2a/intro/
**Downloaded**: 2026-02-11
