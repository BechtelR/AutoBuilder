# Tool Performance Documentation - Agent Development Kit

## Overview

This documentation covers parallel tool execution in ADK Python v1.10.0+. The framework automatically attempts to run function tools concurrently, significantly improving agent performance when dealing with multiple external APIs or lengthy operations.

## Key Performance Benefits

**Scenarios where parallel execution excels:**
- Research tasks gathering information from multiple sources
- Independent API calls (e.g., flight searches across airlines)
- Publishing/communication across multiple channels or recipients

**Performance example:** Three tools requiring 2 seconds each execute in ~2 seconds parallel versus 6 seconds sequentially.

## Building Parallel-Ready Tools

Tools must use asynchronous Python syntax (`async def` and `await`) to enable concurrent execution within an asyncio event loop.

### Implementation Patterns

**HTTP Requests:**
Use `aiohttp.ClientSession` with async/await for non-blocking web calls.

**Database Operations:**
Employ async database libraries like `asyncpg` with async connection management.

**Long Loops:**
Incorporate `await asyncio.sleep(0)` periodically to yield control: "Add periodic yield points for long loops."

**CPU-Intensive Work:**
Leverage `ThreadPoolExecutor` with `loop.run_in_executor()` for processing-heavy functions.

**Large Dataset Processing:**
Combine chunking strategies with thread pools and yield points between chunks for optimal resource management.

## Prompt Optimization

Structure prompts explicitly encouraging parallel function calls. Tool descriptions should indicate: "This function is optimized for parallel execution - call multiple times for different cities."

## Important Limitations

⚠️ Warning: "Any ADK Tools that use synchronous processing in a set of tool function calls will block other tools from executing in parallel, even if the other tools allow for parallel execution."

## References

- Complete examples available in [adk-python repository](https://github.com/google/adk-python/tree/main/contributing/samples/parallel_functions)
- Related documentation: Function Tools guide

---

*Source: https://google.github.io/adk-docs/tools-custom/performance/*
*Downloaded: 2026-02-11*
