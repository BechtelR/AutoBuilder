# vLLM Model Host for ADK Agents - Documentation Extract

## Overview

The Agent Development Kit supports vLLM, a tool for efficiently hosting and serving models through an OpenAI-compatible API endpoint. This integration enables developers to leverage self-hosted models within ADK agents.

## Setup Requirements

**Two primary setup steps are required:**

1. **Model Deployment**: Deploy your selected model using vLLM and note the API base URL (e.g., `https://your-vllm-endpoint.run.app/v1`). Critical configuration includes enabling OpenAI-compatible tool/function calling through flags such as `--enable-auto-tool-choice` and appropriate `--tool-call-parser` settings depending on your model.

2. **Authentication Configuration**: Determine your endpoint's authentication method, which may involve API keys or bearer tokens.

## Integration Implementation

The documentation provides a Python code example demonstrating vLLM integration with ADK agents using the LiteLLM library:

**Key implementation components:**
- Instantiate an `LlmAgent` with a `LiteLlm` model instance
- Configure the model parameter with your endpoint's model identifier
- Set `api_base` to your vLLM deployment URL
- Supply authentication through either `extra_headers` (for bearer tokens from gcloud) or `api_key` parameters
- Include standard agent parameters like `name` and `instruction`

The example demonstrates authentication via gcloud identity tokens for Cloud Run deployments, with fallback handling for unsecured endpoints.

**Compatibility Note**: "Supported in ADK Python v0.1.0"

---

*Source: https://google.github.io/adk-docs/agents/models/vllm/*
*Downloaded: 2026-02-11*
