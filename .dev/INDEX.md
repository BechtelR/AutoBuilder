# .dev/ Document Index

Quick-reference map to truth source files. Use this to find what you need fast.

---

## Core Documents

| # | File | Purpose | Key Truth |
|---|------|---------|-----------|
| — | `.architect.md` | System identity & design philosophy | What AutoBuilder is, core principles, anti-patterns |
| — | `.standards.md` | Engineering standards & anti-patterns | When to use CustomAgent vs LlmAgent, over-engineering red flags |
| — | `.workflow.md` | Development workflow | 4 levels from idea to verified code; artifact flow, sync rules |
| 00 | `00-VISION.md` | Product vision & strategy | Differentiators, problem statement, what we are NOT |
| 01 | `01-PRD.md` | Product requirements (PRD) | User experience deconstructed, personas, journeys, FRs |
| 02 | `02-ARCHITECTURE.md` | System architecture | Five-layer design, data flow, API-first + ADK behind ACL |
| 03 | `03-STRUCTURE.md` | Project scaffold | **Single source of truth** for directory layout |
| 04 | `04-TECH_STACK.md` | Technology decisions & rationale | Every tech choice with why + rejected alternatives |
| 05 | `05-DEV_SETUP.md` | Development environment setup | Prerequisites, env vars, local dev workflow |
| 06 | `06-PROVIDERS.md` | External providers | LLM models, pricing, fallback chains, search providers |
| 07 | `07-COMPONENTS.md` | Component Registry (BOM) | **Every buildable component** → phase assignment; gap detection |
| 08 | `08-ROADMAP.md` | Phased delivery plan & status | **Current phase**, acceptance criteria, delivery order |
| — | `.decision-log.md` | Architecture decisions log | All decisions with rationale, date, and rejected alternatives |

### Architecture Reference (`architecture/`)

Domain-specific L2 deep dives linked from `02-ARCHITECTURE.md` §4. Each is self-contained.

| File | Domain | Key Questions Answered |
|------|--------|----------------------|
| `agents.md` | Agent hierarchy & definitions | How do Director/PM/Workers compose? What tools does each tier get? |
| `clients.md` | CLI & dashboard clients | What API calls does each client make? Chat vs. work queue model? |
| `context.md` | Context assembly & budgeting | How are instructions assembled? How does context recreation work? |
| `data.md` | Data layer & infrastructure | What tables exist? How do Redis and PostgreSQL divide concerns? |
| `engine.md` | ADK engine internals | How do ADK primitives map to AutoBuilder? Session types? |
| `events.md` | Event system (Redis Streams) | How are events published, consumed, and replayed? SSE reconnection? |
| `execution.md` | Autonomous execution loop | How do Director and PM loops run? Multi-session architecture? |
| `gateway.md` | Gateway layer (FastAPI) | Route structure? Anti-corruption pattern? Auth and middleware? |
| `observability.md` | Tracing, logging, monitoring | OpenTelemetry + Langfuse phased rollout? Event stream visibility? |
| `skills.md` | Skills system | Skill file format? Trigger matching? Three-tier library model? |
| `state.md` | State & memory architecture | 4-scope state system? Memory service? Cross-session persistence? |
| `tools.md` | Tools & GlobalToolset | FunctionTool patterns? What built-ins does ADK provide? |
| `workers.md` | Worker architecture (ARQ) | Worker lifecycle? Cron jobs? Concurrency model? |
| `workflows.md` | Workflow composition system | Manifest format? Stage schema? Registry? Completion criteria? |

---

## Supporting Directories

| Directory | Purpose | Key Contents |
|-----------|---------|--------------|
| `.discussion/` | Design evolution & decisions | Timestamped discussion transcripts (e.g., `260214_hierarchical-supervision.md`) |
| `architecture/` | Domain-specific architecture reference | See expanded table above (Architecture Reference) |
| `build-phase/` | Per-phase build artifacts | `.templates/` (frd, spec, model), `phase-{N}/` (frd.md, spec.md, model.md, review.md) |
| `.knowledge/` | Multi-domain reference index | `README.md` → domain dirs; `adk/` has 13 category files + ERRATA |
| `.todo/` | Active task tracking | Phase-specific task lists |

---

## "Where do I find..."

| Question | File(s) |
|----------|---------|
| What is AutoBuilder? | `00-VISION.md`, `.architect.md` |
| What phase are we in? | `08-ROADMAP.md` |
| How does data flow through the system? | `02-ARCHITECTURE.md` |
| Where does file X go? | `03-STRUCTURE.md` |
| Why did we pick technology X? | `04-TECH_STACK.md` |
| How do agents compose? | `architecture/agents.md`, `02-ARCHITECTURE.md` |
| How do agents get context? | `architecture/context.md`, `architecture/skills.md`, `architecture/state.md` |
| How do I add a new workflow? | `architecture/workflows.md` |
| What is a workflow manifest? | `architecture/workflows.md` §3 |
| How do workflow stages and validators work? | `architecture/workflows.md` §4–§6 |
| How does workflow completion reporting work? | `architecture/workflows.md` §7 |
| How does the Director author workflows? | `architecture/workflows.md` §9 |
| What is the `auto-code` workflow? | `architecture/workflows.md` §12 |
| How does state persist? | `architecture/state.md` |
| What tools are available? | `architecture/tools.md` |
| How do I set up local dev? | `05-DEV_SETUP.md` |
| What external providers do we use? | `06-PROVIDERS.md` |
| Why was decision X made? | `.decision-log.md` |
| How does ADK feature X work? | `.knowledge/adk/README.md` → category file → WebFetch URL |
| What are the coding standards? | `.standards.md`, `CLAUDE.md` (project root) |
| What is the development workflow? | `.workflow.md` |
| What are the product requirements? | `01-PRD.md` |
| What components are in Phase N? | `07-COMPONENTS.md` (filter by phase) |
| What components are unassigned? | `07-COMPONENTS.md` (search for `—` in Phase column) |
| What are Phase N's build artifacts? | `build-phase/phase-{N}/` (frd.md, spec.md, model.md, review.md) |

---

## Knowledge Base
Before working with ADK code or designs, must read `.knowledge/adk/README.md` → category file → `ERRATA.md`. Never guess ADK APIs.

## Cross-References

- **03-STRUCTURE.md** is referenced by: `02-ARCHITECTURE.md`, `05-DEV_SETUP.md`, `CLAUDE.md`
- **08-ROADMAP.md** is the status tracker — update it when phases complete
- **04-TECH_STACK.md** justifies choices; `.decision-log.md` records when/why they changed
- **.standards.md** and root `CLAUDE.md` both govern code style — standards is the superset
- **architecture/** files are linked from `02-ARCHITECTURE.md` §4 reference map
- **07-COMPONENTS.md** is the BOM — derived from `architecture/` files, assigns components to roadmap phases
- **PostToolUse hook** (`scripts/check-arch-change.sh`) fires on architecture file edits → reminds to update BOM + roadmap
