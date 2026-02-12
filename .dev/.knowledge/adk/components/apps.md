# Apps: Workflow Management Class

## Overview

The **App** class serves as a top-level container for Agent Development Kit (ADK) agent workflows. According to the documentation, it is "designed to manage the lifecycle, configuration, and state for a collection of agents grouped by a root agent."

**Supported in:** ADK Python v1.14.0+

## Key Features

The App class enables configuration of:

- Context caching
- Context compression
- Agent resume functionality
- Plugins

## Purpose and Benefits

The App class addresses several architectural challenges:

1. **Centralized Configuration** — Provides "a single, centralized location for managing shared resources like API keys and database clients"

2. **Lifecycle Management** — Includes startup and shutdown hooks for managing persistent resources across multiple invocations

3. **State Scope** — Defines explicit boundaries for application-level state with an `app:*` prefix

4. **Deployment Unit** — Establishes a formal deployable unit, simplifying versioning and testing

## Basic Implementation

### Creating a Root Agent and App

```python
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App

root_agent = Agent(
    model='gemini-2.5-flash',
    name='greeter_agent',
    description='An agent that provides a friendly greeting.',
    instruction='Reply with Hello, World!',
)

app = App(
    name="agents",
    root_agent=root_agent,
)
```

### Running the App

```python
import asyncio
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from agent import app

load_dotenv()
runner = InMemoryRunner(app=app)

async def main():
    try:
        response = await runner.run_debug("Hello there!")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Requirements

- Use `app` as the variable name for CLI compatibility
- `Runner.run_debug()` requires ADK Python v1.18.0 or higher

## Next Steps

The documentation references a Hello World App example for more complete implementation patterns.

---

**Source**: https://google.github.io/adk-docs/apps/
**Downloaded**: 2026-02-11
