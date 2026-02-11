# AutoBuilder Tech Stack

## Overview

AutoBuilder is a Python-first autonomous agentic workflow system with a TypeScript web UI. The core engine handles all orchestration, agent coordination, state management, and tool execution in Python. TypeScript is used exclusively for the dashboard/web UI layer, which is a separate concern from the orchestration engine.

This document details every technology choice with rationale for inclusion.

---

## 1. Core Framework: Google ADK

**Choice**: Google Agent Development Kit (ADK) v1.14.0+

**Rationale**: AutoBuilder needs two fundamentally different types of tool execution: LLM-discretionary ("use search if you need info") and deterministic ("run linter, run tests, format code"). ADK is the only evaluated framework where deterministic tools are first-class citizens via `CustomAgent` (inheriting `BaseAgent`). They participate in the same state system as LLM agents, appear in the same event stream for observability, cannot be skipped by LLM judgment, and compose naturally with LLM agents in Sequential/Parallel/Loop workflows.

AutoBuilder is fundamentally an orchestration problem where LLM agents are one component alongside deterministic tooling. ADK treats this as the core design principle.

**Alternatives Evaluated**:

| Framework | Why Not |
|-----------|---------|
| Pydantic AI | All tools are LLM-discretionary; deterministic steps exist in a "shadow world" outside the framework, invisible to tracing and state management |
| Claude Agent SDK | Single-agent harness, not a workflow orchestrator; Claude-only, TypeScript-only |
| Custom framework | Both ADK and PAI handle multi-model natively; building our own provider abstraction is unnecessary |

**ADK Primitives Used**:

| Primitive | Role in AutoBuilder |
|-----------|-------------------|
| `LlmAgent` | Planning, coding, reviewing -- probabilistic steps |
| `CustomAgent` (BaseAgent) | Linter, test runner, formatter, skill loader, outer loop orchestrator -- deterministic steps |
| `SequentialAgent` | Inner feature pipeline (plan, code, lint, test, review) |
| `ParallelAgent` | Concurrent feature execution within a batch |
| `LoopAgent` | Review/fix cycles with max iteration bounds |
| `Session State` | Inter-agent communication (4 scopes: session/user/app/temp) |
| `Event Stream` | Unified observability for all agent types |
| `InstructionProvider` | Dynamic context/knowledge loading per invocation |
| `before_model_callback` | Context injection, token budget monitoring |
| `BaseToolset` | Dynamic tool selection based on feature type |
| `DatabaseSessionService` | State persistence to SQLite/Postgres |

**Acknowledged Tradeoffs**:

| Weakness | Severity | Mitigation |
|----------|----------|------------|
| Gemini-first bias | Medium | LiteLLM wrapper for Claude; test thoroughly in prototyping |
| No Temporal-style durability | Medium-Low | Native Resume feature (v1.16+) covers most crash scenarios; evaluate Temporal only if insufficient |
| Google ecosystem gravity | Medium | Discipline: local SQLite/Postgres only; skip all Vertex AI services |
| Documentation accuracy issues | Low | Test everything empirically |
| Type safety less emphasized | Low | Use Pydantic models for structured outputs within ADK agents |
| No context-window usage awareness | Low | `before_model_callback` token-count implementation (~50 lines) |

**Key Dependencies**:
```python
google-adk>=1.14.0
```

---

## 2. LLM Integration: LiteLLM

**Choice**: LiteLLM for multi-model support

**Rationale**: AutoBuilder routes different tasks to different LLM providers based on capability, cost, and speed. LiteLLM provides a unified interface across providers (Anthropic, OpenAI, Google, etc.) without requiring separate SDK integrations for each. It also handles provider fallback chains -- if a primary model is unavailable or rate-limited, the system falls back gracefully.

**Why not direct SDKs**: Using the Anthropic SDK directly would lock all tasks to a single provider. Using multiple SDKs (anthropic, openai, google-generativeai) would require maintaining separate integration code for each. LiteLLM provides a single interface that ADK consumes via its LiteLLM wrapper class.

**Key Dependencies**:
```python
litellm>=1.0.0
```

---

## 3. Primary LLM: Anthropic Claude

**Choice**: Anthropic Claude as the primary model family

**Rationale**: Best-in-class for code generation, instruction following, and agentic workflows. Large context window (200K tokens) supports the long autonomous runs AutoBuilder requires.

**Model Tiers and Routing**:

| Task Type | Model | Rationale |
|-----------|-------|-----------|
| Planning | `anthropic/claude-opus-4-6` | Complex architectural reasoning |
| Code implementation (standard) | `anthropic/claude-sonnet-4-5-20250929` | Strong coding, good cost/quality balance |
| Code implementation (complex) | `anthropic/claude-opus-4-6` | Maximum capability for difficult tasks |
| Code review | `anthropic/claude-sonnet-4-5-20250929` | Good judgment, reasonable cost |
| Classification / summarization | `anthropic/claude-haiku-4-5-20251001` | Fast, cheap, sufficient for simple tasks |
| Context compression (summarizer) | `anthropic/claude-haiku-4-5-20251001` | Fast summaries without burning expensive tokens |

**Routing Configuration**:

```yaml
routing_rules:
  - task_type: code_implementation
    complexity: standard
    model: "anthropic/claude-sonnet-4-5-20250929"
  - task_type: code_implementation
    complexity: complex
    model: "anthropic/claude-opus-4-6"
  - task_type: planning
    model: "anthropic/claude-opus-4-6"
  - task_type: review
    model: "anthropic/claude-sonnet-4-5-20250929"
  - task_type: classification
    model: "anthropic/claude-haiku-4-5-20251001"
  - task_type: summarization
    model: "anthropic/claude-haiku-4-5-20251001"

fallback_chains:
  anthropic/claude-opus-4-6: ["anthropic/claude-sonnet-4-5-20250929"]
  anthropic/claude-sonnet-4-5-20250929: ["anthropic/claude-haiku-4-5-20251001"]
```

Phase 1 implements static routing (task_type to model lookup table). Adaptive routing with cost tracking and latency monitoring deferred to Phase 2.

---

## 4. Database: SQLite (Phase 1) / PostgreSQL (Production)

**Choice**: SQLite for development and Phase 1; PostgreSQL for production deployment

**Rationale**: ADK's `DatabaseSessionService` supports both SQLite and PostgreSQL via async drivers. SQLite provides zero-configuration local development with no external dependencies. PostgreSQL provides production-grade persistence when needed. The same `DatabaseSessionService` API works with both -- only the connection string changes.

**Session persistence**: All session history, state (4 scopes), and event replay are managed by `DatabaseSessionService`.

**Async drivers required**:
- SQLite: `sqlite+aiosqlite`
- PostgreSQL: `asyncpg`

**Key Dependencies**:
```python
aiosqlite>=0.19.0       # SQLite async driver (Phase 1)
asyncpg>=0.28.0         # PostgreSQL async driver (production)
```

---

## 5. Memory: SQLite FTS5

**Choice**: Custom `BaseMemoryService` implementation backed by SQLite FTS5 full-text search

**Rationale**: ADK's `MemoryService` interface (`BaseMemoryService`) has two methods: `add_session_to_memory()` and `search_memory()`. The only production-ready built-in implementation is `VertexAiMemoryBankService` (GCP-only, which we are avoiding). `InMemoryMemoryService` is keyword-only and non-persistent.

AutoBuilder needs local, persistent, searchable cross-session memory so that feature 47 can know what patterns features 1-10 established. SQLite FTS5 provides full-text search built into SQLite with zero additional dependencies. It is sufficient for queries like "what architectural patterns did we establish in features 1-10?" without requiring a vector store or external service.

**Implementation scope**: ~200-300 lines for `SqliteFtsMemoryService` implementing `BaseMemoryService`.

**Phase 2 evaluation**: If FTS5 proves insufficient for semantic similarity queries, upgrade to a hybrid approach with local embeddings + vector store (ChromaDB/FAISS/SQLite-VSS).

**No additional dependencies** -- SQLite FTS5 is a built-in SQLite extension.

---

## 6. Python Runtime: 3.11+

**Choice**: Python 3.11+ with asyncio

**Rationale**:
- Agent ecosystem is Python-first; Google ADK, Pydantic AI, LangChain, CrewAI are all Python-native
- Strong async support via `asyncio` for concurrent agent execution
- Google ADK requires Python 3.11+
- Type hints + pyright provide TypeScript-like type safety

**Alternatives Considered**:

| Language | Why Not |
|----------|---------|
| TypeScript/Node | Weaker agent framework ecosystem; ADK is Python-only |
| Go | Smaller agent ecosystem, more boilerplate, no ADK support |
| Rust | Overkill for orchestration, no ADK support |

---

## 7. CLI Framework: TBD

**Status**: Open decision for Phase 1.

The CLI is the primary user interface for Phase 1 (web dashboard is Phase 3). Requirements:
- Start/stop autonomous runs
- Specify workflow + spec file
- Configure model routing
- Monitor progress
- Human-in-the-loop intervention points

Candidates under evaluation: `click`, `typer`, `argparse`. Decision deferred until prototyping validates the core ADK integration.

---

## 8. Development Tools

| Tool | Purpose | Rationale |
|------|---------|-----------|
| `ruff` | Python linting + formatting | Replaces black, isort, flake8 in a single tool; fast (Rust-based) |
| `pyright` | Python type checking | TypeScript-like type safety for Python; catches bugs before runtime |
| `pytest` | Python testing | Industry standard; excellent plugin ecosystem |
| `pytest-asyncio` | Async test support | Required for testing ADK async agent execution |
| `pre-commit` | Git hooks for automated checks | Enforces lint/type checks before commits |

---

## 9. Package Management: uv

**Choice**: `uv` for Python package management

**Rationale**: Fast Rust-based package manager and virtual environment manager. Drop-in replacement for pip + venv with dramatically faster resolution and installation. Generates `uv.lock` for deterministic builds.

---

## 10. Dependencies

### pyproject.toml Skeleton

```toml
[project]
name = "autobuilder"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # Core Framework
    "google-adk>=1.14.0",

    # LLM Integration
    "litellm>=1.0.0",

    # Database (Phase 1: SQLite)
    "aiosqlite>=0.19.0",

    # Database (Production: PostgreSQL)
    # "asyncpg>=0.28.0",

    # Structured Data
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",

    # Utilities
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.4.0",
    "pyright>=1.1.0",
    "pre-commit>=3.5.0",
]

postgres = [
    "asyncpg>=0.28.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "SIM", "TCH"]

[tool.pyright]
pythonVersion = "3.11"
typeCheckingMode = "standard"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Key Dependency Rationale

| Dependency | Why Included |
|------------|-------------|
| `google-adk` | Core framework: agent composition, state management, event stream, session services |
| `litellm` | Multi-model LLM routing without separate SDKs per provider |
| `aiosqlite` | Async SQLite driver for `DatabaseSessionService` (Phase 1) |
| `asyncpg` | Async PostgreSQL driver for production `DatabaseSessionService` |
| `pydantic` | Structured outputs from LLM agents; validation; settings management |
| `pyyaml` | Skill frontmatter parsing; workflow manifest parsing; routing config |

### What Is NOT Included

| Dependency | Why Excluded |
|------------|-------------|
| `anthropic` SDK | LiteLLM handles Anthropic API calls; direct SDK adds redundancy |
| `openai` SDK | Same -- LiteLLM abstracts provider SDKs |
| `langchain` | ADK provides its own composition primitives; LangChain would be redundant |
| `chromadb` / `faiss` | Vector store deferred to Phase 2; SQLite FTS5 sufficient for Phase 1 |
| `celery` / `redis` | No background task queue needed; ADK handles async execution natively |
| Any GCP SDK | Avoiding Google ecosystem gravity; local SQLite/Postgres only |

---

*Document Version: 1.0*
*Last Updated: February 2026*
