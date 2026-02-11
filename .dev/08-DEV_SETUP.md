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

Planned directory layout based on the consolidated architecture:

```
autobuilder/
├── src/autobuilder/
│   ├── agents/              # LLM + deterministic agent definitions
│   │   ├── plan_agent.py
│   │   ├── code_agent.py
│   │   ├── review_agent.py
│   │   ├── fix_agent.py
│   │   ├── skill_loader.py  # SkillLoaderAgent (deterministic)
│   │   ├── linter.py        # LinterAgent (deterministic)
│   │   ├── test_runner.py   # TestRunnerAgent (deterministic)
│   │   ├── formatter.py     # FormatterAgent (deterministic)
│   │   ├── dependency_resolver.py  # DependencyResolverAgent (deterministic)
│   │   ├── regression_test.py      # RegressionTestAgent (deterministic)
│   │   └── context_budget.py       # ContextBudgetAgent (deterministic)
│   ├── tools/               # FunctionTool implementations
│   │   ├── filesystem.py    # file_read, file_write, file_edit, file_search, directory_list
│   │   ├── execution.py     # bash_exec
│   │   ├── web.py           # web_search, web_fetch
│   │   ├── task.py          # todo_read, todo_write, todo_list
│   │   └── git.py           # git_status, git_commit, git_branch, git_diff
│   ├── skills/              # Global skills library
│   │   ├── code/
│   │   ├── review/
│   │   ├── test/
│   │   └── planning/
│   ├── workflows/           # Pluggable workflow definitions
│   │   └── auto-code/       # First workflow
│   │       ├── WORKFLOW.yaml
│   │       ├── pipeline.py
│   │       ├── agents/
│   │       └── skills/
│   ├── memory/              # SqliteFtsMemoryService
│   │   └── sqlite_fts.py
│   ├── router/              # LLM Router
│   │   └── llm_router.py
│   ├── cli/                 # CLI interface
│   │   └── main.py
│   └── app.py               # ADK App container
├── tests/
│   ├── test_tools/
│   ├── test_agents/
│   ├── test_memory/
│   ├── test_router/
│   └── test_workflows/
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

Note: Each module targets a maximum of ~300 lines to avoid monolithic files. See consolidated planning doc, Patterns Explicitly Avoided.

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
AUTOBUILDER_DB_URL=sqlite:///./autobuilder_sessions.db   # Session persistence
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
cd autobuilder

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
```

### 4.3 Create Virtual Environment and Install Dependencies

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install project with dev dependencies
uv pip install -e ".[dev]"
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
autobuilder run --spec ./spec.md --workflow auto-code
autobuilder run --spec ./spec.md --workflow auto-code --resume
autobuilder status
autobuilder list-workflows
```

### 4.6 Running the ADK Dev UI

ADK provides a built-in development UI for debugging agent interactions:

```bash
# Start the ADK web UI (points to the app module)
adk web src/autobuilder/app.py

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
pytest --cov=autobuilder --cov-report=html

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
ruff check src/ tests/

# Lint with auto-fix
ruff check --fix src/ tests/

# Type checking
pyright src/
```

### 5.3 Formatting

```bash
# Format code
ruff format src/ tests/

# Check formatting without changes
ruff format --check src/ tests/
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

  "python.analysis.typeCheckingMode": "basic",
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
      "module": "autobuilder.cli.main",
      "args": ["run", "--spec", "./spec.md", "--workflow", "auto-code"],
      "cwd": "${workspaceFolder}",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "AutoBuilder: ADK Web UI",
      "type": "debugpy",
      "request": "launch",
      "module": "google.adk.cli",
      "args": ["web", "src/autobuilder/app.py"],
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
| `aiosqlite` | Async SQLite driver (required by `DatabaseSessionService`) |
| `pydantic` | Structured outputs, config validation |

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
| `ModuleNotFoundError: google.adk` | Ensure virtual environment is activated and `uv pip install -e ".[dev]"` completed |
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
rm -f autobuilder_sessions.db

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

Maximum ~300 lines per module. If a module grows beyond this, decompose into sub-modules. This is an explicit architectural constraint. See consolidated planning doc, Patterns Explicitly Avoided.

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
- State and memory: `.dev/06-STATE_MEMORY.md`
- Tools and agents: `.dev/07-TOOLS.md`
- ADK documentation: https://google.github.io/adk-docs/
- LiteLLM documentation: https://docs.litellm.ai/

---

*Document Version: 1.0*
*Last Updated: 2026-02-11*
