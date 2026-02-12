# LiteLLM Model Connector for ADK Agents

## Overview

LiteLLM is a Python library providing a standardized, "OpenAI-compatible interface to over 100+ LLMs" from various providers including OpenAI, Anthropic, and Cohere. It enables both remote and locally-hosted model access through the ADK framework.

## Setup Instructions

### 1. Installation
```
pip install litellm
```

### 2. Environment Configuration
Set provider-specific API keys as environment variables:

- **OpenAI**: `export OPENAI_API_KEY="YOUR_KEY"`
- **Anthropic**: `export ANTHROPIC_API_KEY="YOUR_KEY"`
- Other providers require their respective environment variables (see LiteLLM documentation)

### Windows UTF-8 Note
To prevent `UnicodeDecodeError` on Windows, set `PYTHONUTF8=1` before running your agent.

## Basic Usage Example

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

# OpenAI GPT-4o example
agent_openai = LlmAgent(
    model=LiteLlm(model="openai/gpt-4o"),
    name="openai_agent",
    instruction="You are a helpful assistant powered by GPT-4o."
)

# Anthropic Claude Haiku example
agent_claude = LlmAgent(
    model=LiteLlm(model="anthropic/claude-3-haiku-20240307"),
    name="claude_direct_agent",
    instruction="You are an assistant powered by Claude Haiku."
)
```

## Use Cases

- Remote model hosting through various API providers
- Local model hosting (compatible with Ollama and vLLM)
- Cost optimization and privacy-focused deployments

---

*Source: https://google.github.io/adk-docs/agents/models/litellm/*
*Downloaded: 2026-02-11*
