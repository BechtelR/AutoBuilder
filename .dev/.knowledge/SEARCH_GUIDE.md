# Knowledge Base Search Guide

Topic-to-file mappings and keyword index.

---

## By Topic

### Agents

| Topic | File(s) |
|-------|---------|
| Agent types overview | `adk/agents/agents-overview.md` |
| LlmAgent basics | `adk/agents/llm-agents.md` |
| LlmAgent API | `python-adk/google-adk-agents-LlmAgent.md` |
| CustomAgent (BaseAgent) | `adk/agents/custom-agents.md` |
| BaseAgent API | `python-adk/google-adk-agents.md` |
| SequentialAgent | `adk/agents/sequential-agents.md`, `python-adk/google-adk-agents-SequentialAgent.md` |
| ParallelAgent | `adk/agents/parallel-agents.md`, `python-adk/google-adk-agents-ParallelAgent.md` |
| LoopAgent | `adk/agents/loop-agents.md`, `python-adk/google-adk-agents-LoopAgent.md` |
| Multi-agent coordination | `adk/agents/multi-agents.md` |
| YAML agent configuration | `adk/agents/agent-config.md` |
| InvocationContext | `python-adk/google-adk-agents.md` |

### State & Sessions

| Topic | File(s) |
|-------|---------|
| State (4 scopes) | `adk/components/sessions-state.md` |
| Session lifecycle | `adk/components/sessions-session-management.md` |
| SessionService API | `python-adk/google-adk-sessions.md` |
| Memory service | `adk/components/sessions-memory.md` |
| Memory API | `python-adk/google-adk-memory.md` |

### Tools

| Topic | File(s) |
|-------|---------|
| FunctionTool basics | `adk/tools/function-tools.md` |
| FunctionTool API | `python-adk/google-adk-tools-function-tool.md` |
| Tools overview | `python-adk/google-adk-tools.md` |
| Custom tools | `adk/tools/custom-tools-overview.md` |
| MCP tools | `adk/tools/mcp-tools.md`, `adk/components/mcp.md` |
| OpenAPI tools | `adk/tools/openapi-tools.md` |
| Authentication | `adk/tools/authentication.md` |
| Tool confirmation | `adk/tools/confirmation.md` |
| Tool performance | `adk/tools/performance.md` |
| Pre-built integrations | `adk/tools/integrations.md` |
| Tool limitations | `adk/tools/limitations.md` |

### Runtime & Execution

| Topic | File(s) |
|-------|---------|
| Event loop (**CRITICAL**) | `adk/runtime/event-loop.md` |
| Resumability | `adk/runtime/resume-agents.md` |
| ResumabilityConfig | `python-adk/google-adk-apps.md` |
| RunConfig | `adk/runtime/runtime-config.md` |
| API server | `adk/runtime/api-server.md` |
| Web interface | `adk/runtime/web-interface.md` |
| CLI | `adk/runtime/command-line.md` |
| Runner API | `python-adk/google-adk-runners.md` |

### Models & Providers

| Topic | File(s) |
|-------|---------|
| LiteLLM (multi-provider) | `adk/models/litellm.md` |
| Gemini | `adk/models/gemini.md` |
| Claude | `adk/models/claude.md` |
| Vertex AI | `adk/models/vertex-ai.md` |
| Ollama | `adk/models/ollama.md` |
| vLLM | `adk/models/vllm.md` |
| Apigee | `adk/models/apigee.md` |
| Model API | `python-adk/google-adk-models.md` |

### Callbacks & Context

| Topic | File(s) |
|-------|---------|
| Callback types | `adk/components/callbacks-types.md` |
| Callback patterns | `adk/components/callbacks-design-patterns.md` |
| Context caching | `adk/components/context-caching.md` |
| Context compaction | `adk/components/context-compaction.md` |

### Application & Infrastructure

| Topic | File(s) |
|-------|---------|
| App lifecycle | `adk/components/apps.md` |
| App API | `python-adk/google-adk-apps.md` |
| Events | `adk/components/events.md`, `python-adk/google-adk-events.md` |
| Artifacts | `adk/components/artifacts.md`, `python-adk/google-adk-artifacts.md` |
| Plugins | `adk/components/plugins.md`, `python-adk/google-adk-plugins.md` |
| Logging | `adk/observability/logging.md`, `python-adk/google-adk-telemetry-logging.md` |

### Deployment

| Topic | File(s) |
|-------|---------|
| Cloud Run | `adk/deployment/cloud-run.md` |
| GKE | `adk/deployment/gke.md` |
| Agent Engine | `adk/deployment/agent-engine.md` |

### Testing

| Topic | File(s) |
|-------|---------|
| Criteria-based eval | `adk/evaluation/criteria-based.md` |
| User simulation | `adk/evaluation/user-simulation.md` |
| Evaluation API | `python-adk/google-adk-evaluation.md` |

### Advanced

| Topic | File(s) |
|-------|---------|
| A2A protocol | `adk/components/a2a-intro.md` |
| Bidi streaming | `adk/components/bidi-streaming-part1.md` through `part5.md` |
| Google Search grounding | `adk/components/grounding-google-search.md` |
| Vertex AI Search grounding | `adk/components/grounding-vertex-ai-search.md` |
| Code executors | `python-adk/google-adk-code-executors.md` |
| Planners | `python-adk/google-adk-planners.md` |
| Auth utilities | `python-adk/google-adk-auth.md` |

### Errata & Gotchas

| Topic | File(s) |
|-------|---------|
| ADK quirks (empirically verified) | `adk/ERRATA.md` |
| State writes don't persist (CRITICAL) | `adk/ERRATA.md` #1 |
| InMemoryRunner auto_create_session | `adk/ERRATA.md` #2 |
| pyright strict workarounds | `adk/ERRATA.md` #3-6 |

---

## "How do I..."

| Question | File(s) |
|----------|---------|
| create an LLM agent? | `adk/agents/llm-agents.md`, `python-adk/google-adk-agents-LlmAgent.md` |
| create a custom agent? | `adk/agents/custom-agents.md`, `python-adk/google-adk-agents.md` |
| chain agents in sequence? | `adk/agents/sequential-agents.md` |
| run agents in parallel? | `adk/agents/parallel-agents.md` |
| create a loop? | `adk/agents/loop-agents.md` |
| create a custom tool? | `adk/tools/function-tools.md` |
| use multiple LLM providers? | `adk/models/litellm.md` |
| manage state between agents? | `adk/components/sessions-state.md` |
| persist state across sessions? | `python-adk/google-adk-sessions.md` |
| add callbacks? | `adk/components/callbacks-types.md` |
| implement checkpoint/resume? | `adk/runtime/resume-agents.md` |
| deploy to Cloud Run? | `adk/deployment/cloud-run.md` |
| test my agents? | `adk/evaluation/criteria-based.md`, `adk/runtime/api-server.md` |
| handle authentication? | `adk/tools/authentication.md` |
| compress context history? | `adk/components/context-compaction.md` |
| store binary files? | `adk/components/artifacts.md`, `python-adk/google-adk-artifacts.md` |
| implement long-term memory? | `adk/components/sessions-memory.md`, `python-adk/google-adk-memory.md` |
| debug agent execution? | `adk/runtime/event-loop.md`, `python-adk/google-adk-events.md` |
| optimize performance? | `adk/tools/performance.md`, `adk/agents/parallel-agents.md` |

---

## Keyword Index

| Keyword | File(s) |
|---------|---------|
| Agent | `adk/agents/` (all files) |
| AgentTool | `python-adk/tools/agent_tool.md` |
| API keys | `adk/tools/authentication.md` |
| API server | `adk/runtime/api-server.md` |
| App | `adk/components/apps.md`, `python-adk/google-adk-apps.md` |
| Artifacts | `adk/components/artifacts.md`, `python-adk/google-adk-artifacts.md` |
| Async | `adk/runtime/event-loop.md` |
| auto_create_session | `adk/ERRATA.md` #2, `python-adk/google-adk-runners.md` |
| BaseAgent | `python-adk/google-adk-agents.md` |
| BaseLlm | `python-adk/google-adk-models.md` |
| before_model_callback | `adk/components/callbacks-types.md`, `python-adk/google-adk-agents-LlmAgent.md` |
| Caching | `adk/components/context-caching.md` |
| Callbacks | `adk/components/callbacks-types.md`, `adk/components/callbacks-design-patterns.md` |
| Checkpoint | `adk/runtime/resume-agents.md` |
| Cloud Run | `adk/deployment/cloud-run.md` |
| Code executor | `python-adk/google-adk-code-executors.md` |
| Compaction | `adk/components/context-compaction.md` |
| Concurrency | `adk/agents/parallel-agents.md`, `adk/tools/performance.md` |
| CustomAgent | `adk/agents/custom-agents.md` |
| Event loop | `adk/runtime/event-loop.md` |
| Events | `adk/components/events.md`, `python-adk/google-adk-events.md` |
| FunctionTool | `adk/tools/function-tools.md`, `python-adk/google-adk-tools-function-tool.md` |
| GKE | `adk/deployment/gke.md` |
| Grounding | `adk/components/grounding-google-search.md`, `adk/components/grounding-vertex-ai-search.md` |
| InMemoryRunner | `python-adk/google-adk-runners.md` |
| InMemorySessionService | `python-adk/google-adk-sessions.md` |
| InvocationContext | `python-adk/google-adk-agents.md` |
| LiteLLM | `adk/models/litellm.md` |
| LlmAgent | `adk/agents/llm-agents.md`, `python-adk/google-adk-agents-LlmAgent.md` |
| LLMRegistry | `python-adk/google-adk-models.md` |
| Logging | `adk/observability/logging.md`, `python-adk/google-adk-telemetry-logging.md` |
| LoopAgent | `adk/agents/loop-agents.md`, `python-adk/google-adk-agents-LoopAgent.md` |
| max_iterations | `adk/agents/loop-agents.md`, `python-adk/google-adk-agents-LoopAgent.md` |
| MCP | `adk/tools/mcp-tools.md`, `adk/components/mcp.md`, `python-adk/tools/mcp_tool.md` |
| Memory | `adk/components/sessions-memory.md`, `python-adk/google-adk-memory.md` |
| Multi-agent | `adk/agents/multi-agents.md` |
| OAuth2 | `adk/tools/authentication.md` |
| OpenAPI | `adk/tools/openapi-tools.md`, `python-adk/tools/openapi_tool.md` |
| output_key | `adk/agents/llm-agents.md`, `adk/agents/multi-agents.md` |
| ParallelAgent | `adk/agents/parallel-agents.md`, `python-adk/google-adk-agents-ParallelAgent.md` |
| Plugins | `adk/components/plugins.md`, `python-adk/google-adk-plugins.md` |
| ResumabilityConfig | `python-adk/google-adk-apps.md` |
| Resume | `adk/runtime/resume-agents.md` |
| RunConfig | `adk/runtime/runtime-config.md` |
| Runner | `python-adk/google-adk-runners.md` |
| SequentialAgent | `adk/agents/sequential-agents.md`, `python-adk/google-adk-agents-SequentialAgent.md` |
| Session | `adk/components/sessions-session-management.md`, `python-adk/google-adk-sessions.md` |
| State | `adk/components/sessions-state.md` |
| State scopes | `adk/components/sessions-state.md` |
| Streaming | `adk/components/bidi-streaming-part1.md` through `part5.md` |
| state_delta | `adk/components/sessions-state.md`, `adk/ERRATA.md` #1 |
| sub_agents | `adk/agents/sequential-agents.md`, `adk/agents/parallel-agents.md` |
| transfer_to_agent | `adk/agents/multi-agents.md`, `python-adk/tools/transfer_to_agent_tool.md` |
| ERRATA | `adk/ERRATA.md` |
