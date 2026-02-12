# ADK Quickstart Reading Guide

Reading guide for AutoBuilder developers, ordered by priority.

---

## 30-Minute Quick Start

1. [adk/get-started-python.md](adk/get-started-python.md) — Setup and first agent
2. [python-adk/QUICK_REFERENCE.md](python-adk/QUICK_REFERENCE.md) — Common code patterns
3. [adk/runtime/event-loop.md](adk/runtime/event-loop.md) — How agents actually execute

---

## Phase 1: Foundation (3-4 hours)

Understand ADK's execution model and core primitives.

1. **[adk/get-started-python.md](adk/get-started-python.md)** — Installation, project setup, first agent
2. **[adk/runtime/event-loop.md](adk/runtime/event-loop.md)** — **CRITICAL** — Core execution model
3. **[adk/agents/llm-agents.md](adk/agents/llm-agents.md)** — LLM agent config, tools, callbacks
4. **[adk/agents/custom-agents.md](adk/agents/custom-agents.md)** — Subclassing BaseAgent for deterministic steps
5. **[adk/components/sessions-state.md](adk/components/sessions-state.md)** — Four-scope state system (session, user, app, temp)
6. **[python-adk/google-adk-agents-LlmAgent.md](python-adk/google-adk-agents-LlmAgent.md)** — Complete LlmAgent API reference
7. **[python-adk/QUICK_REFERENCE.md](python-adk/QUICK_REFERENCE.md)** — Copy-paste starting points

## Phase 2: Orchestration (2-3 hours)

Compose agents into workflows.

8. **[adk/agents/sequential-agents.md](adk/agents/sequential-agents.md)** — Feature pipeline (plan -> code -> lint -> test -> review)
9. **[adk/agents/parallel-agents.md](adk/agents/parallel-agents.md)** — Batch execution of multiple features
10. **[adk/agents/loop-agents.md](adk/agents/loop-agents.md)** — Review/fix cycles with retry logic
11. **[python-adk/google-adk-agents-SequentialAgent.md](python-adk/google-adk-agents-SequentialAgent.md)** — SequentialAgent API
12. **[python-adk/google-adk-agents-ParallelAgent.md](python-adk/google-adk-agents-ParallelAgent.md)** — ParallelAgent API
13. **[python-adk/google-adk-agents-LoopAgent.md](python-adk/google-adk-agents-LoopAgent.md)** — LoopAgent API
14. **[adk/agents/multi-agents.md](adk/agents/multi-agents.md)** — Multi-agent coordination patterns

## Phase 3: Tools & Integration (1-2 hours)

Create custom tools for agents.

15. **[adk/tools/function-tools.md](adk/tools/function-tools.md)** — Wrap Python functions as LLM-callable tools
16. **[python-adk/google-adk-tools-function-tool.md](python-adk/google-adk-tools-function-tool.md)** — FunctionTool API, auto-schema from type hints
17. **[adk/tools/authentication.md](adk/tools/authentication.md)** — OAuth2, API keys, credential management
18. **[adk/tools/performance.md](adk/tools/performance.md)** — Parallel tool execution, caching
19. **[adk/tools/integrations.md](adk/tools/integrations.md)** — 50+ pre-built tools

## Phase 4: Advanced Features (2-3 hours)

Multi-model routing, resumability, memory.

20. **[adk/models/litellm.md](adk/models/litellm.md)** — Multi-provider routing via LiteLLM
21. **[adk/runtime/resume-agents.md](adk/runtime/resume-agents.md)** — Checkpoint/resume, ResumabilityConfig
22. **[adk/components/sessions-memory.md](adk/components/sessions-memory.md)** — Long-term memory service
23. **[python-adk/google-adk-memory.md](python-adk/google-adk-memory.md)** — MemoryService API
24. **[adk/components/callbacks-types.md](adk/components/callbacks-types.md)** — before_model, after_model, tool callbacks
25. **[adk/components/callbacks-design-patterns.md](adk/components/callbacks-design-patterns.md)** — Callback best practices
26. **[python-adk/google-adk-apps.md](python-adk/google-adk-apps.md)** — App configuration, ResumabilityConfig
27. **[python-adk/google-adk-sessions.md](python-adk/google-adk-sessions.md)** — SessionService implementations
28. **[adk/components/context-compaction.md](adk/components/context-compaction.md)** — History compression for long sessions

## Phase 5: Testing & Deployment (1-2 hours)

29. **[adk/evaluation/criteria-based.md](adk/evaluation/criteria-based.md)** — 8 evaluation criteria
30. **[adk/runtime/api-server.md](adk/runtime/api-server.md)** — REST API for integration testing
31. **[adk/deployment/cloud-run.md](adk/deployment/cloud-run.md)** — Serverless deployment
32. **[adk/deployment/gke.md](adk/deployment/gke.md)** — Kubernetes deployment

---

## By Development Task

| Building... | Read |
|-------------|------|
| **BatchOrchestrator** | [agents/custom-agents.md](adk/agents/custom-agents.md), [runtime/event-loop.md](adk/runtime/event-loop.md), [components/sessions-state.md](adk/components/sessions-state.md), [agents/multi-agents.md](adk/agents/multi-agents.md) |
| **Feature pipeline** | [agents/sequential-agents.md](adk/agents/sequential-agents.md), [agents/loop-agents.md](adk/agents/loop-agents.md) |
| **LLM agents** (planner, coder, reviewer) | [agents/llm-agents.md](adk/agents/llm-agents.md), [google-adk-agents-LlmAgent.md](python-adk/google-adk-agents-LlmAgent.md), [tools/function-tools.md](adk/tools/function-tools.md) |
| **Deterministic agents** (linter, test runner) | [agents/custom-agents.md](adk/agents/custom-agents.md), [google-adk-agents.md](python-adk/google-adk-agents.md), [components/sessions-state.md](adk/components/sessions-state.md) |
| **LLM Router** | [models/litellm.md](adk/models/litellm.md), [google-adk-models.md](python-adk/google-adk-models.md) |
| **SkillLoaderAgent** | [agents/custom-agents.md](adk/agents/custom-agents.md), [components/callbacks-types.md](adk/components/callbacks-types.md) |
| **Memory system** | [components/sessions-memory.md](adk/components/sessions-memory.md), [google-adk-memory.md](python-adk/google-adk-memory.md) |
| **Tools** (filesystem, bash, git) | [tools/function-tools.md](adk/tools/function-tools.md), [google-adk-tools-function-tool.md](python-adk/google-adk-tools-function-tool.md), [tools/performance.md](adk/tools/performance.md) |
| **Resumability** | [runtime/resume-agents.md](adk/runtime/resume-agents.md), [google-adk-apps.md](python-adk/google-adk-apps.md), [google-adk-sessions.md](python-adk/google-adk-sessions.md) |
| **Parallel execution** | [agents/parallel-agents.md](adk/agents/parallel-agents.md), [google-adk-agents-ParallelAgent.md](python-adk/google-adk-agents-ParallelAgent.md) |
| **Review/fix loop** | [agents/loop-agents.md](adk/agents/loop-agents.md), [google-adk-agents-LoopAgent.md](python-adk/google-adk-agents-LoopAgent.md) |
| **App container** | [google-adk-apps.md](python-adk/google-adk-apps.md), [components/apps.md](adk/components/apps.md), [google-adk-sessions.md](python-adk/google-adk-sessions.md) |
| **Debugging** | [runtime/event-loop.md](adk/runtime/event-loop.md), [google-adk-events.md](python-adk/google-adk-events.md), [observability/logging.md](adk/observability/logging.md) |
| **Tests** | [evaluation/criteria-based.md](adk/evaluation/criteria-based.md), [google-adk-runners.md](python-adk/google-adk-runners.md) |
| **Deployment** | [deployment/cloud-run.md](adk/deployment/cloud-run.md), [deployment/gke.md](adk/deployment/gke.md) |
