# Part 1: Introduction to ADK Bidi-streaming

## Overview

This documentation introduces Google's Agent Development Kit (ADK) framework for building real-time bidirectional streaming applications with Gemini models. The guide covers streaming fundamentals, Live API technology, ADK architecture, and the complete application lifecycle.

## Key Concepts

### What is Bidi-streaming?

Bidi-streaming represents a shift from traditional "ask-and-wait" AI interactions to real-time, two-way communication where both humans and AI can speak, listen, and respond simultaneously. Key characteristics include:

- **Two-way Communication**: Continuous data exchange without waiting for complete responses
- **Responsive Interruption**: Users can interrupt mid-response, like natural conversation
- **Multimodal Excellence**: Processes text, audio, and video simultaneously through one connection

### Live API Technology

ADK's streaming capabilities are powered by two platforms:

1. **Gemini Live API** (Google AI Studio) - Best for rapid prototyping with minimal setup
2. **Vertex AI Live API** (Google Cloud) - Designed for production deployments with enterprise features

Core capabilities include:
- Multimodal streaming (audio, video, text)
- Voice Activity Detection (VAD)
- Immediate responses with minimal latency
- Tool integration with seamless function calling
- Session management and resumption

## ADK Architecture

### High-Level Components

**Developer-Provided:**
- Web/Mobile frontend
- WebSocket/SSE server (e.g., FastAPI)
- Custom Agent definition

**ADK-Provided:**
- `LiveRequestQueue`: Message buffer for user inputs
- `Runner`: Execution engine orchestrating sessions
- `RunConfig`: Streaming behavior configuration

**Live API-Provided:**
- Real-time LLM processing and response generation

## Application Lifecycle

### Phase 1: Application Initialization (Startup)

Create reusable components:
- Define your `Agent` with model, tools, and instructions
- Create a `SessionService` for conversation persistence
- Create a `Runner` connecting agent and sessions

### Phase 2: Session Initialization (Per User Connection)

Set up per-session resources:
- Get or create ADK `Session` (handles conversation history)
- Create `RunConfig` (modality preferences, transcription settings)
- Create `LiveRequestQueue` (message channel to agent)

### Phase 3: Bidirectional Streaming (Active Communication)

Concurrent data flow:
- **Upstream**: User messages flow through `LiveRequestQueue` to agent
- **Downstream**: Agent events stream back via `run_live()` async generator

### Phase 4: Session Termination

Clean closure:
- Call `LiveRequestQueue.close()` to signal end
- Exit event loop gracefully

## FastAPI Implementation Pattern

The standard pattern uses concurrent upstream/downstream tasks:

```python
async def upstream_task():
    # Receive from WebSocket, send to LiveRequestQueue
    while True:
        data = await websocket.receive_text()
        content = types.Content(parts=[types.Part(text=data)])
        live_request_queue.send_content(content)

async def downstream_task():
    # Receive from run_live(), send to WebSocket
    async for event in runner.run_live(...):
        await websocket.send_text(
            event.model_dump_json(exclude_none=True, by_alias=True)
        )

try:
    await asyncio.gather(upstream_task(), downstream_task())
finally:
    live_request_queue.close()
```

## Real-World Applications

Bidi-streaming enables sophisticated agent applications across multiple domains:

- **Customer Service**: Video-enabled support with real-time problem diagnosis
- **E-commerce**: Interactive shopping with multimodal recommendations
- **Field Service**: Hands-free technician assistance with live video guidance
- **Healthcare**: Secure patient intake with video consultation
- **Financial Services**: Real-time portfolio analysis with screen sharing

## Platform Flexibility

One major advantage: ADK abstracts away platform differences through the `GOOGLE_GENAI_USE_VERTEXAI` environment variable:

- **Development**: Set to `FALSE` for Gemini Live API with free API keys
- **Production**: Set to `TRUE` for Vertex AI Live API with enterprise infrastructure

No code changes required when switching platforms—only environment configuration.

## Key Distinctions

**ADK Session** vs **Live API Session**:
- ADK `Session`: Persistent conversation storage (hours/days/months)
- Live API session: Transient streaming context (minutes/hours)

ADK initializes Live API sessions with historical context from persisted ADK sessions, then updates storage as new events occur.

## Prerequisites

Familiarity with these technologies is recommended:
- Python async programming (`async`/`await`, `asyncio`)
- Pydantic for data validation and serialization
- FastAPI or similar async web framework
- WebSocket protocols for bidirectional communication
- ADK's agent framework and session management

## Next Steps

The subsequent parts of this guide cover:
- **Part 2**: Sending messages via `LiveRequestQueue`
- **Part 3**: Event handling and processing
- **Part 4**: Advanced `RunConfig` options
- **Part 5**: Multimodal features (audio, images, video)

---

**Source**: https://google.github.io/adk-docs/streaming/dev-guide/part1/
**Downloaded**: 2026-02-11
