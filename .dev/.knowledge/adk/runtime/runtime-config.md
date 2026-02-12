# Runtime Configuration - ADK Documentation

Source: https://google.github.io/adk-docs/runtime/runconfig/

## Overview

`RunConfig` defines runtime behavior for agents in the Agent Development Kit, controlling speech settings, streaming modes, function calling, artifact saving, and LLM call limits.

## Class Definition

The `RunConfig` class holds configuration parameters across supported languages:

- **Python ADK**: Uses Pydantic for validation
- **TypeScript ADK**: Standard interface with compiler type safety
- **Go ADK**: Mutable structs by default
- **Java ADK**: Immutable data classes

## Core Runtime Parameters

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `speech_config` | Optional[SpeechConfig] | None | Configures voice synthesis and language settings |
| `response_modalities` | List[str] | None | Specifies output channels (TEXT, AUDIO) |
| `save_input_blobs_as_artifacts` | Boolean | False | Preserves input data for debugging |
| `support_cfc` | Boolean | False | Enables Compositional Function Calling (experimental) |
| `streaming_mode` | StreamingMode | NONE | Sets streaming behavior |
| `output_audio_transcription` | Optional[AudioTranscriptionConfig] | None | Configures audio output transcription |
| `max_llm_calls` | Integer | 500 | Bounds total LLM invocations per run |

## Streaming Modes

- **NONE**: Complete responses delivered as units
- **SSE**: Server-sent events for one-way streaming
- **BIDI**: Bidirectional simultaneous communication

## Speech Configuration

Speech support requires specifying:

```
SpeechConfig:
  - voice_config: Voice selection (PrebuiltVoiceConfig with voice_name)
  - language_code: ISO 639 code (e.g., "en-US")
```

## Validation Rules

- Extremely large `max_llm_calls` values are prevented to avoid resource issues
- Zero or negative values allow unbounded LLM interactions
- Python uses Pydantic validation; Java/TypeScript rely on static typing

## Usage Examples

**Basic configuration** limits agent to 100 non-streaming LLM calls.

**SSE streaming** enables responsive experiences with up to 200 calls.

**Speech-enabled agents** configure voice synthesis, audio/text output, artifact saving, and CFC support with 1000 call limit.

**CFC support** requires `StreamingMode.SSE` and invokes the LIVE API (experimental).
