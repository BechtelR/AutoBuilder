# AutoBuilder Project Structure

Single source of truth for the project scaffold. All other docs reference this file rather than duplicating the structure.

---

```
AutoBuilder/
│
├── app/                            # Python engine (main package)
│   ├── __main__.py                 # CLI entry point (invokes typer app)
│   │
│   ├── cli/                        # CLI interface (typer) — pure gateway API consumer
│   │   ├── main.py                 # Typer app definition and command registration
│   │   ├── commands.py             # Command implementations (run, status, list, logs, intervene)
│   │   └── output.py               # Terminal formatting and display helpers
│   │
│   ├── gateway/                    # FastAPI application
│   │   ├── main.py                 # FastAPI app factory, lifespan
│   │   ├── routes/                 # Route modules (workflows, chat, sessions, events, health)
│   │   ├── models/                 # Pydantic request/response models (API contracts, incl. chat.py)
│   │   ├── middleware/             # Auth, rate limiting, error handling, CORS
│   │   ├── sse.py                  # SSE endpoint — subscribes to Redis Streams
│   │   └── deps.py                 # Dependency injection (DB sessions, Redis, services)
│   │
│   ├── workers/                    # ARQ async workers
│   │   ├── settings.py             # ARQ WorkerSettings (Redis URL, queues, cron jobs)
│   │   ├── tasks.py                # Task definitions (workflow execution, cleanup)
│   │   └── adk.py                  # ADK engine factories (session service, agents, App container, Runner)
│   │
│   ├── events/                     # Event infrastructure
│   │   ├── publisher.py            # Publish events to Redis Streams
│   │   ├── consumer.py             # Stream consumer base, consumer group management
│   │   └── webhooks.py             # Webhook dispatcher — fires via httpx
│   │
│   ├── models/                     # Shared domain definitions
│   │   ├── __init__.py
│   │   ├── enums.py                # Global enums (WorkflowStatus, AgentRole, etc.)
│   │   ├── constants.py            # Global constants
│   │   └── base.py                 # Shared Pydantic base models
│   │
│   ├── lib/                        # Shared libraries (substantive, reusable modules)
│   │   ├── logging.py              # Structured logging setup
│   │   ├── exceptions.py           # Custom exception hierarchy
│   │   └── decorators.py           # Shared decorators (retry, timing, etc.)
│   │
│   ├── utils/                      # Stateless utility functions
│   │   ├── text.py                 # String helpers, formatting
│   │   ├── tokens.py               # Token counting, budget calculations
│   │   └── hashing.py              # Hashing, checksums
│   │
│   ├── agents/                     # Agent definitions + infrastructure
│   │   ├── director.md             # Director agent definition (LLM)
│   │   ├── pm.md                   # PM agent definition (LLM)
│   │   ├── planner.md              # Planning agent definition (LLM)
│   │   ├── coder.md                # Coding agent definition (LLM)
│   │   ├── reviewer.md             # Review agent definition (LLM)
│   │   ├── fixer.md                # Fix agent definition (LLM)
│   │   ├── linter.md               # Linter agent definition (custom, deterministic)
│   │   ├── tester.md               # Test runner agent definition (custom, deterministic)
│   │   ├── formatter.md            # Formatter agent definition (custom, deterministic)
│   │   ├── skill_loader.md         # Skill loader agent definition (custom, deterministic)
│   │   ├── memory_loader.md        # Memory loader agent definition (custom, deterministic)
│   │   ├── dependency_resolver.md  # Dependency resolver agent definition (custom, hybrid)
│   │   ├── diagnostics.md          # Diagnostics agent definition (custom, hybrid)
│   │   ├── regression_tester.md    # Regression test agent definition (custom, deterministic)
│   │   ├── _registry.py            # AgentRegistry + class registry (CustomAgent string→type resolution)
│   │   ├── assembler.py            # InstructionAssembler + InstructionFragment + InstructionContext
│   │   ├── protocols.py            # SkillLibraryProtocol, NullSkillLibrary
│   │   ├── state_helpers.py        # context_from_state, project config loader, compose_callbacks
│   │   ├── context_monitor.py      # ContextBudgetMonitor (before_model_callback) + ContextRecreationRequired
│   │   ├── pipeline.py             # DeliverablePipeline factory (SequentialAgent + ReviewCycle)
│   │   └── custom/                 # CustomAgent Python implementations
│   │       ├── skill_loader.py     # SkillLoaderAgent (deterministic)
│   │       ├── memory_loader.py    # MemoryLoaderAgent (deterministic)
│   │       ├── linter.py           # LinterAgent (deterministic)
│   │       ├── test_runner.py      # TestRunnerAgent (deterministic)
│   │       ├── formatter.py        # FormatterAgent (deterministic)
│   │       ├── regression_tester.py # RegressionTestAgent (deterministic)
│   │       ├── dependency_resolver.py # DependencyResolverAgent (hybrid)
│   │       └── diagnostics.py      # DiagnosticsAgent (hybrid)
│   │
│   ├── tools/                      # FunctionTool wrappers + GlobalToolset
│   │   ├── _toolset.py             # GlobalToolset(BaseToolset) — per-role tool vending
│   │   ├── filesystem.py           # 10 tools (read, write, edit, insert, multi_edit, glob, grep, move, delete, directory_list)
│   │   ├── code.py                 # code_symbols, run_diagnostics
│   │   ├── execution.py            # bash_exec, http_request
│   │   ├── git.py                  # 8 tools (status, commit, branch, diff, log, show, worktree, apply)
│   │   ├── web.py                  # web_search, web_fetch
│   │   ├── task.py                 # 6 tools (todo_read/write/list, task_create/update/query)
│   │   └── management.py           # 12 tools (PM: 6 + Director: 6)
│   │
│   ├── skills/                     # Global skill files (Markdown + YAML frontmatter)
│   │   ├── code/                   # Code-generation skills (api-endpoint, data-model, database-migration)
│   │   ├── review/                 # Code-review skills (security-review, performance-review)
│   │   ├── test/                   # Test-writing skills (unit-test-patterns)
│   │   ├── planning/               # Planning and decomposition skills (task-decomposition)
│   │   ├── research/               # Research skills (source-evaluation, citation-standards)
│   │   └── authoring/              # Authoring skills for system artifacts
│   │       ├── agent-definition/   # How to write agent definition files (SKILL.md + references/)
│   │       ├── skill-authoring/    # How to write skills (SKILL.md + references/)
│   │       ├── workflow-authoring/ # How to compose workflows (SKILL.md + references/)
│   │       └── project-conventions/ # How to configure project-level overrides (SKILL.md)
│   │
│   ├── workflows/                  # Pluggable workflow definitions
│   │   ├── auto-code/              # First workflow
│   │   │   ├── WORKFLOW.yaml       # Manifest: triggers, tools, models, pipeline type
│   │   │   ├── pipeline.py         # ADK agent composition
│   │   │   ├── agents/             # Workflow-specific agent definitions
│   │   │   │   ├── planner.md      # Planning agent overrides for auto-code
│   │   │   │   ├── coder.md        # Coding agent overrides for auto-code
│   │   │   │   └── reviewer.md     # Review agent overrides for auto-code
│   │   │   └── skills/             # Workflow-specific skills (extend global)
│   │   │       └── code/           # auto-code specific skills (test-generation, etc.)
│   │   ├── auto-design/            # Future
│   │   └── auto-market/            # Future
│   │
│   ├── router/                     # LLM Router (model_role to model mapping)
│   ├── memory/                     # Memory service (PostgreSQL tsvector + pgvector)
│   │
│   ├── db/                         # Database layer
│   │   ├── engine.py               # AsyncEngine + AsyncSession factory
│   │   ├── models.py               # SQLAlchemy mapped models
│   │   └── migrations/             # Alembic migration scripts
│   │
│   └── config/                     # Configuration loading and validation
│
├── dashboard/                      # React 19 + Vite SPA (Phase 12)
│   ├── src/
│   │   ├── app/                    # App shell, layout, routing
│   │   │   ├── shell/              # App shell component
│   │   │   └── layout/             # Layout components
│   │   ├── features/               # Feature modules (self-contained)
│   │   │   └── pipelines/          # Example feature
│   │   │       ├── pages/          # Route pages
│   │   │       ├── components/     # Feature-specific components
│   │   │       ├── hooks/          # Feature-specific hooks
│   │   │       ├── stores/         # Feature-specific stores
│   │   │       └── types/          # Feature-specific types
│   │   ├── ui/                     # Design system (atomic)
│   │   │   ├── atoms/              # Buttons, inputs, badges
│   │   │   ├── molecules/          # Cards, form groups, dropdowns
│   │   │   └── organisms/          # Navigation, sidebars, data tables
│   │   ├── lib/                    # Shared libraries (routing, data, layouts)
│   │   ├── components/             # Shared non-atomic components
│   │   ├── hooks/                  # Global hooks
│   │   ├── stores/                 # Global Zustand stores
│   │   ├── styles/                 # Global styles, Tailwind theme tokens
│   │   ├── types/                  # Shared TypeScript types
│   │   └── generated/              # hey-api output (TS client + TanStack Query hooks)
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.ts
│
├── tests/                          # Test suite (mirrors app/ structure)
│   ├── conftest.py                 # Shared fixtures and factories
│   ├── gateway/                    # Gateway route tests
│   ├── workers/                    # Worker task tests
│   ├── agents/                     # Agent tests
│   └── ...
│
├── scripts/                        # Dev and deployment scripts
│   ├── seed.py                     # Seed database with test data
│   ├── reset-db.sh                 # Drop and recreate database
│   └── ...
│
├── docs/                           # User-facing documentation (future)
│
├── .dev/                           # Architecture docs and planning (not shipped)
│   ├── .architect.md               # Architect agent instructions
│   ├── .standards.md               # Engineering standards
│   ├── .workflow.md                # Development workflow (4 levels, artifact flow, sync rules)
│   ├── 00-VISION.md                # Mission, differentiators, prior art
│   ├── 01-PRD.md                   # Product requirements document
│   ├── 02-ARCHITECTURE.md          # Technical architecture
│   ├── 03-STRUCTURE.md             # This file — project scaffold
│   ├── 04-TECH_STACK.md            # Technology choices and rationale
│   ├── 05-DEV_SETUP.md             # Development environment setup
│   ├── 06-PROVIDERS.md             # External providers
│   ├── 07-COMPONENTS.md            # Component registry (BOM)
│   ├── 08-ROADMAP.md               # Project roadmap and phased delivery
│   ├── architecture/               # Domain-specific architecture reference (14 files)
│   │   ├── gateway.md              # Gateway layer, ACL, routes, type safety
│   │   ├── workers.md              # ARQ workers, lifecycle, concurrency
│   │   ├── events.md               # Event system, Redis Streams, CEO queue
│   │   ├── data.md                 # Data layer + infrastructure
│   │   ├── engine.md               # ADK engine, App container, LLM routing
│   │   ├── agents.md               # Agent hierarchy, types, composition
│   │   ├── execution.md            # Execution loop, multi-session model
│   │   ├── state.md                # State scopes, memory architecture
│   │   ├── tools.md                # FunctionTools, GlobalToolset
│   │   ├── skills.md               # Skill system, format, triggers
│   │   ├── workflows.md            # Pluggable workflows, manifests, registry
│   │   ├── observability.md        # Observability: tracing, logging
│   │   ├── context.md             # Context assembly, budgeting, recreation
│   │   └── clients.md              # CLI + Dashboard architecture
│   ├── build-phase/                # Per-phase build artifacts
│   │   ├── .templates/             # FRD, spec, model templates
│   │   └── phase-{N}/             # frd.md, spec.md, model.md, review.md
│   ├── .discussion/                # Planning discussion documents
│   └── .notes/                     # Working notes
│
├── AGENTS.md                       # AI agent guidance (concise)
├── CLAUDE.md                       # Symlink -> AGENTS.md
├── README.md                       # Project overview and quick start
├── Dockerfile                      # Production image (deployment + CI)
├── docker-compose.yml              # Infrastructure services (postgres + redis)
├── pyproject.toml                  # Project config (uv, ruff, pyright)
└── alembic.ini                     # Alembic configuration
```

---

## Directory Responsibilities

| Directory | Role |
|-----------|------|
| `app/` | Python engine — all server-side code lives here |
| `app/cli/` | CLI interface — thin typer API client; imports `httpx` and `app/config`, never engine internals |
| `app/gateway/` | FastAPI REST + SSE layer; owns the external API contract |
| `app/gateway/middleware/` | Request middleware (auth, rate limiting, error handling, CORS) |
| `app/workers/` | ARQ async workers; execute ADK pipelines out-of-process |
| `app/events/` | Redis Streams event infrastructure (publish, consume, webhooks) |
| `app/models/` | Shared domain definitions (enums, constants, base Pydantic models) |
| `app/lib/` | Shared libraries — logging, exceptions, decorators, base classes |
| `app/utils/` | Stateless utility functions — string helpers, token counting, hashing |
| `app/agents/` | Agent definitions (.md) + infrastructure (AgentRegistry, InstructionAssembler, pipeline factory, context monitor) |
| `app/agents/custom/` | CustomAgent Python implementations (deterministic and hybrid) |
| `app/tools/` | 42 FunctionTool wrappers (8 modules) + `GlobalToolset(BaseToolset)` for per-role vending |
| `app/skills/` | Markdown skill files with YAML frontmatter |
| `app/workflows/` | Pluggable workflow definitions (each a self-contained directory) |
| `app/router/` | LLM model routing (task type to provider/model) |
| `app/memory/` | Cross-session searchable memory (PostgreSQL tsvector + pgvector) |
| `app/db/` | Database engine, ORM models, Alembic migrations |
| `app/config/` | Configuration loading, validation, defaults |
| `dashboard/` | React 19 SPA — pure API consumer, static build |
| `dashboard/src/app/` | App shell, layout, top-level routing |
| `dashboard/src/features/` | Feature modules — each owns pages, components, hooks, stores, types |
| `dashboard/src/ui/` | Design system — atomic components (atoms, molecules, organisms) |
| `dashboard/src/lib/` | Shared libraries (routing, data utilities, layouts) |
| `dashboard/src/stores/` | Global Zustand stores (SSE buffer, connection status) |
| `dashboard/src/styles/` | Global styles, Tailwind theme tokens |
| `dashboard/src/types/` | Shared TypeScript types (beyond generated) |
| `dashboard/src/generated/` | hey-api output (TS client + TanStack Query hooks) |
| `tests/` | Test suite mirroring `app/` structure |
| `scripts/` | Dev and deployment scripts (seed, reset, etc.) |
| `docs/` | User-facing documentation (future) |
| `.dev/` | Internal architecture docs and planning — not shipped |

---

*Document Version: 1.8*
*Last Updated: 2026-03-11*
