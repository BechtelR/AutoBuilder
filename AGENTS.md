**DEPRECATED: Content is outdated and innacurate**

# AGENTS.md

This file provides guidance to AI coding agents working in the AutoBuilder repository.

## Project Overview

AutoBuilder is an autonomous agentic workflow system built on Google ADK that orchestrates multi-agent teams alongside deterministic tooling in structured, resumable pipelines. It supports pluggable workflow composition (auto-code, auto-design, auto-research, etc.), dynamic LLM routing across providers via LiteLLM, six-level progressive memory architecture, skill-based knowledge injection, and git worktree isolation for parallel execution. The system runs continuously from specification to verified output with optional human-in-the-loop intervention points. Built as a Python engine with TypeScript UI.

Architecture planning docs live in `.dev/.discussion/` — read `260114_plan-shaping.md` for full context on decisions and architecture.

## Monorepo Structure

```
AutoBuilder/
├── core/
│   ├── providers/          # AI provider implementations (Claude, OpenAI, Ollama)
│   ├── workflows/          # Workflow types (auto-code, auto-design, auto-market)
│   └── tools/              # Agent tool definitions (file, shell, workflow-specific)
├── apps/
│   ├── cli/                # CLI application (primary interface)
│   └── dashboard/          # Optional web UI (Express + WebSocket + React)
├── libs/                   # Shared utility packages (@autobuilder/*)
│   ├── types/              # Core TypeScript definitions (no dependencies)
│   ├── utils/              # Logging, errors, utilities
│   ├── platform/           # Path management, security
│   ├── git-utils/          # Git operations & worktree management
│   ├── dependency-resolver/# Feature dependency ordering (topological sort)
│   ├── model-resolver/     # Model alias resolution
│   └── prompts/            # AI prompt templates
└── .dev/                   # Planning docs and notes (not shipped)
```

## Build & Dev Commands

```bash
# Install dependencies
npm install

# Build all shared packages (required before app builds)
npm run build:packages      # Builds libs in dependency order

# Development
npm run dev                 # Interactive dev launcher
npm run dev:server          # Server with hot reload (tsx watch)
npm run dev:web             # Web UI dev server

# Full build
npm run build               # Build packages + apps

# Formatting
npm run format              # Prettier write
npm run format:check        # Prettier check (CI)
```

## Testing

Test framework: **Vitest** with `globals: true` (no need to import describe/it/expect).

```bash
# Run all tests
npm run test:all

# Run package tests only (libs)
npm run test:packages

# Run server tests only
npm run test:server

# Run a single test file
npx vitest run path/to/file.test.ts

# Run tests matching a name pattern
npx vitest run -t "pattern"

# Watch mode
npm run test:unit:watch
```

## Linting

```bash
npm run lint                # ESLint (UI app)
npm run format:check        # Prettier check
```

Pre-commit hook (Husky + lint-staged) auto-runs `prettier --write` on staged files.

## Code Style Guidelines

### Language & Module System

- **TypeScript** with `strict: true` everywhere
- **ES Modules** — every `package.json` has `"type": "module"`
- **NodeNext** module resolution for libs/server; **Bundler** for UI
- **Node.js >= 22**

### Formatting (Prettier)

- Semicolons: **yes**
- Quotes: **single**
- Tab width: **2 spaces**
- Trailing commas: **es5**
- Print width: **100**
- Arrow parens: **always**
- End of line: **lf**

### Imports

- **Type-only imports** when importing only types: `import type { Feature } from '@autobuilder/types';`
- **Package imports** for shared code: `import { createLogger } from '@autobuilder/utils';`
- **`.js` extension** on relative imports (required by NodeNext): `import { helper } from './helper.js';`
- **No default exports** — use named exports exclusively
- **Import order**: Node built-ins, external packages, `@autobuilder/*` packages, relative imports
- **Never import from internal paths** of another package — always use the barrel export

```typescript
// Correct
import type { Feature, ExecuteOptions } from '@autobuilder/types';
import { createLogger, classifyError } from '@autobuilder/utils';
import { resolveModelString } from '@autobuilder/model-resolver';

// Wrong — don't reach into another package's internals
import { Feature } from '../services/feature-loader';
```

### Naming Conventions

| Kind              | Convention           | Example                          |
|-------------------|----------------------|----------------------------------|
| Files             | `kebab-case.ts`      | `execution-engine.ts`            |
| Functions         | `camelCase`          | `resolveModelString()`           |
| Classes           | `PascalCase`         | `ExecutionEngine`                |
| Interfaces/Types  | `PascalCase`         | `AgentProvider`, `WorkflowType`  |
| Constants         | `SCREAMING_SNAKE`    | `MAX_CONCURRENCY`, `ANSI`        |
| Enums             | `PascalCase`         | `LogLevel.ERROR`                 |
| Custom errors     | `PascalCase + Error` | `PathNotAllowedError`            |

### Type Patterns

- Use `interface` for object shapes and contracts (e.g., `AgentProvider`, `Workflow`)
- Use `type` for unions, intersections, and aliases (e.g., `type ErrorType = 'auth' | 'rate-limit'`)
- Use `export type` in barrel `index.ts` files for type-only re-exports
- Use optional properties (`prop?: Type`) rather than `prop: Type | undefined`
- Use `unknown` over `any` — lint warns on `@typescript-eslint/no-explicit-any`

### Error Handling

- Catch blocks use `unknown` type: `catch (error: unknown)`
- Narrow with `instanceof Error` or guard functions (`isAbortError()`, `isRateLimitError()`)
- Create custom error classes extending `Error` with a `.name` property
- Classify errors via typed utility: `classifyError()` returning `ErrorInfo`
- Return sensible defaults rather than throwing where possible
- Always handle async errors — no unhandled promise rejections

```typescript
class ProviderError extends Error {
  name = 'ProviderError';
  constructor(message: string, public readonly provider: string) {
    super(message);
  }
}

try {
  await provider.execute(options);
} catch (error: unknown) {
  const info = classifyError(error);
  logger.error(`Provider failed: ${info.message}`);
}
```

### Documentation

- JSDoc with `@param`, `@returns`, `@example` on all public API functions
- Keep comments focused on **why**, not **what**

### Module & Export Patterns

- Barrel `index.ts` files re-export public API from implementation files
- Separate type-only exports: `export type { Feature } from './feature.js';`
- Mixed re-exports: `export { CLAUDE_MODEL_MAP, type ModelAlias } from './model.js';`

### Testing Conventions

- Test files: `<source-file>.test.ts` inside a `tests/` directory
- Use `describe`/`it`/`expect` (globals from vitest config)
- Use `vi.mock()` and `vi.resetModules()` for module mocking
- Create factory helpers for test data: `createFeature()`, `createProvider()`
- Cover edge cases: null, undefined, empty arrays, boundary conditions
- Coverage thresholds: 90%+ lines, 95%+ functions, 75%+ branches

### Package Dependency Chain

Packages may only depend on packages above them in this list:

```
@autobuilder/types          (no dependencies)
    ↓
@autobuilder/utils, @autobuilder/platform, @autobuilder/model-resolver,
@autobuilder/dependency-resolver, @autobuilder/prompts
    ↓
@autobuilder/git-utils
    ↓
apps (cli, dashboard)
```

### Key Architectural Patterns

- **Provider Abstraction**: `AgentProvider` interface with per-model implementations; capability-based routing via `ProviderRouter`
- **Async Generators**: Providers yield `AgentEvent` via `AsyncGenerator` for streaming
- **Parallel Execution**: `Promise.all` over batches, isolated via git worktrees
- **Event-Driven**: Server operations emit events streamed to UI via WebSocket
- **CLI-First**: Primary interface is CLI (`auto-builder` command); dashboard is optional

### Environment Variables

- `ANTHROPIC_API_KEY` — Anthropic API key (or use Claude OAuth)
- `OPENAI_API_KEY` — OpenAI API key
- `PORT` — Server port (default: 3008)
- `DATA_DIR` — Data storage directory
- `ALLOWED_ROOT_DIRECTORY` — Restrict file operations to a directory
