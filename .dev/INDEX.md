# .dev/ Document Index

Quick-reference map to truth source files. Use this to find what you need fast.

---

## Core Documents

| # | File | Purpose | Key Truth |
|---|------|---------|-----------|
| — | `.architect.md` | System identity & design philosophy | What AutoBuilder is, core principles, anti-patterns |
| — | `.standards.md` | Engineering standards & anti-patterns | When to use CustomAgent vs LlmAgent, over-engineering red flags |
| 00 | `00-VISION.md` | Product vision & strategy | Differentiators, problem statement, what we are NOT |
| 01 | `01-ROADMAP.md` | Phased delivery plan & status | **Current phase**, acceptance criteria, delivery order |
| 02 | `02-ARCHITECTURE.md` | System architecture | Five-layer design, data flow, API-first + ADK behind ACL |
| 03 | `03-STRUCTURE.md` | Project scaffold | **Single source of truth** for directory layout |
| 04 | `04-TECH_STACK.md` | Technology decisions & rationale | Every tech choice with why + rejected alternatives |
| 05 | `05-AGENTS.md` | Agent architecture | Agent types, composition, plan/execute separation |
| 06 | `06-SKILLS.md` | Skill-based knowledge injection | Progressive disclosure, skill file format, trigger matching |
| 07 | `07-WORKFLOWS.md` | Pluggable workflow system | Workflow manifests, registry, why workflows are generic |
| 08 | `08-STATE_MEMORY.md` | State & memory architecture | ADK 4-scope state, session rewind, cross-session memory |
| 09 | `09-TOOLS.md` | Tools & deterministic agents | FunctionTool vs CustomAgent, MCP guidance, tool isolation |
| 10 | `10-DEV_SETUP.md` | Development environment setup | Prerequisites, env vars, local dev workflow |
| 11 | `11-PROVIDERS.md` | External providers | LLM models, pricing, fallback chains, search providers |

---

## Supporting Directories

| Directory | Purpose | Key Contents |
|-----------|---------|--------------|
| `.discussion/` | Design evolution & decisions | `design-changelog.md` — canonical decision record (28 decisions) |
| `.knowledge/` | Multi-domain reference index | `README.md` → domain dirs; `adk/` has 13 category files + ERRATA |
| `.todo/` | Active task tracking | Phase-specific task lists |

---

## "Where do I find..."

| Question | File(s) |
|----------|---------|
| What is AutoBuilder? | `00-VISION.md`, `.architect.md` |
| What phase are we in? | `01-ROADMAP.md` |
| How does data flow through the system? | `02-ARCHITECTURE.md` |
| Where does file X go? | `03-STRUCTURE.md` |
| Why did we pick technology X? | `04-TECH_STACK.md` |
| How do agents compose? | `05-AGENTS.md`, `02-ARCHITECTURE.md` |
| How do agents get context? | `06-SKILLS.md`, `08-STATE_MEMORY.md` |
| How do I add a new workflow? | `07-WORKFLOWS.md` |
| How does state persist? | `08-STATE_MEMORY.md` |
| What tools are available? | `09-TOOLS.md` |
| How do I set up local dev? | `10-DEV_SETUP.md` |
| What external providers do we use? | `11-PROVIDERS.md` |
| Why was decision X made? | `.discussion/design-changelog.md` |
| How does ADK feature X work? | `.knowledge/adk/README.md` → category file → WebFetch URL |
| What are the coding standards? | `.standards.md`, `CLAUDE.md` (project root) |

---

## Knowledge Base
Before working with ADK code or designs, must read `.knowledge/adk/README.md` → category file → `ERRATA.md`. Never guess ADK APIs.

## Cross-References

- **03-STRUCTURE.md** is referenced by: `02-ARCHITECTURE.md`, `10-DEV_SETUP.md`, `CLAUDE.md`
- **01-ROADMAP.md** is the status tracker — update it when phases complete
- **04-TECH_STACK.md** justifies choices; `.discussion/design-changelog.md` records when/why they changed
- **.standards.md** and root `CLAUDE.md` both govern code style — standards is the superset
