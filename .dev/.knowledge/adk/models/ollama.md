# Ollama Model Host for ADK Agents - Documentation Summary

## Overview
Ollama enables hosting and running open-source models locally. The Agent Development Kit integrates with Ollama through the LiteLLM connector library, supporting ADK Python v0.1.0 and later.

## Key Setup Instructions

**Basic Implementation:**
Create agents using LiteLLM wrapper with the syntax: `LiteLlm(model="ollama_chat/gemma3:latest")`. Always use the `ollama_chat` interface rather than `ollama` to avoid infinite tool call loops and context issues.

**Environment Configuration:**
Set `OLLAMA_API_BASE="http://localhost:11434"` as an environment variable, as LiteLLM relies on this for all API calls beyond generation requests.

## Model Selection Guidelines

For tool-reliant agents, select models with explicit tool support from Ollama's repository. Verify capabilities using: `ollama show mistral-small3.1` and confirm "tools" appears under the Capabilities section.

**Template Customization:**
Some default model templates aggressively prompt function calling. You can extract and modify templates using `ollama show --modelfile` and replace prompts that unconditionally request function calls with conditional logic determining whether a function is actually necessary.

## Alternative: OpenAI Provider

Set `OPENAI_API_BASE=http://localhost:11434/v1` and `OPENAI_API_KEY=anything`, then use `LiteLlm(model="openai/mistral-small3.1")`. Note the `/v1` suffix in the API base URL.

## Debugging
Enable LiteLLM debug mode with `litellm._turn_on_debug()` to inspect requests sent to the Ollama server, displaying formatted curl commands for troubleshooting.

---

*Source: https://google.github.io/adk-docs/agents/models/ollama/*
*Downloaded: 2026-02-11*
