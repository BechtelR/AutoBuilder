# Part 2: Sending Messages with LiveRequestQueue

## Overview

This documentation page explains how to send messages to ADK streaming agents using `LiveRequestQueue`. The core concept is a unified interface for all message types through the `LiveRequest` container model.

## Key Components

### LiveRequest Structure

The `LiveRequest` model contains:
- **content**: Text-based content and structured data
- **blob**: Audio/video data and binary streams
- **activity_start/activity_end**: User activity signals
- **close**: Connection termination flag

"The `content` and `blob` fields are mutually exclusive—only one can be set per LiveRequest."

## Message Types

### send_content()

Sends text messages in turn-by-turn mode, triggering immediate response generation. Uses `Content` and `Part` objects from the google.genai.types library.

### send_realtime()

"The `send_realtime()` method sends binary data streams—primarily audio, image and video" using the `Blob` type for continuous streaming scenarios.

### Activity Signals

Manual voice activity control available when automatic VAD is disabled. Signals include:
- `send_activity_start()`: User begins speaking
- `send_activity_end()`: User finishes speaking

Used for push-to-talk interfaces or noisy environments requiring client-side control.

### Control Signals

The `close()` method provides graceful session termination. "In ADK Bidi-streaming, your application is responsible for sending the `close` signal explicitly."

## Concurrency & Best Practices

- Create `LiveRequestQueue` within async context to ensure correct event loop usage
- Uses synchronous send methods despite underlying async queue
- Provides FIFO ordering with no message coalescing
- Queue is unbounded by default; monitor depth in production scenarios

## Resource Management

Always call `close()` in BIDI mode to prevent zombie sessions on the Live API, even when exceptions occur.

---

**Source**: https://google.github.io/adk-docs/streaming/dev-guide/part2/
**Downloaded**: 2026-02-11
