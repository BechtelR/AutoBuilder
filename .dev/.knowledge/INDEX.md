# Knowledge Base Index

## Python API Reference (`python-adk/`)

### Quick Start
- [QUICK_REFERENCE.md](python-adk/QUICK_REFERENCE.md) — Common patterns and code examples

### Core Agent Classes
- [google-adk-agents.md](python-adk/google-adk-agents.md) — Module overview, BaseAgent, InvocationContext
- [google-adk-agents-LlmAgent.md](python-adk/google-adk-agents-LlmAgent.md) — LLM-based agent (69KB)
- [google-adk-agents-SequentialAgent.md](python-adk/google-adk-agents-SequentialAgent.md) — Sequential execution
- [google-adk-agents-LoopAgent.md](python-adk/google-adk-agents-LoopAgent.md) — Loop with max iterations
- [google-adk-agents-ParallelAgent.md](python-adk/google-adk-agents-ParallelAgent.md) — Concurrent execution

### Application & Runtime
- [google-adk-apps.md](python-adk/google-adk-apps.md) — App container, ResumabilityConfig
- [google-adk-runners.md](python-adk/google-adk-runners.md) — Runner, InMemoryRunner

### State Management
- [google-adk-sessions.md](python-adk/google-adk-sessions.md) — Session services
- [google-adk-artifacts.md](python-adk/google-adk-artifacts.md) — Artifact storage
- [google-adk-memory.md](python-adk/google-adk-memory.md) — Memory services

### Events & Observability
- [google-adk-events.md](python-adk/google-adk-events.md) — Event stream (278KB)
- [google-adk-telemetry-logging.md](python-adk/google-adk-telemetry-logging.md) — Logging and telemetry

### Models
- [google-adk-models.md](python-adk/google-adk-models.md) — BaseLlm, Gemini, LLMRegistry

### Tools
- [google-adk-tools.md](python-adk/google-adk-tools.md) — Tools overview
- [google-adk-tools-function-tool.md](python-adk/google-adk-tools-function-tool.md) — FunctionTool class

### Code Execution, Planning, Auth
- [google-adk-code-executors.md](python-adk/google-adk-code-executors.md) — Code executors
- [google-adk-planners.md](python-adk/google-adk-planners.md) — Planning abstractions
- [google-adk-evaluation.md](python-adk/google-adk-evaluation.md) — Evaluation framework
- [google-adk-plugins.md](python-adk/google-adk-plugins.md) — Plugin system
- [google-adk-auth.md](python-adk/google-adk-auth.md) — Auth utilities

### Tool Modules (`python-adk/tools/`)

**Base classes**: [base_tool](python-adk/tools/base_tool.md), [base_toolset](python-adk/tools/base_toolset.md), [base_authenticated_tool](python-adk/tools/base_authenticated_tool.md), [function_tool](python-adk/tools/function_tool.md), [authenticated_function_tool](python-adk/tools/authenticated_function_tool.md), [tool_context](python-adk/tools/tool_context.md), [toolbox_toolset](python-adk/tools/toolbox_toolset.md)

**Google services**: [google_search_tool](python-adk/tools/google_search_tool.md), [google_api_tool](python-adk/tools/google_api_tool.md), [google_maps_grounding_tool](python-adk/tools/google_maps_grounding_tool.md), [vertex_ai_search_tool](python-adk/tools/vertex_ai_search_tool.md), [enterprise_search_tool](python-adk/tools/enterprise_search_tool.md), [bigquery](python-adk/tools/bigquery.md), [apihub_tool](python-adk/tools/apihub_tool.md)

**Integrations**: [mcp_tool](python-adk/tools/mcp_tool.md), [openapi_tool](python-adk/tools/openapi_tool.md), [application_integration_tool](python-adk/tools/application_integration_tool.md), [crewai_tool](python-adk/tools/crewai_tool.md), [langchain_tool](python-adk/tools/langchain_tool.md)

**Data & memory**: [load_memory_tool](python-adk/tools/load_memory_tool.md), [preload_memory_tool](python-adk/tools/preload_memory_tool.md), [load_artifacts_tool](python-adk/tools/load_artifacts_tool.md), [load_web_page](python-adk/tools/load_web_page.md), [url_context_tool](python-adk/tools/url_context_tool.md), [retrieval](python-adk/tools/retrieval.md)

**Workflow & control**: [agent_tool](python-adk/tools/agent_tool.md), [transfer_to_agent_tool](python-adk/tools/transfer_to_agent_tool.md), [exit_loop_tool](python-adk/tools/exit_loop_tool.md), [get_user_choice_tool](python-adk/tools/get_user_choice_tool.md), [long_running_tool](python-adk/tools/long_running_tool.md), [example_tool](python-adk/tools/example_tool.md)

---

## ADK Conceptual Guides (`adk/`)

### Getting Started
- [get-started-python.md](adk/get-started-python.md) — Python quickstart
- [get-started-typescript.md](adk/get-started-typescript.md) — TypeScript quickstart
- [get-started-go.md](adk/get-started-go.md) — Go quickstart
- [get-started-java.md](adk/get-started-java.md) — Java quickstart

### Agents
- [agents/agents-overview.md](adk/agents/agents-overview.md) — Overview of agent types
- [agents/llm-agents.md](adk/agents/llm-agents.md) — LLM agent configuration
- [agents/workflow-agents-overview.md](adk/agents/workflow-agents-overview.md) — Workflow concepts
- [agents/sequential-agents.md](adk/agents/sequential-agents.md) — Sequential patterns
- [agents/loop-agents.md](adk/agents/loop-agents.md) — Loop patterns
- [agents/parallel-agents.md](adk/agents/parallel-agents.md) — Parallel patterns
- [agents/custom-agents.md](adk/agents/custom-agents.md) — Custom agent orchestration
- [agents/multi-agents.md](adk/agents/multi-agents.md) — Multi-agent coordination
- [agents/agent-config.md](adk/agents/agent-config.md) — YAML agent configuration

### Components
- [components/apps.md](adk/components/apps.md) — Application configuration
- [components/sessions-session-management.md](adk/components/sessions-session-management.md) — Session management
- [components/sessions-state.md](adk/components/sessions-state.md) — State management (4 scopes)
- [components/sessions-memory.md](adk/components/sessions-memory.md) — Memory services
- [components/artifacts.md](adk/components/artifacts.md) — Artifact storage
- [components/events.md](adk/components/events.md) — Event system
- [components/callbacks-types.md](adk/components/callbacks-types.md) — Callback types
- [components/callbacks-design-patterns.md](adk/components/callbacks-design-patterns.md) — Callback patterns
- [components/context-caching.md](adk/components/context-caching.md) — Context caching
- [components/context-compaction.md](adk/components/context-compaction.md) — Context compaction
- [components/plugins.md](adk/components/plugins.md) — Plugin system
- [components/mcp.md](adk/components/mcp.md) — Model Context Protocol
- [components/a2a-intro.md](adk/components/a2a-intro.md) — Agent-to-agent communication
- [components/grounding-google-search.md](adk/components/grounding-google-search.md) — Google Search grounding
- [components/grounding-vertex-ai-search.md](adk/components/grounding-vertex-ai-search.md) — Vertex AI Search
- [components/bidi-streaming-part1.md](adk/components/bidi-streaming-part1.md) — Bidi streaming (parts 1-5)
- [components/bidi-streaming-part2.md](adk/components/bidi-streaming-part2.md)
- [components/bidi-streaming-part3.md](adk/components/bidi-streaming-part3.md)
- [components/bidi-streaming-part4.md](adk/components/bidi-streaming-part4.md)
- [components/bidi-streaming-part5.md](adk/components/bidi-streaming-part5.md)

### Models
- [models/gemini.md](adk/models/gemini.md) — Gemini
- [models/claude.md](adk/models/claude.md) — Claude
- [models/litellm.md](adk/models/litellm.md) — LiteLLM (multi-provider)
- [models/vertex-ai.md](adk/models/vertex-ai.md) — Vertex AI
- [models/ollama.md](adk/models/ollama.md) — Ollama
- [models/vllm.md](adk/models/vllm.md) — vLLM
- [models/apigee.md](adk/models/apigee.md) — Apigee

### Tools
- [tools/custom-tools-overview.md](adk/tools/custom-tools-overview.md) — Custom tools overview
- [tools/function-tools.md](adk/tools/function-tools.md) — Function tool creation
- [tools/mcp-tools.md](adk/tools/mcp-tools.md) — MCP tools
- [tools/openapi-tools.md](adk/tools/openapi-tools.md) — OpenAPI tools
- [tools/authentication.md](adk/tools/authentication.md) — Authentication
- [tools/confirmation.md](adk/tools/confirmation.md) — Human-in-the-loop confirmation
- [tools/performance.md](adk/tools/performance.md) — Performance and parallelism
- [tools/integrations.md](adk/tools/integrations.md) — Pre-built integrations
- [tools/limitations.md](adk/tools/limitations.md) — Tool limitations

### Runtime
- [runtime/event-loop.md](adk/runtime/event-loop.md) — **Core execution model**
- [runtime/resume-agents.md](adk/runtime/resume-agents.md) — Checkpoint/resume
- [runtime/runtime-config.md](adk/runtime/runtime-config.md) — RunConfig
- [runtime/api-server.md](adk/runtime/api-server.md) — API server
- [runtime/command-line.md](adk/runtime/command-line.md) — CLI
- [runtime/web-interface.md](adk/runtime/web-interface.md) — Web UI

### Deployment
- [deployment/cloud-run.md](adk/deployment/cloud-run.md) — Cloud Run
- [deployment/gke.md](adk/deployment/gke.md) — GKE
- [deployment/agent-engine.md](adk/deployment/agent-engine.md) — Agent Engine

### Evaluation
- [evaluation/criteria-based.md](adk/evaluation/criteria-based.md) — Criteria-based evaluation
- [evaluation/user-simulation.md](adk/evaluation/user-simulation.md) — User simulation

### Observability
- [observability/logging.md](adk/observability/logging.md) — Logging
