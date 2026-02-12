# google.adk.telemetry & Logging - Observability

**Module**: `google.adk.telemetry` (limited direct API) + Python logging integration
**Purpose**: Logging, tracing, and observability for ADK applications
**Documentation Sources**:
- https://google.github.io/adk-docs/observability/logging/
- https://google.github.io/adk-docs/observability/monocle/
- https://google.github.io/adk-docs/api-reference/java/com/google/adk/Telemetry.html (Java)

---

## Overview

The Agent Development Kit uses Python's standard `logging` module to provide flexible diagnostic capabilities. As the documentation states:

> "ADK's approach to logging is to provide detailed diagnostic information without being overly verbose by default."

ADK also supports OpenTelemetry-compatible tracing through third-party integrations.

---

## Python Logging Configuration

### Basic Setup

Developers configure logging in their main application script using `logging.basicConfig()`:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
```

### CLI Configuration

The ADK CLI supports logging control via command-line flags:

```bash
# Set log level explicitly
adk web --log_level DEBUG path/to/agents_dir

# Use verbose shortcut for DEBUG level
adk web -v path/to/agents_dir
adk web --verbose path/to/agents_dir
```

**Note**: Command-line settings override programmatic configuration.

---

## Log Levels

| Level | Purpose | Content | Use Case |
|-------|---------|---------|----------|
| **DEBUG** | Crucial for debugging | Full LLM prompts, API responses, state transitions | Development and troubleshooting |
| **INFO** | General lifecycle events | Agent initialization, tool execution, session changes | Production monitoring |
| **WARNING** | Potential issues | Deprecated features, recoverable errors | Production alerts |
| **ERROR** | Serious failures | Failed API calls, exceptions, configuration problems | Production error tracking |

**Recommendation**:
- **Production**: INFO or WARNING level
- **Development/Debugging**: DEBUG level only when needed

---

## Log Structure

A typical log entry follows this format:

```
%(asctime)s - %(levelname)s - %(name)s - %(message)s
```

### Format Components

| Component | Description | Example |
|-----------|-------------|---------|
| `%(asctime)s` | Timestamp | `2025-07-08 11:22:33,456` |
| `%(levelname)s` | Log level | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `%(name)s` | Logger name (hierarchical) | `google_adk.models.google_llm` |
| `%(message)s` | Log message | `LLM Request: ...` |

### Example Log Entry

```
2025-07-08 11:22:33,456 - DEBUG - google_adk.models.google_llm - LLM Request: {"model": "gemini-2.0-flash-exp", "messages": [...]}
```

---

## Hierarchical Loggers

ADK uses hierarchical logger names for fine-grained control:

```python
import logging

# Control all ADK logs
logging.getLogger('google_adk').setLevel(logging.INFO)

# Control only agent logs
logging.getLogger('google_adk.agents').setLevel(logging.DEBUG)

# Control only model logs
logging.getLogger('google_adk.models').setLevel(logging.WARNING)

# Control only tool logs
logging.getLogger('google_adk.tools').setLevel(logging.INFO)
```

---

## Configuration Principles

### 1. No Auto-Configuration

**ADK does not auto-configure logging**. Developer responsibility applies.

If you don't configure logging:
```python
# This will use Python's default WARNING level
from google.adk import agents
```

### 2. Framework Flexibility

Works with any standard Python logging configuration:

```python
import logging
import logging.handlers

# File handler
file_handler = logging.FileHandler('adk.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(message)s'))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

# Root logger configuration
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)
```

### 3. Integration with Logging Libraries

Compatible with popular logging libraries:

```python
# Using structlog
import structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

# Using loguru
from loguru import logger
import sys

logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("adk_{time}.log", rotation="500 MB", level="DEBUG")
```

---

## OpenTelemetry Integration

### Monocle Observability Platform

Monocle is an open-source observability platform that automatically instruments Google ADK applications.

**Capabilities**:
- Comprehensive tracing for ADK applications through automatic instrumentation
- OpenTelemetry-compatible traces
- Agent runs, tool calls, and model requests tracking

#### Installation

```bash
pip install monocle_apptrace google-adk
```

#### Setup

Initialize telemetry at application startup:

```python
from monocle_apptrace import setup_monocle_telemetry

setup_monocle_telemetry(workflow_name="my-adk-app")
```

#### Instrumented Components

Monocle automatically instruments three core ADK elements:

1. **`BaseAgent.run_async`** – Captures agent execution and delegation
2. **`FunctionTool.run_async`** – Captures tool execution with parameters and results
3. **`Runner.run_async`** – Captures runner execution and request context

#### Export Options

**Default**: Local JSON files in `./monocle` directory

**Environment Variables**:
```bash
# Console output (debugging)
export MONOCLE_EXPORTER="console"

# File export (production)
export MONOCLE_EXPORTER="file"
```

#### Trace Data Captured

Monocle records:
- Agent state and delegation events
- Tool names, parameters, and results
- Timing information (start, end, duration)
- Error states and exceptions
- Token usage for LLM calls

#### Visualization

**Okahu Trace Visualizer** VS Code extension provides:
- Interactive trace analysis
- Gantt chart visualization
- JSON data inspection
- Error identification

---

## Third-Party Observability Platforms

### Phoenix

**Source**: https://google.github.io/adk-docs/observability/phoenix/

Open-source, self-hosted observability platform for monitoring, debugging, and improving LLM applications and AI Agents at scale.

**Features**:
- Comprehensive tracing capabilities
- Evaluation features
- Self-hosted option

### Arize AX

**Source**: https://google.github.io/adk-docs/observability/arize-ax/

Production-grade observability platform for monitoring, debugging, and improving LLM applications and AI Agents at scale.

**Features**:
- Comprehensive tracing
- Evaluation capabilities
- Monitoring features
- Production-ready

---

## Best Practices

### 1. Production Logging

```python
import logging

# Production configuration
logging.basicConfig(
    level=logging.INFO,  # INFO or WARNING for production
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('adk_production.log'),
        logging.StreamHandler()
    ]
)

# Set DEBUG only for specific subsystems when troubleshooting
logging.getLogger('google_adk.agents').setLevel(logging.DEBUG)
```

### 2. Development Logging

```python
import logging

# Development configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s'
)
```

### 3. Structured Logging

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger('google_adk').addHandler(handler)
```

### 4. Context-Aware Logging

```python
import logging

logger = logging.getLogger(__name__)

def process_user_request(user_id: str, request: str):
    logger.info(
        "Processing request",
        extra={'user_id': user_id, 'request_length': len(request)}
    )
```

### 5. Performance Monitoring

```python
import logging
import time

logger = logging.getLogger(__name__)

async def timed_agent_execution(agent, input_data):
    start_time = time.time()
    logger.debug(f"Starting agent {agent.name}")

    result = await agent.run_async(input_data)

    duration = time.time() - start_time
    logger.info(
        f"Agent {agent.name} completed",
        extra={'duration_seconds': duration}
    )

    return result
```

---

## Java Telemetry API (Reference)

**Note**: The Java ADK has a dedicated `Telemetry` utility class for tracing. Python ADK relies on standard logging + OpenTelemetry integrations.

**Java API Reference**: https://google.github.io/adk-docs/api-reference/java/com/google/adk/Telemetry.html

The Java `Telemetry` class provides methods to trace:
- Tool calls
- Tool responses
- LLM interactions
- Data handling

---

## Common Logger Names

| Logger | Purpose |
|--------|---------|
| `google_adk` | Root logger for all ADK |
| `google_adk.agents` | Agent execution |
| `google_adk.models` | LLM interactions |
| `google_adk.tools` | Tool execution |
| `google_adk.runners` | Runner operations |
| `google_adk.sessions` | Session management |
| `google_adk.events` | Event processing |
| `google_adk.memory` | Memory operations |

---

## Related Documentation

- [Callbacks](https://google.github.io/adk-docs/callbacks/)
- [Plugins](https://google.github.io/adk-docs/plugins/)
- [Events](https://google.github.io/adk-docs/events/)
- [Monocle Integration](https://google.github.io/adk-docs/observability/monocle/)
- [Phoenix Integration](https://google.github.io/adk-docs/observability/phoenix/)
- [Arize AX Integration](https://google.github.io/adk-docs/observability/arize-ax/)

---

**Last Updated**: 2026-02-11
**API Stability**: Stable (Python logging), Beta (Telemetry integrations)
