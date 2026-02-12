# Memory: Long-Term Knowledge with MemoryService

## Overview

The `MemoryService` enables agents to retain and access information across multiple conversations. Unlike `Session` which tracks a single conversation, `MemoryService` provides a searchable archive of long-term knowledge.

**Key distinction:**
- **Session/State**: Short-term memory within one chat
- **MemoryService**: Searchable knowledge library from past interactions

## Core Responsibilities

The `BaseMemoryService` interface manages:

1. **Information Ingestion** (`add_session_to_memory`): Adds completed session contents to long-term storage
2. **Information Search** (`search_memory`): Retrieves relevant context based on queries

## Memory Service Comparison

| Feature | InMemoryMemoryService | VertexAiMemoryBankService |
|---------|----------------------|--------------------------|
| **Persistence** | None (session-only) | Yes (managed by Vertex AI) |
| **Use Case** | Prototyping, local testing | Production agents learning from interactions |
| **Memory Extraction** | Full conversation storage | "LLM-powered extraction of meaningful information" |
| **Search** | Basic keyword matching | Semantic search |
| **Setup** | None required | Requires Agent Engine instance |

## InMemoryMemoryService

Simple implementation requiring no configuration, ideal for development:

```python
from google.adk.memory import InMemoryMemoryService
memory_service = InMemoryMemoryService()
```

## Vertex AI Memory Bank

Production-grade service connecting to Google Cloud's managed memory platform.

### Prerequisites

- Google Cloud Project with Vertex AI API enabled
- Agent Engine instance created in Vertex AI
- Authentication via `gcloud auth application-default login`
- Environment variables: `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`

### Configuration

```bash
adk web path/to/agents --memory_service_uri="agentengine://<agent_engine_id>"
```

Or programmatically:

```python
from google.adk.memory import VertexAiMemoryBankService

memory_service = VertexAiMemoryBankService(
    project="PROJECT_ID",
    location="LOCATION",
    agent_engine_id=agent_engine_id
)
```

## Using Memory in Agents

Two built-in tools for memory retrieval:

- **PreloadMemory**: Automatically retrieves memories at conversation start
- **LoadMemory**: Agent-initiated retrieval when helpful

```python
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

agent = Agent(
    model=MODEL_ID,
    tools=[PreloadMemoryTool()]
)
```

## Automating Memory Extraction

Use callbacks to save sessions automatically:

```python
async def auto_save_callback(callback_context):
    await callback_context._invocation_context.memory_service.add_session_to_memory(
        callback_context._invocation_context.session
    )

agent = Agent(
    after_agent_callback=auto_save_callback
)
```

## Advanced: Multiple Memory Services

While framework configuration supports one service, agents can manually instantiate multiple services for different knowledge sources:

```python
class MultiMemoryAgent(Agent):
    def __init__(self, **kwargs):
        self.memory_service = InMemoryMemoryService()
        self.vertexai_service = VertexAiMemoryBankService(...)
```

This enables accessing conversational history alongside specialized knowledge bases within a single agent turn.

---

**Source**: https://google.github.io/adk-docs/sessions/memory/
**Downloaded**: 2026-02-11
