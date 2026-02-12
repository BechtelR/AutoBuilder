# Architecture Decisions Log

All major decisions recorded with rationale and date.

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | SDK over headless CLI | Less overhead, better parallelism, native streaming, multi-model support | 2026-01-14 |
| 2 | New app, not modified Automaker | Reuse architectural patterns, skip complexity debt | 2026-01-14 |
| 3 | Multi-workflow architecture | Future-proof for auto-design, auto-market, etc. | 2026-01-14 |
| 4 | Standalone orchestrator, not plugin | Plugin coupling is fragile; autonomous loop needs full control | 2026-01-14 |
| 5 | Plan/Execute phase separation | Strict role boundaries proven by oh-my-opencode's Prometheus/Atlas | 2026-01-14 |
| 6 | Agent role-based tool restrictions | Read-only exploration agents prevent scope creep | 2026-01-14 |
| 7 | Provider fallback chains | 3-step resolution (user, chain, default) is proven and pragmatic | 2026-01-14 |
| 8 | Python for core engine | Agent ecosystem is Python-first; all candidate frameworks are Python-native | 2026-02-11 |
| 9 | TypeScript only for UI | Dashboard/web UI layer, separate concern from orchestration engine | 2026-02-11 |
| 10 | No custom provider abstraction | Both Pydantic AI and Google ADK handle multi-model natively; building our own is unnecessary | 2026-02-11 |
| 11 | Claude Agent SDK rejected | It is an agent harness (single Claude agent), not a workflow orchestrator; Claude-only, TS-only | 2026-02-11 |
| 12 | Google ADK selected as framework | Unified composition of LLM agents + deterministic tools; first-class workflow primitives | 2026-02-11 |
| 13 | Phased MVP delivery | Targeting all 15+ features simultaneously risks bloat; MVP focuses on 6 core capabilities | 2026-02-11 |
| 14 | Skills system as Phase 1 component | Agents without skills are generic; skills produce project-appropriate output from day one | 2026-02-11 |
| 15 | Workflow composition system as Phase 1 | Workflows must be pluggable from day one; hardcoding auto-code then bolting on others later would require ripping out assumptions | 2026-02-11 |
| 16 | MCP used sparingly | MCPs add significant context bloat; prefer lightweight FunctionTools; use agent-browser for browser automation | 2026-02-11 |
| 17 | LLM Router for dynamic model selection | Different tasks benefit from different models; route by capability/cost/speed, not hardcoded model strings | 2026-02-11 |
| 18 | ADK App class as application container | App provides lifecycle management, context compression, resumability, plugin registration -- use as the top-level container | 2026-02-11 |
| 19 | Multi-level memory as Phase 1 | Agents must accumulate learnings across deliverables and sessions; without memory, deliverable 47 cannot know what patterns deliverables 1-10 established | 2026-02-11 |
| 20 | API-first gateway architecture | FastAPI gateway owns the external contract; ADK behind anti-corruption layer; swappable without client changes | 2026-02-11 |
| 21 | REST + SSE transport | REST for commands/queries, SSE for real-time event streaming; no GraphQL or gRPC at gateway layer; WebRTC reserved for future voice | 2026-02-11 |
| 22 | Single database | All data lives behind the gateway; no separate dashboard database; SQLAlchemy 2.0 async + Alembic migrations | 2026-02-11 |
| 23 | Redis from day one | Task queue (ARQ), event bus (Redis Streams), cron store, cache -- fundamental infrastructure, not a Phase 2 add-on | 2026-02-11 |
| 24 | ARQ for async workers | Native asyncio worker (not Celery); out-of-process workflow execution; gateway enqueues, workers execute | 2026-02-11 |
| 25 | Dashboard as pure SPA | React 19 + Vite static build; consumes gateway API via REST + SSE; no backend, no database of its own | 2026-02-11 |
| 26 | hey-api codegen for type safety | Pydantic models -> FastAPI -> OpenAPI spec -> hey-api -> typed TS client + TanStack Query hooks; build-time type safety without TS ORM | 2026-02-11 |
| 27 | Redis Streams for event bus | Persistent, replayable, consumer groups; SSE reconnection via Last-Event-ID + stream replay; webhook dispatch via consumer | 2026-02-11 |
| 28 | ARQ cron for scheduled jobs | Built-in to ARQ; no separate scheduler service needed | 2026-02-11 |
