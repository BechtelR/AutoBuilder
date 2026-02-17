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
│   │   ├── routes/                 # Route modules (workflows, sessions, events, health)
│   │   ├── models/                 # Pydantic request/response models (API contracts)
│   │   ├── middleware/             # Auth, rate limiting, error handling, CORS
│   │   ├── sse.py                  # SSE endpoint — subscribes to Redis Streams
│   │   └── deps.py                 # Dependency injection (DB sessions, Redis, services)
│   │
│   ├── workers/                    # ARQ async workers
│   │   ├── settings.py             # ARQ WorkerSettings (Redis URL, queues, cron jobs)
│   │   └── tasks.py                # Task definitions (workflow execution, cleanup)
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
│   ├── agents/                     # Agent definitions
│   │   ├── custom/                 # CustomAgent subclasses (linter, test runner, skill loader)
│   │   └── llm/                    # LlmAgent definitions (planner, coder, reviewer)
│   │
│   ├── tools/                      # FunctionTool wrappers + AutoBuilderToolset
│   │   ├── toolset.py              # AutoBuilderToolset(BaseToolset) — per-role tool vending
│   │   ├── filesystem.py           # file_read, file_write, file_edit, file_search, directory_list
│   │   ├── execution.py            # bash_exec
│   │   ├── git.py                  # git_status, git_commit, git_branch, git_diff
│   │   ├── web.py                  # web_search, web_fetch
│   │   ├── task.py                 # todo_read, todo_write, todo_list
│   │   └── project.py              # select_ready_batch, enqueue_ceo_item
│   │
│   ├── skills/                     # Global skill files (Markdown + YAML frontmatter)
│   │   ├── code/                   # Code-generation skills
│   │   ├── review/                 # Code-review skills
│   │   ├── test/                   # Test-writing skills
│   │   └── planning/               # Planning and decomposition skills
│   │
│   ├── workflows/                  # Pluggable workflow definitions
│   │   ├── auto-code/              # First workflow
│   │   │   ├── WORKFLOW.yaml       # Manifest: triggers, tools, models, pipeline type
│   │   │   ├── pipeline.py         # ADK agent composition
│   │   │   └── agents/             # Workflow-specific agent definitions
│   │   ├── auto-design/            # Future
│   │   └── auto-market/            # Future
│   │
│   ├── router/                     # LLM Router (task_type to model mapping)
│   ├── memory/                     # Memory service (PostgreSQL tsvector + pgvector)
│   │
│   ├── db/                         # Database layer
│   │   ├── engine.py               # AsyncEngine + AsyncSession factory
│   │   ├── models.py               # SQLAlchemy mapped models
│   │   └── migrations/             # Alembic migration scripts
│   │
│   └── config/                     # Configuration loading and validation
│
├── dashboard/                      # React 19 + Vite SPA (Phase 3)
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
│   ├── 00-VISION.md                # Mission, differentiators, prior art
│   ├── 01-ROADMAP.md               # Project roadmap and phased delivery
│   ├── 02-ARCHITECTURE.md          # Technical architecture
│   ├── 03-STRUCTURE.md             # This file — project scaffold
│   ├── 04-TECH_STACK.md            # Technology choices and rationale
│   ├── architecture/               # Domain-specific architecture reference (13 files)
│   │   ├── gateway.md              # Gateway layer, ACL, routes, type safety
│   │   ├── workers.md              # ARQ workers, lifecycle, concurrency
│   │   ├── events.md               # Event system, Redis Streams, CEO queue
│   │   ├── data.md                 # Data layer + infrastructure
│   │   ├── engine.md               # ADK engine, App container, LLM routing
│   │   ├── agents.md               # Agent hierarchy, types, composition
│   │   ├── execution.md            # Execution loop, multi-session model
│   │   ├── state.md                # State scopes, memory architecture
│   │   ├── tools.md                # FunctionTools, AutoBuilderToolset
│   │   ├── skills.md               # Skill system, format, triggers
│   │   ├── workflows.md            # Pluggable workflows, manifests, registry
│   │   ├── observability.md        # Observability, context management
│   │   └── clients.md              # CLI + Dashboard architecture
│   ├── 05-DEV_SETUP.md              # Development environment setup
│   ├── 06-PROVIDERS.md              # External providers
│   ├── .discussion/                 # Planning discussion documents
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
| `app/agents/` | ADK agent definitions (deterministic and LLM) |
| `app/tools/` | FunctionTool wrappers organized by type + `AutoBuilderToolset(BaseToolset)` for per-role vending |
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

*Document Version: 1.4*
*Last Updated: 2026-02-16*
