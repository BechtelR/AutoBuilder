# Claude Models for ADK Agents - Documentation Summary

## Overview
The Agent Development Kit supports integrating Anthropic's Claude models into Java ADK applications through the `Claude` wrapper class. This capability is available in ADK Java v0.2.0 and later.

## Key Integration Methods

**Direct API Access:** Users can connect Claude models using an Anthropic API key directly, or access them through Google Cloud Vertex AI services.

**Alternative Approaches:** Python developers can leverage Claude models through the LiteLLM library, while those using Vertex AI can access "third-party models on Vertex AI" including Anthropic Claude.

## Prerequisites

1. **Dependencies:** The Java ADK's Claude wrapper relies on classes from Anthropic's official Java SDK, typically included as transitive dependencies.

2. **API Key:** Developers must obtain an API key from Anthropic and manage it securely through a secret manager.

## Implementation Pattern

The basic setup involves:
- Creating an `AnthropicOkHttpClient` configured with your API credentials
- Instantiating the `Claude` model wrapper with a model identifier (e.g., "claude-3-7-sonnet-latest")
- Passing the Claude instance to an `LlmAgent` builder

## Code Structure
The example demonstrates creating an agent with custom instructions: *"You are a helpful AI assistant powered by Anthropic Claude."* This agent can then be used for various tasks within the ADK framework.

---

*Source: (https://google.github.io/adk-docs/agents/models/anthropic/)*
*Downloaded: 2026-02-11*
