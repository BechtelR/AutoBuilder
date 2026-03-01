# Pre-Phase 5 Deliverables

*Date: 2026-02-28*
*Context: Phase 0 + Phase 4 delta remediation, Decision #49 gateway conversational interface*
*Priority: Must complete before Phase 5 (Agent Hierarchy)*
*Status: DONE*

---

## Phase 0 Remediation

- [x] Remove `app/orchestrator/` directory (orphaned placeholder, no BOM component, removed from `03-STRUCTURE.md` v1.5)
- [x] `.env.example` line 26: fix reference `.dev/11-PROVIDERS.md` → `.dev/06-PROVIDERS.md`
- [x] `.env.example` lines 16–19: update search provider comment — remove "Phase 1 TBD" and `SEARXNG_URL`, reflect Tavily+Brave decision (Roadmap Q7)
- [x] `.env.example` lines 23–24: remove `AUTOBUILDER_MAX_CONCURRENCY` and `AUTOBUILDER_SKILLS_DIR` (not loaded by Settings; Phase 8 and Phase 6 scope)

## Phase 4 Remediation

- [x] Add `DirectorQueueStatus` enum to `app/models/enums.py` — BOM V22: `PENDING`, `IN_PROGRESS`, `RESOLVED`, `FORWARDED_TO_CEO`

## Gateway — DB Models

- [x] `Chat` mapped class in `app/db/models.py` (id, session_id, type, status, title, project_id, created_at, updated_at, messages relationship)
- [x] `ChatMessage` mapped class in `app/db/models.py` (id, chat_id, role, content, created_at, chat relationship)

## Gateway — Enums

- [x] `ChatType` enum in `app/models/enums.py` (`DIRECTOR`, `PROJECT`)
- [x] `ChatStatus` enum in `app/models/enums.py` (`ACTIVE`, `ARCHIVED`)
- [x] `ChatMessageRole` enum in `app/models/enums.py` (`USER`, `DIRECTOR`)

## Gateway — Pydantic Models

- [x] `CreateChatRequest` in `app/gateway/models/chat.py`
- [x] `ChatResponse` in `app/gateway/models/chat.py`
- [x] `SendChatMessageRequest` in `app/gateway/models/chat.py`
- [x] `ChatMessageResponse` in `app/gateway/models/chat.py`

## Gateway — Migration

- [x] Alembic migration: chat tables included in `001_initial_schema.py` (rolled in during early dev)

## Gateway — Routes

- [x] `POST /chat` — create chat (`app/gateway/routes/chat.py`)
- [x] `GET /chat` — list chats with filters
- [x] `GET /chat/{session_id}` — get chat detail
- [x] `POST /chat/{session_id}/messages` — send message, enqueue Director turn
- [x] `GET /chat/{session_id}/messages` — retrieve message history
- [x] `GET /chat/{session_id}/stream` — SSE stream for Director responses (placeholder — returns chat detail; real SSE in Phase 5)
- [x] Register chat router in `app/gateway/main.py`

## Gateway — Worker Task

- [x] `run_director_turn(ctx, chat_id, message_id)` in `app/workers/tasks.py`

## Gateway — ADK Factory

- [x] `create_director_agent()` stub in `app/workers/adk.py` (echo agent until Phase 5)

## Architecture Doc Verification

- [x] `architecture/gateway.md` — `/chat` routes match implementation (v1.1)
- [x] `architecture/data.md` — `Chat` + `ChatMessage` models documented
- [x] `architecture/clients.md` — chat interface documented from client perspective (v1.1)
- [x] `02-ARCHITECTURE.md` — two interaction models (work-queue vs conversational) already explicit (line 93)
- [x] `03-STRUCTURE.md` — routes and models directories updated (v1.6)

## Testing

- [x] Unit tests: Pydantic chat models (`tests/gateway/test_chat_models.py`) — 7 tests
- [x] Integration tests: chat routes with real PostgreSQL (`tests/gateway/test_chat.py`) — 13 tests
- [x] Worker task test: Director turn with stub agent (`tests/workers/test_tasks.py`)

## Quality Gates

- [x] `uv run pyright` — zero errors
- [x] `uv run ruff check .` — zero violations
- [x] `uv run pytest tests/gateway/test_chat_models.py` — 7/7 pass

---

## References

- Phase 0 delta report: `build-phase/phase-0/delta-report.md` §Remediation Required
- Phase 4 delta report: `build-phase/phase-4/delta-report.md` §Remediation Required
- Decision #49: `.discussion/260227_project-review.md`
- Gateway design detail: prior `.todo/260227_update-gateway-design.md`
