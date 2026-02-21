#!/bin/bash
set -euo pipefail

# PostToolUse hook: cascading document pipeline integrity checks
# Trigger 1: architecture change → update BOM
# Trigger 2: BOM change → check STRUCTURE + ROADMAP

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // .tool_input.file // ""')

# Trigger 1: Architecture file changed → remind to update BOM
if [[ "$file_path" == *".dev/architecture/"* ]] || [[ "$file_path" == *".dev/02-ARCHITECTURE.md"* ]]; then
  filename=$(basename "$file_path")
  cat <<EOF
{
  "systemMessage": "ARCHITECTURE CHANGE DETECTED: ${filename} was modified. Update the Component Registry (.dev/07-COMPONENTS.md) BEFORE continuing: (1) Add new components with phase assignments, (2) Update or remove changed/deleted components, (3) Verify no new gaps (unassigned phase '—')."
}
EOF
  exit 0
fi

# Trigger 2: BOM changed → remind to check STRUCTURE + ROADMAP
if [[ "$file_path" == *".dev/07-COMPONENTS.md"* ]]; then
  cat <<EOF
{
  "systemMessage": "COMPONENT REGISTRY UPDATED. Now verify downstream documents: (1) .dev/03-STRUCTURE.md — do new components require new directories or modules in the project scaffold? (2) .dev/08-ROADMAP.md — do phase scope summaries and completion contracts still match the BOM? Check for phase component count changes and new completion criteria."
}
EOF
  exit 0
fi

# Not a watched file — no action
exit 0
