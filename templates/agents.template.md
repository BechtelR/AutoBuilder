# AGENTS.md - [DOMAIN NAME]
(file is 150 lines or less)

## Preferences
- Brief and concise explanations; time is precious
- Think outside the box, create innovation
- Pragmatic simplicity over architectural complexity
- Question assumptions - don't automatically agree, challenge requirements if they don't make sense
- Your role is the expert engineer with the voice of Truth
- System security and privacy are non-negotiable
- Performance matters - measure don't guess
- User experience should be delightful
- Developer experience should be delightful
- Documentation should enable, not overwhelm

## Tech Stack
- Languages: [PRIMARY LANGUAGE AND VERSION]
- Framework: [PRIMARY FRAMEWORK]
- Package Manager: [PACKAGE MANAGER]
- [OTHER KEY TECHNOLOGIES]

## Workspace Commands
```bash
# Development
[DEV_COMMAND]          # Start dev server
[BUILD_COMMAND]        # Build
[TEST_COMMAND]         # Run tests
[TYPECHECK_COMMAND]    # Type checking

# [DOMAIN-SPECIFIC COMMANDS]
```

## Architecture Rules
- Generic > Specific (registries, not hardcoded lists)
- Single source of truth for all configuration
- Async by default for all I/O operations
- Event-driven > Request-response for scale
- Fail fast with meaningful error messages
- [DOMAIN-SPECIFIC RULES]

## Code Style
- Strict typing enforced
- Async by default for all I/O operations
- Prefer composition over deep inheritance
- Use interfaces/protocols over concrete types
- Validate inputs at service boundaries
- Immutable data patterns where possible
- Fail fast with meaningful error messages
- [DOMAIN-SPECIFIC STYLE RULES]
- Example: UI
```
- Use semantic theme classes, not hardcoded colors
- Import shared components from the design system package
```

## Project Structure
```
[DOMAIN-PATH]/
├── [MAIN-DIRECTORIES]
└── [SUB-DIRECTORIES]
```

## Project Architecture
Explain the key design and models of this feature or framework. Describe the fundamental structures, shared resources, database/API communication, how this feature/framework is integrated with others and how it fits in the whole project, etc.

## Critical DOs
- Understand the design or problem BEFORE writing code
- Ask clarifying questions
- Make security decisions early, not as an afterthought
- Fail fast and fail loudly with meaningful error messages
- Type-check early and often - most common build error
- Build for composition over inheritance
- [DOMAIN-SPECIFIC DOS]

## Critical DON'Ts
- NEVER MAKE UP NON-EXISTENT FILES, FACTS OR REFERENCES
- NEVER IGNORE EXISTING ERRORS
- Don't assume dependencies already exist
- Don't bypass type checking with `any`/`Any`
- Don't commit secrets or API keys
- Don't expose sensitive data to external services unprotected
- [DOMAIN-SPECIFIC DON'TS]
- Example: UI
```
- Don't use hardcoded styles (prefer theme variables)
- Don't install UI libraries directly in apps (use shared design system)
```

## Security
- **Input Validation**: Validate all inputs at service boundaries
- **No Secrets in Code**: Never hardcode secrets, use environment variables
- **Secure Defaults**: Fail-safe patterns, explicit security configurations
- **Sensitive Data**: No sensitive data in logs, external calls, or client responses
- [DOMAIN-SPECIFIC SECURITY REQUIREMENTS]

## Quick Troubleshooting
```bash
# [DOMAIN-SPECIFIC TROUBLESHOOTING COMMANDS]
```

## Credentials
Where to find or lookup credentials needed for project actions; web logins, database access, etc.

## URLs ([ENVIRONMENT])
- [DOMAIN-SPECIFIC URLs]

## Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./app.db` | Database connection |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `LOG_LEVEL` | `INFO` | Log verbosity |
| [DOMAIN-SPECIFIC VARIABLES] | | |

## Related Documentation
- **[BLUEPRINT.md](./BLUEPRINT.md)**: Technical architecture and design
- **[README.md](./README.md)**: Setup and introduction
- **[docs/](./docs/)**: Additional documentation (if applicable)
- [DOMAIN-SPECIFIC DOCUMENTATION LINKS]
