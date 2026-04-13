#!/usr/bin/env bash
# E2E Workflow Runner — drives a full user journey through the AutoBuilder API.
# Usage: bash tests/user-journey/e2e-workflow-runner.sh
# Requires: docker compose stack running, jq installed
set -euo pipefail

API="http://localhost:8000"
BRIEF_FILE="tests/user-journey/fixtures/e2e-workflow-brief.json"
POLL_INTERVAL=10
MAX_POLL_DIRECTOR=24    # 2 min for Director response
MAX_POLL_PROJECT=60     # 10 min for project completion
OUTPUT_DIR="tests/user-journey/.output"
RESULTS_FILE="$OUTPUT_DIR/e2e-results.json"

# --- Helpers ---
fail() { echo "FAIL: $1" >&2; exit 1; }
info() { echo "[$(date +%H:%M:%S)] $1"; }

check_jq() { command -v jq &>/dev/null || fail "jq is required"; }

check_health() {
  local health
  health=$(curl -sf "$API/health" 2>/dev/null) || fail "Gateway not responding at $API/health"
  echo "$health" | jq -e '.status == "ok"' &>/dev/null || fail "Gateway unhealthy: $health"
  info "Gateway healthy"
}

check_worker() {
  # Check if the worker container is running (more reliable than grepping logs,
  # which may have scrolled past the startup message).
  docker compose ps --status running --format '{{.Service}}' 2>/dev/null \
    | grep -q '^worker$' \
    || fail "Worker container not running — check: docker compose ps"
  info "Worker running"
}

# --- Phase 1: Get main chat session ---
get_main_session() {
  local resp
  resp=$(curl -sf "$API/chat/main") || fail "Cannot get main chat session"
  echo "$resp" | jq -r '.session_id'
}

# --- Phase 2: Send brief and wait for Director ---
send_brief() {
  local session_id="$1"
  local resp
  resp=$(curl -sf -X POST "$API/chat/$session_id/messages" \
    -H "Content-Type: application/json" \
    -d @"$BRIEF_FILE") || fail "Cannot send message"
  echo "$resp" | jq -r '.id'
}

wait_for_director() {
  local session_id="$1"
  for i in $(seq 1 "$MAX_POLL_DIRECTOR"); do
    local messages
    messages=$(curl -sf "$API/chat/$session_id/messages") || continue
    local director_count
    director_count=$(echo "$messages" | jq '[.[] | select(.role == "DIRECTOR")] | length')
    if [ "$director_count" -gt 0 ]; then
      info "Director responded after $((i * 5))s"
      echo "$messages" | jq -r '[.[] | select(.role == "DIRECTOR")][0].content' | head -5
      return 0
    fi
    sleep 5
  done
  fail "Director did not respond within $((MAX_POLL_DIRECTOR * 5))s"
}

# --- Phase 3: Find project and monitor ---
find_project() {
  # List projects ordered by created_at desc and pick the newest one that was
  # created within the last 5 minutes. This avoids grabbing a stale project
  # from a previous test run or a concurrent creation.
  local projects
  projects=$(curl -sf "$API/projects") || fail "Cannot list projects"
  local project_id
  # jq fromdateiso8601 requires "Z" suffix and no fractional seconds.
  # Python/Pydantic datetimes may include microseconds and/or "+00:00" offset,
  # so we strip both before parsing.
  project_id=$(echo "$projects" | jq -r '
    def parse_dt: split("+")[0] | split(".")[0] + "Z" | fromdateiso8601;
    [.[] | select(
      (.created_at | parse_dt) > (now - 300)
    )] | .[0].id // empty
  ')
  [ -n "$project_id" ] || fail "No project created in the last 5 minutes"
  echo "$project_id"
}

monitor_project() {
  local project_id="$1"
  local status stage
  for i in $(seq 1 "$MAX_POLL_PROJECT"); do
    local project
    project=$(curl -sf "$API/projects/$project_id") || continue
    status=$(echo "$project" | jq -r '.status')
    stage=$(echo "$project" | jq -r '.current_stage // "none"')
    info "[$((i * POLL_INTERVAL))s] Status: $status, Stage: $stage"

    # Show deliverable progress
    curl -sf "$API/deliverables?project_id=$project_id" 2>/dev/null \
      | jq -r '.[] | "  \(.name): \(.status)"' 2>/dev/null || true

    if [ "$status" = "COMPLETED" ] || [ "$status" = "ABORTED" ]; then
      echo "$status"
      return 0
    fi

    # Auto-resolve CEO queue items every 3rd poll to avoid blocking
    if (( i % 3 == 0 )); then
      resolve_ceo_queue
    fi

    sleep "$POLL_INTERVAL"
  done
  echo "TIMEOUT"
}

resolve_ceo_queue() {
  local items
  items=$(curl -sf "$API/ceo/queue" | jq '[.[] | select(.status == "PENDING")]')
  local count
  count=$(echo "$items" | jq 'length')
  if [ "$count" -gt 0 ]; then
    info "Resolving $count CEO queue items"
    echo "$items" | jq -r '.[].id' | while read -r item_id; do
      curl -sf -X PATCH "$API/ceo/queue/$item_id" \
        -H "Content-Type: application/json" \
        -d '{"action": "RESOLVE", "resolution": "Approved for E2E test", "resolver": "e2e-test"}' \
        >/dev/null
      info "  Resolved: $item_id"
    done
  fi
}

# --- Phase 4: Collect results ---
collect_results() {
  local project_id="$1" final_status="$2"
  local project deliverables director_queue ceo_queue

  project=$(curl -sf "$API/projects/$project_id")
  deliverables=$(curl -sf "$API/deliverables?project_id=$project_id")
  director_queue=$(curl -sf "$API/director/queue" | jq 'length')
  ceo_queue=$(curl -sf "$API/ceo/queue" | jq 'length')

  # Build results JSON
  jq -n \
    --arg status "$final_status" \
    --arg project_id "$project_id" \
    --argjson project "$project" \
    --argjson deliverables "$deliverables" \
    --argjson director_queue_count "$director_queue" \
    --argjson ceo_queue_count "$ceo_queue" \
    '{
      verdict: (if $status == "COMPLETED" and ($project.deliverable_failed // 0) > 0 then "PARTIAL"
                elif $status == "COMPLETED" then "PASS"
                elif $status == "ABORTED" then "FAIL"
                elif $status == "TIMEOUT" then "TIMEOUT"
                else "BLOCKED" end),
      project_id: $project_id,
      final_status: $status,
      accumulated_cost: $project.accumulated_cost,
      deliverable_total: $project.deliverable_total,
      deliverable_completed: $project.deliverable_completed,
      deliverable_failed: $project.deliverable_failed,
      director_queue_items: $director_queue_count,
      ceo_queue_items: $ceo_queue_count,
      deliverables: [$deliverables[] | {name, status, retry_count}]
    }' \
    > "$RESULTS_FILE"

  info "Results written to $RESULTS_FILE"
  cat "$RESULTS_FILE" | jq .
}

# --- Main ---
main() {
  info "=== E2E Workflow Test ==="
  mkdir -p "$OUTPUT_DIR"
  check_jq
  check_health
  check_worker

  info "--- Phase 1: Get main chat session ---"
  SESSION_ID=$(get_main_session)
  info "Session: $SESSION_ID"

  info "--- Phase 2: Send brief to Director ---"
  MSG_ID=$(send_brief "$SESSION_ID")
  info "Message sent: $MSG_ID"
  wait_for_director "$SESSION_ID"

  info "--- Phase 3: Monitor execution ---"
  PROJECT_ID=$(find_project)
  info "Project: $PROJECT_ID"

  FINAL_STATUS=$(monitor_project "$PROJECT_ID")
  if [ "$FINAL_STATUS" = "TIMEOUT" ]; then
    # Check if blocked on CEO queue
    resolve_ceo_queue
    info "Resuming monitoring after CEO queue resolution..."
    FINAL_STATUS=$(monitor_project "$PROJECT_ID")
  fi

  info "--- Phase 4: Results ---"
  collect_results "$PROJECT_ID" "$FINAL_STATUS"

  # Lifecycle guard verification
  if [ "$FINAL_STATUS" = "COMPLETED" ] || [ "$FINAL_STATUS" = "ABORTED" ]; then
    PAUSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/projects/$PROJECT_ID/pause")
    RESUME_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/projects/$PROJECT_ID/resume")
    info "Lifecycle guards: pause=$PAUSE_CODE resume=$RESUME_CODE (expected 409)"
  fi

  info "=== Done ==="
  info "Cleanup: bash tests/user-journey/e2e-cleanup.sh $PROJECT_ID"
}

main "$@"
