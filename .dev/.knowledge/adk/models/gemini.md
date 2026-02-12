# Google Gemini Models for ADK Agents - Documentation Summary

## Overview
The Agent Development Kit supports Google Gemini generative AI models with extensive feature support including code execution, Google Search, context caching, computer use, and the Interactions API.

## Getting Started

Basic implementation example for Python:
```python
from google.adk.agents import LlmAgent

agent_gemini_flash = LlmAgent(
    model="gemini-2.5-flash",
    name="gemini_flash_agent",
    instruction="You are a fast and helpful Gemini assistant.",
)
```

Similar patterns exist for TypeScript, Go, and Java implementations.

## Authentication Methods

### Google AI Studio
- **Approach:** API Key-based
- **Setup:** Obtain key from [Google AI Studio](https://aistudio.google.com/apikey)
- **Configuration:** Set `GOOGLE_API_KEY` and `GOOGLE_GENAI_USE_VERTEXAI=FALSE` environment variables

### Google Cloud Vertex AI
Three authentication approaches:

1. **User Credentials (Local Development):** Uses `gcloud auth application-default login` with project and location environment variables

2. **Express Mode:** Simplified API-key setup for rapid prototyping using Vertex AI Express Mode credentials

3. **Service Account (Production):** Recommended for deployed applications; use service account keys or Workload Identity

## Key Considerations

**Voice/Video Streaming:** Requires models supporting the Gemini Live API; check official documentation for compatible model IDs.

**Security:** "Service account credentials or API keys are powerful credentials. Never expose them publicly."

## Gemini Interactions API

Available in Python v1.21.0+, this feature provides stateful conversation capabilities using `previous_interaction_id` instead of full history transmission.

**Enable via:**
```python
model=Gemini(
    model="gemini-2.5-flash",
    use_interactions_api=True,
)
```

**Limitation:** Cannot mix custom function tools with built-in tools; use `bypass_multi_tools_limit=True` parameter to convert built-in tools to function-based alternatives.

## Error Handling

**Error 429 - RESOURCE_EXHAUSTED:** Occurs when request volume exceeds allocated capacity. Solutions include requesting higher quota limits or enabling client-side retries through `HttpRetryOptions` configuration.

---

*Source: https://google.github.io/adk-docs/agents/models/google-gemini/*
*Downloaded: 2026-02-11*
