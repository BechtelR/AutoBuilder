# Vertex AI Hosted Models for ADK Agents

## Overview
This documentation covers integrating Vertex AI-hosted models with the Agent Development Kit (ADK). Users can deploy various models to Vertex AI Endpoints and use them directly with LlmAgent.

## Setup Requirements

**Environment Configuration:**
- Enable Application Default Credentials via `gcloud auth application-default login`
- Set `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` environment variables
- **Critical:** Set `GOOGLE_GENAI_USE_VERTEXAI=TRUE` to route requests through Vertex AI

## Supported Model Types

### Model Garden Deployments
Deploy open and proprietary models from Vertex AI Model Garden to endpoints. Pass the full resource string: `"projects/PROJECT_ID/locations/LOCATION/endpoints/ENDPOINT_ID"`

Example with Llama 3:
```python
agent_llama3_vertex = LlmAgent(
    model="projects/YOUR_PROJECT_ID/locations/us-central1/endpoints/YOUR_LLAMA3_ENDPOINT_ID",
    name="llama3_vertex_agent",
    instruction="You are a helpful assistant based on Llama 3..."
)
```

### Fine-tuned Model Endpoints
Deploy custom fine-tuned models using the same endpoint resource string format.

### Anthropic Claude on Vertex AI
**Python:** Requires explicit registration before agent creation:
```python
from google.adk.models.anthropic_llm import Claude
from google.adk.models.registry import LLMRegistry
LLMRegistry.register(Claude)

agent_claude = LlmAgent(
    model="claude-3-sonnet@20240229",
    name="claude_vertexai_agent"
)
```

**Java:** Directly instantiate the Claude wrapper with VertexBackend configuration:
```java
AnthropicClient client = AnthropicOkHttpClient.builder()
    .backend(VertexBackend.builder()
        .region("us-east5")
        .project("your-gcp-project-id")
        .googleCredentials(GoogleCredentials.getApplicationDefault())
        .build())
    .build();

LlmAgent agent = LlmAgent.builder()
    .model(new Claude(claudeModelVertexAi, anthropicClient))
    .name("claude_vertexai_agent")
    .build();
```

### Open Models via MaaS
Access open-source models like Meta Llama using LiteLLM wrapper:
```python
from google.adk.models.lite_llm import LiteLlm

agent_llama = LlmAgent(
    model=LiteLlm(model="vertex_ai/meta/llama-4-scout-17b-16e-instruct-maas"),
    name="llama4_agent"
)
```

## Key Integration Points

- **Registry Pattern:** Python ADK automatically recognizes `gemini-*` strings and standard endpoint URIs; third-party models require manual registration
- **Authentication:** Java requires proper ADC configuration for credential handling
- **Configuration:** Optional `GenerateContentConfig` parameters (e.g., `max_output_tokens`) can customize behavior

---

*Source: https://google.github.io/adk-docs/agents/models/vertex/*
*Downloaded: 2026-02-11*
