# AGENTS.md

This file provides guidance to AI coding agents working in the AutoBuilder repository.

## Project Overview

AutoBuilder is an autonomous agentic workflow system built on Google ADK that orchestrates multi-agent teams alongside deterministic tooling in structured, resumable pipelines. It supports pluggable workflow composition (auto-code, auto-design, auto-research, etc.), dynamic LLM routing across providers via LiteLLM, six-level progressive memory architecture, skill-based knowledge injection, and git worktree isolation for parallel execution. The system runs continuously from specification to verified output with optional human-in-the-loop intervention points.

- **Engine**: Python 3.11+
- **Framework**: Google ADK (Agent Development Kit)
- **Multi-model**: LiteLLM for provider-agnostic model routing
- **UI** (future): TypeScript web dashboard (separate concern from engine)

Architecture planning docs live in `.dev/.discussion/` — read `260211_plan-shaping.md` for the consolidated planning document.

---

## Project Structure (Planned)

```
AutoBuilder/
├── autobuilder/                  # Python engine (main package)
│   ├── app.py                    # ADK App container (entry point)
│   ├── agents/                   # Agent definitions
│   │   ├── deterministic/        # CustomAgent subclasses (linter, test runner, skill loader, etc.)
│   │   └── llm/                  # LlmAgent definitions (planner, coder, reviewer)
│   ├── tools/                    # FunctionTool wrappers (filesystem, bash, git, web, todo)
│   ├── skills/                   # Global skill files (Markdown + YAML frontmatter)
│   │   ├── code/
│   │   ├── review/
│   │   ├── test/
│   │   └── planning/
│   ├── workflows/                # Pluggable workflow definitions
│   │   ├── auto-code/
│   │   │   ├── WORKFLOW.yaml     # Manifest: triggers, tools, models, pipeline type
│   │   │   ├── pipeline.py       # ADK agent composition
│   │   │   └── agents/           # Workflow-specific agent definitions
│   │   ├── auto-design/          # Future
│   │   └── auto-market/          # Future
│   ├── router/                   # LLM Router (task_type to model mapping)
│   ├── memory/                   # SqliteFtsMemoryService (BaseMemoryService implementation)
│   ├── orchestrator/             # BatchOrchestrator (outer loop CustomAgent)
│   └── config/                   # Configuration loading and validation
├── tests/                        # Test suite (mirrors autobuilder/ structure)
├── .dev/                         # Planning docs and standards (not shipped)
│   ├── .architect.md             # Architect agent instructions
│   ├── .standards.md             # Engineering standards
│   ├── 09-DELIVERY.md            # Phased delivery plan
│   ├── .discussion/              # Planning discussion documents
│   └── .notes/                   # Working notes
├── AGENTS.md                     # This file
├── pyproject.toml                # Project config (uv/pip, ruff, pyright)
└── README.md                     # TBD
```

---

## Framework: Google ADK

AutoBuilder uses Google ADK (Agent Development Kit) as its orchestration framework. ADK was selected because it treats deterministic tools (`CustomAgent`) and LLM agents (`LlmAgent`) as equal workflow participants in the same event stream, state system, and tracing infrastructure.

### Key Primitives

| Primitive | Role in AutoBuilder |
|-----------|-------------------|
| `LlmAgent` | Planning, coding, reviewing — probabilistic steps requiring LLM judgment |
| `CustomAgent` (BaseAgent) | Linter, test runner, formatter, skill loader, orchestrator — deterministic steps |
| `SequentialAgent` | Inner feature pipeline (plan, code, lint, test, review) |
| `ParallelAgent` | Concurrent feature execution within a batch |
| `LoopAgent` | Review/fix cycles with max iteration bounds |
| `Session State` | Inter-agent communication (4 scopes: session, user, app, temp) |
| `Event Stream` | Unified observability for all agent types |
| `FunctionTool` | Wrap Python functions as LLM-callable tools (auto-schema from type hints) |
| `InstructionProvider` | Dynamic context/knowledge loading per invocation |
| `before_model_callback` | Context injection, token budget monitoring |
| `DatabaseSessionService` | State persistence to SQLite or Postgres |

### Multi-Model via LiteLLM

LiteLLM provides the model abstraction layer. Model strings use the LiteLLM format (e.g., `anthropic/claude-sonnet-4-5-20250929`). The LLM Router selects models per task based on routing configuration.

---

## Build & Dev Commands

```bash
# Package management (uv)
uv sync                           # Install dependencies from pyproject.toml
uv add <package>                  # Add a dependency
uv add --dev <package>            # Add a dev dependency

# Running
uv run python -m autobuilder      # Run AutoBuilder (TBD — entry point)
uv run adk web                    # ADK Dev UI for local debugging

# Testing
uv run pytest                     # Run all tests
uv run pytest tests/path/to/test_file.py  # Run a single test file
uv run pytest -k "pattern"        # Run tests matching a name pattern
uv run pytest --cov=autobuilder   # Run with coverage report

# Linting & Formatting
uv run ruff check .               # Lint
uv run ruff check --fix .         # Lint with auto-fix
uv run ruff format .              # Format
uv run ruff format --check .      # Format check (CI)

# Type Checking
uv run pyright                    # Type check (strict mode)
```

---

## Testing

- **Framework**: `pytest` with `pytest-asyncio` for async tests
- **Factory patterns** for test data: `create_feature()`, `create_session()`, `create_skill_entry()`
- **Coverage target**: >80% line coverage
- **Test files**: `test_<module>.py` inside `tests/` directory mirroring source structure
- **Mocking**: Mock external services (LLM calls, filesystem) — never call real APIs in unit tests
- **Integration tests**: May use real ADK primitives with `InMemorySessionService`

---

## Code Style Guidelines

### Language

- **Python 3.11+** with full type hints on all function signatures
- **asyncio** for all I/O operations

### Formatting (ruff)

- Line length: **100**
- Quote style: **TBD** (double or single — decide before first commit)
- Import sorting: isort-compatible rules via ruff
- Enforced via pre-commit hooks

### Imports

Import order (enforced by ruff):

1. Standard library (`os`, `pathlib`, `asyncio`)
2. Third-party (`google.adk`, `pydantic`, `litellm`)
3. Local (`autobuilder.agents`, `autobuilder.tools`)

```python
import asyncio
from pathlib import Path

from google.adk.agents import LlmAgent, SequentialAgent
from pydantic import BaseModel

from autobuilder.agents.deterministic.skill_loader import SkillLoaderAgent
from autobuilder.tools.filesystem import file_read, file_write
```

### Naming Conventions

| Kind | Convention | Example |
|------|-----------|---------|
| Files | `snake_case.py` | `skill_loader.py` |
| Functions | `snake_case` | `resolve_model_string()` |
| Classes | `PascalCase` | `BatchOrchestrator` |
| Protocols | `PascalCase` | `MemoryService` |
| Constants | `SCREAMING_SNAKE` | `MAX_CONCURRENCY`, `DEFAULT_MODEL` |
| Pydantic models | `PascalCase` | `RoutingConfig`, `FeatureSpec` |
| State keys | `snake_case` | `current_feature_spec`, `app:coding_standards` |
| Test files | `test_<module>.py` | `test_skill_loader.py` |

### Type Patterns

- **Pydantic `BaseModel`** for structured outputs from LLM agents and external boundaries
- **`Protocol`** for interfaces with multiple implementations (e.g., `MemoryService`)
- **`dataclass`** or **`TypedDict`** for internal DTOs
- **`Enum`** for fixed sets of values
- **No `Any`** — use `object` for truly dynamic data, explicit types everywhere
- **pyright strict mode** enforced

### Error Handling

- Catch `Exception`, narrow with `isinstance`
- Return sensible defaults rather than throwing where possible
- Custom exception classes for domain errors
- Always handle async errors

```python
try:
    result = await tool.execute(params)
except Exception as e:
    if isinstance(e, RateLimitError):
        await backoff_and_retry(e)
    elif isinstance(e, ToolExecutionError):
        logger.error(f"Tool failed: {e.tool_name} — {e.message}")
        return ToolResult(success=False, error=str(e))
    else:
        raise
```

### Module Size

Max **~300 lines** per module. If a file grows past this, split it. Exceptions are rare and must be documented.

---

## Architecture Overview

### Agent Types

**Deterministic agents** (`CustomAgent` subclasses) — guaranteed workflow steps:
- `SkillLoaderAgent` — resolve and load relevant skills into state
- `LinterAgent` — run project linter, write results to state
- `TestRunnerAgent` — run test suite, write results to state
- `FormatterAgent` — run code formatter
- `DependencyResolverAgent` — topological sort of features
- `RegressionTestAgent` — run cross-feature regression suite
- `ContextBudgetAgent` — check token usage, trigger compression if needed

**LLM agents** (`LlmAgent`) — probabilistic steps requiring judgment:
- `plan_agent` — generate implementation plan from feature spec
- `code_agent` — write code from plan
- `review_agent` — review code quality against standards
- `fix_agent` — fix issues identified by review

### State Scopes

| Prefix | Scope | Lifetime | Use |
|--------|-------|----------|-----|
| *(none)* | Session | Per-run (persistent via DB) | Feature statuses, loaded skills, test results |
| `user:` | User | Cross-session | Preferences, model selections |
| `app:` | App | Cross-user, cross-session | Project config, conventions, skill index |
| `temp:` | Temp | Current invocation only | Scratch data, intermediate LLM outputs |

Plus `MemoryService` for cross-session searchable knowledge archive.

### Pipeline Structure

```
Outer loop (BatchOrchestrator — CustomAgent):
  While incomplete features exist:
    Select next batch (dependency-aware)
    ParallelAgent(batch):
      For each feature — SequentialAgent:
        SkillLoaderAgent (deterministic)
        plan_agent (LLM)
        code_agent (LLM)
        LinterAgent (deterministic)
        TestRunnerAgent (deterministic)
        LoopAgent(review cycle, max N):
          review_agent (LLM)
          fix_agent (LLM)
          LinterAgent (deterministic)
          TestRunnerAgent (deterministic)
    Run regression tests
    Checkpoint
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `.dev/.architect.md` | Architect agent instructions — principles, constraints, quality checklist |
| `.dev/.standards.md` | Engineering standards — coding rules, naming, patterns |
| `.dev/09-DELIVERY.md` | Phased delivery plan — MVP scope, phases, risks |
| `.dev/.discussion/260211_plan-shaping.md` | Consolidated planning document — full architecture decisions |
| `.dev/.discussion/260211_technical-spike-adk-vs-pydantic.md` | ADK vs Pydantic AI evaluation |

---

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | Yes (if using Claude) |
| `OPENAI_API_KEY` | OpenAI API key | No (if using OpenAI models) |
| `GOOGLE_API_KEY` | Google API key for Gemini models | No (if using Gemini) |
| `LITELLM_LOG` | LiteLLM logging level | No |
| `AUTOBUILDER_DB_URL` | Database URL for session persistence (default: `sqlite+aiosqlite:///./autobuilder_sessions.db`) | No |
| `AUTOBUILDER_LOG_LEVEL` | Logging level (default: `INFO`) | No |

---

*Document version: 1.0.0 | Last updated: 2026-02-11*
