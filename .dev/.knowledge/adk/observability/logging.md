# Agent Development Kit: Logging & Observability

Source: https://google.github.io/adk-docs/observability/logging/

## Overview

The Agent Development Kit (ADK) uses Python's standard `logging` module for diagnostic information. The framework itself does not configure logging; developers must set this up in their application's entry point.

## Core Principles

**Hierarchical approach:** "Loggers are named hierarchically based on the module path (e.g., `google_adk.google.adk.agents.llm_agent`), allowing for fine-grained control."

**Developer responsibility:** The framework is designed to be configured by application developers to match their specific needs, whether in development or production environments.

## Configuration Methods

### Basic Setup

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
```

### CLI Configuration

The ADK command-line interface supports logging control via `--log_level`:

```bash
adk web --log_level DEBUG path/to/your/agents_dir
adk web -v path/to/your/agents_dir  # shortcut for DEBUG
```

Available levels: `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, `CRITICAL`

## Log Level Details

| Level | Purpose | Content |
|-------|---------|---------|
| **DEBUG** | Detailed troubleshooting | Full LLM prompts, API responses, state transitions |
| **INFO** | Lifecycle events | Agent startup, session creation, tool execution |
| **WARNING** | Potential issues | Deprecated features, non-critical recovery events |
| **ERROR** | Serious failures | Failed API calls, unhandled exceptions, configuration problems |

## Log Structure

Standard format components:
- `%(asctime)s` – Timestamp
- `%(levelname)s` – Severity level
- `%(name)s` – Logger module name
- `%(message)s` – Log content

## Practical Debugging

When investigating agent behavior, enable DEBUG logging to inspect:
- Complete system instructions sent to language models
- Full conversation history
- Tool definitions and function calls
- Model response timing

**Production recommendation:** Use `INFO` or `WARNING` levels; enable `DEBUG` only during troubleshooting, as it produces verbose output potentially containing sensitive information.

---

**Supported versions:** Python v0.1.0+, TypeScript v0.2.0+, Go v0.1.0+, Java v0.1.0+
