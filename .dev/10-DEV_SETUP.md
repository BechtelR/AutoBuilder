# AutoBuilder Development Setup

## Overview

This guide walks you through setting up a local development environment for AutoBuilder. AutoBuilder is a Python-first project using Google ADK as its agent framework, with an optional TypeScript dashboard.

---

## 1. Prerequisites

### 1.1 Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Core engine runtime |
| uv | Latest | Python package manager (fast, replaces pip) |
| Redis | 7.0+ | Task queue (ARQ), event bus (Streams), cache, cron |
| Git | 2.40+ | Version control + worktree isolation |
| SQLite | 3.35+ (with FTS5) | Session persistence + memory service |

### 1.2 Optional Software

| Software | Version | Purpose |
|----------|---------|---------|
| Node.js | 20 LTS | Dashboard UI (Phase 3) |
| PostgreSQL | 15+ | Alternative to SQLite for session persistence |
| Docker | Latest | Containerized development (TBD) |

### 1.3 API Keys

At least one LLM provider API key is required:

| Provider | Environment Variable | Purpose |
|----------|---------------------|---------|
| Anthropic | `ANTHROPIC_API_KEY` | Primary LLM provider (Claude models) |
| OpenAI | `OPENAI_API_KEY` | Alternative LLM provider |
| Google | `GOOGLE_API_KEY` | Gemini models (native ADK support) |

---

## 2. Project Structure

See [03-STRUCTURE.md](./03-STRUCTURE.md) for the full project scaffold.

Each module targets a maximum of ~500 to avoid monolithic files.

---

## 3. Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# =============================================================================
# AutoBuilder Environment Configuration
# =============================================================================

# --- LLM Providers (at least one required) ---
ANTHROPIC_API_KEY=sk-ant-...          # Primary: Claude models via LiteLLM
OPENAI_API_KEY=sk-...                 # Alternative: OpenAI models
GOOGLE_API_KEY=...                    # Alternative: Gemini models (native ADK)

# --- Database ---
AUTOBUILDER_DB_URL=sqlite+aiosqlite:///./autobuilder.db   # Session persistence
# AUTOBUILDER_DB_URL=postgresql+asyncpg://user:pass@localhost:5432/autobuilder

# --- Web Search (optional, Phase 1 provider TBD) ---
# SEARXNG_URL=http://localhost:8080
# BRAVE_API_KEY=...
# TAVILY_API_KEY=tvly-...

# --- Application ---
AUTOBUILDER_LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR
AUTOBUILDER_MAX_CONCURRENCY=3         # Max parallel feature pipelines
AUTOBUILDER_SKILLS_DIR=./skills       # Additional project-local skills directory

# --- LLM Router Defaults ---
AUTOBUILDER_DEFAULT_CODE_MODEL=anthropic/claude-sonnet-4-5-20250929
AUTOBUILDER_DEFAULT_PLAN_MODEL=anthropic/claude-opus-4-6
AUTOBUILDER_DEFAULT_REVIEW_MODEL=anthropic/claude-sonnet-4-5-20250929
AUTOBUILDER_DEFAULT_FAST_MODEL=anthropic/claude-haiku-4-5-20251001
```

---

## 4. Setup Commands

### 4.1 Install uv (if not installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 4.2 Clone and Configure

```bash
git clone <repo-url>
cd AutoBuilder

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
```

### 4.3 Create Virtual Environment and Install Dependencies

```bash
# Install project with dev dependencies
uv sync
```

### 4.4 Verify Installation

```bash
# Verify ADK is available
python -c "import google.adk; print(google.adk.__version__)"

# Verify LiteLLM is available
python -c "import litellm; print(litellm.__version__)"
```

### 4.5 Running the CLI

```bash
# TBD: CLI interface is Phase 1
# Expected usage pattern:
app run --spec ./spec.md --workflow auto-code
app run --spec ./spec.md --workflow auto-code --resume
app status
app list-workflows
```

### 4.6 Running the ADK Dev UI

ADK provides a built-in development UI for debugging agent interactions:

```bash
# Start the ADK web UI (points to the app module)
adk web app/app.py

# Opens browser at http://localhost:8000 with:
# - Agent interaction traces
# - Event stream viewer
# - State inspector
# - Session management
```

---

## 5. Development Commands

### 5.1 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test directory
pytest tests/test_tools/

# Run specific test file
pytest tests/test_memory/test_sqlite_fts.py

# Run with verbose output
pytest -v

# Run only fast tests (exclude integration)
pytest -m "not integration"
```

### 5.2 Linting

```bash
# Lint check
ruff check app/ tests/

# Lint with auto-fix
ruff check --fix app/ tests/

# Type checking
pyright app/
```

### 5.3 Formatting

```bash
# Format code
ruff format app/ tests/

# Check formatting without changes
ruff format --check app/ tests/
```

---

## 6. IDE Configuration

### 6.1 VS Code Extensions

Install these extensions:

- **Python** (Microsoft)
- **Pylance** (Microsoft) -- type checking via pyright
- **Ruff** (Astral) -- linting and formatting

### 6.2 VS Code Settings

`.vscode/settings.json`:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },

  "python.analysis.typeCheckingMode": "strict",
  "python.analysis.autoImportCompletions": true,
  "python.analysis.diagnosticMode": "workspace",

  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/*.egg-info": true
  }
}
```

### 6.3 Launch Configurations

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "AutoBuilder: CLI",
      "type": "debugpy",
      "request": "launch",
      "module": "app.cli.main",
      "args": ["run", "--spec", "./spec.md", "--workflow", "auto-code"],
      "cwd": "${workspaceFolder}",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "AutoBuilder: ADK Web UI",
      "type": "debugpy",
      "request": "launch",
      "module": "google.adk.cli",
      "args": ["web", "app/app.py"],
      "cwd": "${workspaceFolder}",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "AutoBuilder: Pytest",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["-v"],
      "cwd": "${workspaceFolder}",
      "envFile": "${workspaceFolder}/.env"
    }
  ]
}
```

---

## 7. Key Dependencies

Core dependencies (defined in `pyproject.toml`):

| Package | Purpose |
|---------|---------|
| `google-adk` | Agent framework (composition, state, sessions, events) |
| `litellm` | Multi-provider LLM routing (Claude, OpenAI, Gemini via single interface) |
| `fastapi` + `uvicorn` | Gateway API server (REST + SSE, OpenAPI spec generation) |
| `sqlalchemy[asyncio]` | Async ORM for all database persistence |
| `alembic` | Database schema migrations |
| `aiosqlite` | Async SQLite driver (required by `DatabaseSessionService`) |
| `arq` | Async task queue with built-in cron (Redis-backed) |
| `redis[hiredis]` | Task queue backend, event bus (Streams), cache |
| `pydantic` | Structured outputs, config validation, API contracts |
| `httpx` | Async HTTP client for webhooks and external API calls |
| `typer` | CLI framework |
| `pyyaml` | Skill frontmatter and workflow manifest parsing |

Dev dependencies:

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support |
| `pytest-cov` | Coverage reporting |
| `ruff` | Linting + formatting |
| `pyright` | Static type checking |

Optional dependencies:

| Package | Purpose |
|---------|---------|
| `asyncpg` | Postgres async driver (alternative to SQLite) |

---

## 8. Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: google.adk` | Ensure `uv sync` completed and you are running via `uv run` |
| LiteLLM model not found | Check that the model string matches LiteLLM's expected format (e.g., `anthropic/claude-sonnet-4-5-20250929`) |
| `ANTHROPIC_API_KEY` not set | Ensure `.env` file exists and is loaded; some shells require `source .env` or use `python-dotenv` |
| SQLite FTS5 not available | Most Python distributions include FTS5; if missing, rebuild SQLite from source with `--enable-fts5` |
| ADK Dev UI not starting | Ensure `google-adk[cli]` is installed; check that `app.py` exports an `app` variable |
| Async driver error | Ensure `aiosqlite` is installed for SQLite or `asyncpg` for Postgres |

### Useful Commands

```bash
# Check Python version
python --version

# Check installed packages
uv pip list | grep -E "google-adk|litellm|aiosqlite"

# Verify SQLite FTS5 support
python -c "import sqlite3; conn = sqlite3.connect(':memory:'); conn.execute('CREATE VIRTUAL TABLE t USING fts5(content)'); print('FTS5 OK')"

# Check git worktree support
git worktree list

# Reset development database
rm -f autobuilder.db

# View ADK version
python -c "import google.adk; print(google.adk.__version__)"
```

---

## 9. Code Style Guidelines

### Naming Conventions

| Kind | Convention | Example |
|------|-----------|---------|
| Files | `snake_case.py` | `skill_loader.py` |
| Functions | `snake_case` | `resolve_model_string()` |
| Classes | `PascalCase` | `SkillLoaderAgent` |
| Constants | `SCREAMING_SNAKE` | `MAX_CONCURRENCY` |
| Type aliases | `PascalCase` | `RoutingConfig` |

### Module Size

Maximum ~500 per module. If a module grows beyond this, decompose into sub-modules. This is an explicit architectural constraint.

### Error Handling

- Use `try/except` with specific exception types
- Custom exceptions extend a base `AutoBuilderError`
- Always handle async errors -- no unhandled coroutine exceptions
- Return structured error data rather than raising where possible in tools

### Documentation

- Docstrings on all public functions (Google style)
- Keep comments focused on "why", not "what"
- Type hints on all function signatures

---

## 10. Related Documents

- Consolidated planning doc: `.dev/.discussion/260211_plan-shaping.md`
- State and memory: `.dev/08-STATE_MEMORY.md`
- Tools and agents: `.dev/09-TOOLS.md`
- ADK documentation: https://google.github.io/adk-docs/
- LiteLLM documentation: https://docs.litellm.ai/

---

*Document Version: 1.0*
*Last Updated: 2026-02-11*
