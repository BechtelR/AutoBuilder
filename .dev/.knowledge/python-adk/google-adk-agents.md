# Google ADK Agents Module Reference

Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.agents

## Module Overview

The `google.adk.agents` module provides the core agent framework for building conversational AI systems. It includes base classes and invocation context management for text and live interactions.

## Key Classes

### Agent
An alias for `LlmAgent`, representing the primary agent type for language model-based interactions.

### BaseAgent
The foundation class for all agents in the Agent Development Kit.

**Core Fields:**
- `name` (str, required): Python identifier, must be unique within agent tree
- `description` (str): One-line capability summary for model delegation
- `parent_agent`: Reference to parent in agent hierarchy
- `sub_agents`: List of child agents with validated unique names
- `before_agent_callback`: Pre-execution hook(s) to intercept or modify behavior
- `after_agent_callback`: Post-execution hook(s) for response augmentation

**Key Methods:**
- `run_async(parent_context)`: Entry point for text-based conversation, yields Events
- `run_live(parent_context)`: Entry point for video/audio conversation, yields Events
- `find_agent(name)`: Locates agent by name in tree
- `find_sub_agent(name)`: Searches descendants only
- `clone(update=None)`: Creates independent copy with optional field updates
- `from_config(config, config_abs_path)`: Factory method from configuration files

**Properties:**
- `root_agent`: Retrieves topmost agent in hierarchy
- `canonical_before_agent_callbacks`: Normalized callback list
- `canonical_after_agent_callbacks`: Normalized callback list

### InvocationContext
Represents a single agent invocation lifecycle from user message to final response.

**Key Fields:**
- `invocation_id`: Unique identifier for this invocation
- `agent`: The active agent instance
- `user_content`: Input from end user
- `session`: Conversation session data
- `agent_states`: Per-agent state storage (dict)
- `end_invocation`: Flag to terminate processing
- `context_cache_config`: Caching configuration
- `run_config`: Execution parameters
- `resumability_config`: Session resumption settings

**Lifecycle Concept:**
An invocation orchestrates multiple agent calls until transfer or completion. Each agent call may contain multiple steps—LLM invocations paired with tool execution cycles.

## Callback System

Callbacks receive a `CallbackContext` parameter and return optional `Content`:

- **before_agent_callback**: Executes before agent runs; returning content skips agent execution
- **after_agent_callback**: Executes after agent completion; content appends to response history

Multiple callbacks execute sequentially until one returns non-None content.

## Validation

- Agent names validated as Python identifiers
- Sub-agent names enforced as unique within siblings
- An agent can only be added once to the tree
