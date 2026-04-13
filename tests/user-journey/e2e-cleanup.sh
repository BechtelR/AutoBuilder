#!/usr/bin/env bash
# E2E Cleanup — removes test project, deliverables, chat messages, and result artifacts.
# Usage: bash tests/user-journey/e2e-cleanup.sh [project_id]
#   If project_id is omitted, reads it from e2e-results.json.
set -euo pipefail

OUTPUT_DIR="tests/user-journey/.output"
RESULTS_FILE="$OUTPUT_DIR/e2e-results.json"

PROJECT_ID="${1:-}"
if [ -z "$PROJECT_ID" ] && [ -f "$RESULTS_FILE" ]; then
  PROJECT_ID=$(jq -r '.project_id // empty' "$RESULTS_FILE" 2>/dev/null || true)
fi

if [ -z "$PROJECT_ID" ]; then
  echo "Usage: $0 <project_id>"
  echo "  Or run after e2e-workflow-runner.sh (reads from $RESULTS_FILE)"
  exit 1
fi

# Validate UUID format to prevent SQL injection
if ! echo "$PROJECT_ID" | grep -qE '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'; then
  echo "ERROR: PROJECT_ID is not a valid UUID: $PROJECT_ID" >&2
  exit 1
fi

echo "Cleaning up project: $PROJECT_ID"

# Delete DB artifacts in FK-safe order. Use a temp table to capture workflow_ids
# before deliverables are deleted (workflows link to projects via deliverables).
docker compose exec -T postgres psql -U autobuilder -d autobuilder -c "
  BEGIN;
  -- Capture workflow IDs before we delete deliverables
  CREATE TEMP TABLE _e2e_wf_ids AS
    SELECT DISTINCT workflow_id FROM deliverables WHERE project_id = '$PROJECT_ID';

  -- Validator results (via workflow_id)
  DELETE FROM validator_results WHERE workflow_id IN (SELECT workflow_id FROM _e2e_wf_ids);
  -- Artifacts (via deliverable entity_id)
  DELETE FROM artifacts WHERE entity_id IN (
    SELECT id FROM deliverables WHERE project_id = '$PROJECT_ID'
  );
  -- Task group executions (via stage_execution_id -> stage_executions -> workflow)
  DELETE FROM taskgroup_executions WHERE stage_execution_id IN (
    SELECT id FROM stage_executions WHERE workflow_id IN (SELECT workflow_id FROM _e2e_wf_ids)
  );
  -- Stage executions (via workflow_id)
  DELETE FROM stage_executions WHERE workflow_id IN (SELECT workflow_id FROM _e2e_wf_ids);
  -- Deliverables
  DELETE FROM deliverables WHERE project_id = '$PROJECT_ID';
  -- Project tasks
  DELETE FROM project_tasks WHERE project_id = '$PROJECT_ID';
  -- Project configs
  DELETE FROM project_configs WHERE project_id = '$PROJECT_ID';
  -- Director queue items for this project
  DELETE FROM director_queue WHERE source_project_id = '$PROJECT_ID';
  -- CEO queue items for this project
  DELETE FROM ceo_queue WHERE source_project_id = '$PROJECT_ID';
  -- Capture specification IDs before deleting workflows
  CREATE TEMP TABLE _e2e_spec_ids AS
    SELECT DISTINCT specification_id FROM workflows
    WHERE id IN (SELECT workflow_id FROM _e2e_wf_ids)
    AND specification_id IS NOT NULL;
  -- Workflows (now safe -- deliverables FK already removed)
  DELETE FROM workflows WHERE id IN (SELECT workflow_id FROM _e2e_wf_ids);
  -- Specifications (now safe -- workflow FK already removed)
  DELETE FROM specifications WHERE id IN (SELECT specification_id FROM _e2e_spec_ids);
  DROP TABLE _e2e_spec_ids;
  -- The project itself
  DELETE FROM projects WHERE id = '$PROJECT_ID';

  DROP TABLE _e2e_wf_ids;
  COMMIT;
"

# Clean up chat messages from main session (E2E test messages)
docker compose exec -T postgres psql -U autobuilder -d autobuilder -c "
  DELETE FROM chat_messages WHERE chat_id IN (
    SELECT id FROM chats WHERE title = 'Main'
  );
"

# Clean up ADK-managed sessions (created by google-adk DatabaseSessionService).
# ADK stores sessions keyed by app_name='autobuilder'. We delete all session
# data for the test app to avoid stale state on re-runs.
docker compose exec -T postgres psql -U autobuilder -d autobuilder -c "
  DO \$\$
  BEGIN
    -- ADK tables may not exist if worker never ran; guard with IF EXISTS
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'events') THEN
      DELETE FROM events WHERE session_id IN (
        SELECT session_id FROM sessions WHERE app_name = 'autobuilder'
      );
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'app_states') THEN
      DELETE FROM app_states WHERE app_name = 'autobuilder';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_states') THEN
      DELETE FROM user_states WHERE app_name = 'autobuilder';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sessions') THEN
      DELETE FROM sessions WHERE app_name = 'autobuilder';
    END IF;
  END \$\$;
"

# Clean up ARQ job queue and workflow event streams
docker compose exec -T redis redis-cli --no-auth-warning EVAL "
  local deleted = 0
  -- ARQ keys
  local arq_keys = redis.call('keys', 'arq:job:*')
  for _,k in ipairs(arq_keys) do redis.call('del', k) end
  redis.call('del', 'arq:queue')
  deleted = deleted + #arq_keys
  -- Workflow event streams (workflow:{uuid}:events)
  local stream_keys = redis.call('keys', 'workflow:*:events')
  for _,k in ipairs(stream_keys) do redis.call('del', k) end
  deleted = deleted + #stream_keys
  -- Director/project lifecycle keys
  redis.call('del', 'director:paused')
  local pause_keys = redis.call('keys', 'project:pause_requested:*')
  for _,k in ipairs(pause_keys) do redis.call('del', k) end
  deleted = deleted + #pause_keys
  -- Active work session locks
  local ws_keys = redis.call('keys', 'director:work_session:*')
  for _,k in ipairs(ws_keys) do redis.call('del', k) end
  deleted = deleted + #ws_keys
  return deleted
" 0

# Remove runtime output
rm -rf "$OUTPUT_DIR"

echo "Cleanup complete"
