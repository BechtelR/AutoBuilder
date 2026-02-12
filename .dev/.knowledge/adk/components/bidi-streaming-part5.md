# Part 5: Audio, Images, and Video - Agent Development Kit

## Audio Capabilities

The Live API enables natural voice conversations with sub-second latency through bidirectional audio streaming.

### Sending Audio Input

Audio must be formatted as **16-bit PCM at 16,000 Hz in mono** before transmission. The ADK does not perform format conversion, so ensuring correct specifications beforehand is critical.

**Best practices for audio streaming:**
- Use chunked streaming with sizes between 10-200ms based on latency requirements
- Send 100ms chunks (~3,200 bytes @ 16kHz) for balanced performance
- Stream continuously; the model processes audio rather than waiting for turn-taking
- With VAD enabled (default), manual activity signals are unnecessary

**Browser implementation** uses Web Audio API with AudioWorklet processors to capture microphone input, convert Float32 samples to 16-bit PCM format, and transmit via WebSocket binary frames.

### Receiving Audio Output

The model outputs audio at **24,000 Hz, 16-bit PCM, mono** format with MIME type `audio/pcm;rate=24000`. The data arrives as raw PCM bytes ready for playback.

**Event processing:** Access audio data through `part.inline_data` when `mime_type` begins with "audio/pcm". The google.genai types system automatically decodes base64-encoded audio to usable bytes.

**Client-side playback** employs an AudioWorklet processor with a ring buffer architecture to handle network jitter and ensure smooth playback despite variable latency.

## Image and Video Processing

Both static images and video in ADK Bidi-streaming process frames as individual JPEG images rather than continuous video streams.

**Specifications:**
- Format: JPEG (`image/jpeg`)
- Maximum frame rate: 1 FPS
- Recommended resolution: 768x768 pixels

**Limitations:** "Not suitable for real-time video action recognition" or motion tracking due to insufficient temporal resolution.

**Browser capture workflow:** Request camera access via `navigator.mediaDevices.getUserMedia()`, draw video frames to canvas, convert to JPEG with 0.85 quality, and encode as base64 for WebSocket transmission.

## Audio Model Architectures

### Native Audio Models

End-to-end models that process audio input and generate audio output directly without text conversion, producing more human-like prosody.

- **Models:** gemini-2.5-flash-native-audio-preview-12-2025 (Gemini Live API)
- **Features:** Automatic language detection, affective dialog, proactive responses
- **Limitation:** "AUDIO-only response modality" results in slower initial response times

### Half-Cascade Models

Hybrid architecture combining native audio input with text-to-speech output generation, providing better production reliability.

- **Models:** gemini-2.5-flash (Vertex AI Live API)
- **Features:** TEXT and AUDIO response modalities, explicit language control
- **Voices:** 8 prebuilt options (Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr)

**Model selection recommendation:** Use environment variables for flexibility as model availability changes over time.

## Audio Transcription

The Live API automatically converts speech to text for both user input and model output. Transcription is **enabled by default** but can be explicitly disabled.

**Event structure:** Transcriptions arrive as separate `input_transcription` and `output_transcription` fields on Event objects, not as content parts. Each contains `.text` (string) and `.finished` (boolean) attributes.

**Multi-agent requirement:** For agents with `sub_agents`, ADK automatically enables transcription regardless of RunConfig settings to support agent transfer functionality.

## Voice Configuration

Configure model audio characteristics at either the agent level (via `Gemini` instance) or session level (via RunConfig). Agent-level configuration takes precedence when both are specified.

**Example:** Create separate `Gemini` instances with distinct voices for different agents in multi-agent workflows, enabling each agent to speak with its own voice personality.

**Parameters:**
- `voice_config.prebuilt_voice_config.voice_name`: Voice identifier string
- `language_code`: ISO 639 language code for speech synthesis

## Voice Activity Detection (VAD)

VAD is **enabled by default**, automatically detecting speech start/stop for natural turn-taking. Disable it when implementing push-to-talk interfaces or client-side voice detection.

**Client-side VAD pattern:** Browser detects voice activity using AudioWorklet with RMS-based detection, sends manual `activity_start`/`activity_end` signals, and streams audio only during active speech—reducing CPU and network overhead.

## Custom Video Streaming Tools

ADK provides special tool support where streaming tools can yield video frames asynchronously via AsyncGenerator while the model continues generating responses. You must provide a `stop_streaming(function_name: str)` function to allow explicit stream termination.

---

**Source**: https://google.github.io/adk-docs/streaming/dev-guide/part5/
**Downloaded**: 2026-02-11
