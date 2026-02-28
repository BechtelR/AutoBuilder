# Pre-Phase 5 Deliverables

*Date: 2026-02-28*
*Context: Phase 0 + Phase 4 delta remediation, Decision #49 gateway conversational interface*
*Priority: Must complete before Phase 5 (Agent Hierarchy)*

---

## Phase 0 Remediation

- [ ] Remove `app/orchestrator/` directory (orphaned placeholder, no BOM component, removed from `03-STRUCTURE.md` v1.5)
- [ ] `.env.example` line 26: fix reference `.dev/11-PROVIDERS.md` → `.dev/06-PROVIDERS.md`
- [ ] `.env.example` lines 16–19: update search provider comment — remove "Phase 1 TBD" and `SEARXNG_URL`, reflect Tavily+Brave decision (Roadmap Q7)
- [ ] `.env.example` lines 23–24: remove `AUTOBUILDER_MAX_CONCURRENCY` and `AUTOBUILDER_SKILLS_DIR` (not loaded by Settings; Phase 8 and Phase 6 scope)

## Phase 4 Remediation

- [ ] Add `DirectorQueueStatus` enum to `app/models/enums.py` — BOM V22: `PENDING`, `IN_PROGRESS`, `RESOLVED`, `FORWARDED_TO_CEO`

## Gateway — DB Models

- [ ] `Chat` mapped class in `app/db/models.py` (id, session_id, type, status, title, project_id, created_at, updated_at, messages relationship)
- [ ] `ChatMessage` mapped class in `app/db/models.py` (id, chat_id, role, content, created_at, chat relationship)

## Gateway — Enums

- [ ] `ChatType` enum in `app/models/enums.py` (`DIRECTOR`, `PROJECT`)
- [ ] `ChatStatus` enum in `app/models/enums.py` (`ACTIVE`, `ARCHIVED`)
- [ ] `ChatMessageRole` enum in `app/models/enums.py` (`USER`, `DIRECTOR`)

## Gateway — Pydantic Models

- [ ] `CreateChatRequest` in `app/gateway/models/chat.py`
- [ ] `ChatResponse` in `app/gateway/models/chat.py`
- [ ] `SendChatMessageRequest` in `app/gateway/models/chat.py`
- [ ] `ChatMessageResponse` in `app/gateway/models/chat.py`

## Gateway — Migration

- [ ] Alembic migration: `uv run alembic revision --autogenerate -m "add chat and chat messages" --rev-id NNN`

## Gateway — Routes

- [ ] `POST /chat` — create chat (`app/gateway/routes/chat.py`)
- [ ] `GET /chat` — list chats with filters
- [ ] `GET /chat/{session_id}` — get chat detail
- [ ] `POST /chat/{session_id}/messages` — send message, enqueue Director turn
- [ ] `GET /chat/{session_id}/messages` — retrieve message history
- [ ] `GET /chat/{session_id}/stream` — SSE stream for Director responses
- [ ] Register chat router in `app/gateway/main.py`

## Gateway — Worker Task

- [ ] `run_director_turn(ctx, chat_id, message_id)` in `app/workers/tasks.py`

## Gateway — ADK Factory

- [ ] `create_director_agent()` stub in `app/workers/adk.py` (echo agent until Phase 5)

## Architecture Doc Verification

- [ ] `architecture/gateway.md` — `/chat` routes match implementation
- [ ] `architecture/data.md` — `Chat` + `ChatMessage` models documented
- [ ] `architecture/clients.md` — chat interface documented from client perspective
- [ ] `02-ARCHITECTURE.md` — two interaction models (work-queue vs conversational) explicit
- [ ] `03-STRUCTURE.md` — `app/gateway/routes/chat.py` and `app/gateway/models/chat.py` in scaffold

## Testing

- [ ] Unit tests: Pydantic chat models (`tests/gateway/test_chat_models.py`)
- [ ] Integration tests: chat routes with real PostgreSQL (`tests/gateway/test_chat.py`)
- [ ] Worker task test: Director turn with stub agent

---

## References

- Phase 0 delta report: `build-phase/phase-0/delta-report.md` §Remediation Required
- Phase 4 delta report: `build-phase/phase-4/delta-report.md` §Remediation Required
- Decision #49: `.discussion/260227_project-review.md`
- Gateway design detail: prior `.todo/260227_update-gateway-design.md`
