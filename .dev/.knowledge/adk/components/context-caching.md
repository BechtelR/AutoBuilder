# Context Caching with Gemini - Complete Content

## Overview

The Agent Development Kit (ADK) supports context caching for Gemini 2.0 and higher models. This feature enables reuse of extended instructions and large datasets across multiple agent requests, improving performance and reducing token consumption.

**Key capability:** "Using context caching features in generative AI models can significantly speed up responses and lower the number of tokens sent to the model for each request."

## Configure Context Caching

Implementation requires the `ContextCacheConfig` class at the App object level:

```python
from google.adk import Agent
from google.adk.apps.app import App
from google.adk.agents.context_cache_config import ContextCacheConfig

root_agent = Agent(
  # configure an agent using Gemini 2.0 or higher
)

# Create the app with context caching configuration
app = App(
    name='my-caching-agent-app',
    root_agent=root_agent,
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,    # Minimum tokens to trigger caching
        ttl_seconds=600,    # Store for up to 10 minutes
        cache_intervals=5,  # Refresh after 5 uses
    ),
)
```

## Configuration Settings

The `ContextCacheConfig` class provides three primary settings:

| Setting | Description |
|---------|-------------|
| **min_tokens** | Minimum tokens required to enable caching; avoids overhead for small requests (default: 0) |
| **ttl_seconds** | Time-to-live for cached content in seconds before refresh (default: 1800/30 minutes) |
| **cache_intervals** | Maximum reuse count before expiration, regardless of TTL status (default: 10) |

## Next Steps

- Review the `cache_analysis` sample for performance analysis implementation
- Explore `static_instruction` sample for session-wide instructions using the static_instruction agent parameter

**Availability:** ADK Python v1.15.0 and later

---

**Source**: https://google.github.io/adk-docs/context/caching/
**Downloaded**: 2026-02-11
