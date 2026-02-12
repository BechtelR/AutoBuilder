# Part 4: Understanding RunConfig - Agent Development Kit

## Overview

This documentation section covers RunConfig parameters that control ADK Bidi-streaming sessions. RunConfig manages response formats, session lifecycles, and production constraints for streaming applications.

## Key Topics Covered

### RunConfig Parameter Quick Reference

A comprehensive table documents configuration options including:

- **response_modalities**: Controls output format (TEXT or AUDIO)
- **streaming_mode**: Selects BIDI or SSE mode
- **session_resumption**: Enables automatic reconnection
- **context_window_compression**: Enables unlimited session duration
- **max_llm_calls**: Limits total LLM calls per session
- **save_live_blob**: Persists audio/video streams
- **custom_metadata**: Attaches metadata to invocation events
- **support_cfc**: Enables compositional function calling (experimental)

Additional audio/video configurations are covered in Part 5.

### Response Modalities

"Only one response modality is supported per session" - you must choose either TEXT or AUDIO at startup and cannot switch mid-session. ADK automatically defaults to AUDIO when not specified. While response modality constrains output, you can always send text, voice, or video input regardless.

### StreamingMode: BIDI vs SSE

Two distinct streaming protocols are supported:

- **BIDI (StreamingMode.BIDI)**: WebSocket-based Live API connection enabling real-time bidirectional communication, required for audio/video interactions
- **SSE (StreamingMode.SSE)**: HTTP-based standard Gemini API using Server-Sent Events for text-only streaming

BIDI enables true simultaneous sending/receiving while SSE follows traditional request-response patterns.

#### Progressive SSE Streaming

When using SSE mode, progressive SSE streaming is enabled by default, providing content ordering preservation, intelligent text merging, and deferred function execution. This can be disabled via the `ADK_DISABLE_PROGRESSIVE_SSE_STREAMING` environment variable if needed.

### Live API Sessions vs ADK Sessions

The documentation clarifies a crucial distinction:

- **ADK Session**: Persistent conversation storage created via SessionService, survives across multiple run_live() calls
- **Live API session**: Ephemeral streaming context created during run_live(), destroyed when streaming ends, subject to platform duration limits

"Session continuity is maintained through ADK Session's persistent storage" across WebSocket reconnections and application restarts.

### Session Duration Limits by Platform

**Gemini Live API:**
- Audio-only: 15 minutes without compression
- Audio+video: 2 minutes without compression
- Concurrent sessions: 50 (Tier 1) to 1,000 (Tier 2+)

**Vertex AI Live API:**
- All sessions: 10 minutes without compression
- Concurrent sessions: Up to 1,000 per project

### Live API Session Resumption

The Live API enforces approximately 10-minute connection timeouts. Session resumption allows migrating sessions across multiple WebSocket connections transparently. When enabled, ADK automatically handles reconnection logic—"detecting connection closures, caching resumption handles, and reconnecting seamlessly in the background."

ADK manages the ADK-to-Live API connection; developers remain responsible for client connections to their applications.

### Context Window Compression

Compression uses sliding-window approaches to manage token limits and extends session duration to unlimited time, removing platform duration caps. However, it summarizes earlier conversation history rather than retaining full verbatim records.

Configuration requires setting `trigger_tokens` (typically 70-80% of context window) and `target_tokens` (typically 60-70% of context window).

### Best Practices for Session Management

**Essential**: Enable session resumption for production applications to handle automatic connection timeouts transparently.

**Recommended**: Enable context window compression only when sessions need to exceed platform duration limits, as it adds latency and may reduce conversational nuance.

**Optional**: Monitor session duration only if not using context window compression.

### Concurrent Session Quotas

Two architectural patterns manage quota constraints:

1. **Direct Mapping**: Simple 1:1 user-to-session mapping suitable for applications staying below quota limits
2. **Session Pooling with Queueing**: Queue waiting users when quota is reached, starting sessions as slots become available

### Miscellaneous Controls

- **max_llm_calls**: Caps LLM invocations (does not apply to BIDI streaming)
- **save_live_blob**: Persists audio/video for debugging and compliance
- **custom_metadata**: Attaches application-specific key-value metadata to events for analytics and routing
- **support_cfc**: Enables compositional function calling (experimental, Gemini 2.x only, routes through Live API internally)

## Production Considerations

The documentation emphasizes that developers should understand platform-specific quotas, design architectures within concurrent session limits, implement appropriate queueing strategies, and monitor quota usage proactively. RunConfig mastery enables "production-ready streaming applications that balance feature richness with operational constraints."

---

**Source**: https://google.github.io/adk-docs/streaming/dev-guide/part4/
**Downloaded**: 2026-02-11
