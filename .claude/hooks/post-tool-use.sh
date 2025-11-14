#!/bin/bash
# Post Tool Use Hook
# Inject worker status updates into context after each tool use

STATE_DIR=".claude/parallel-state"
EVENTS_LOG="$STATE_DIR/events.jsonl"
PLAN_FILE="$STATE_DIR/plan.json"

# Check if parallel execution is active
if [ ! -f "$PLAN_FILE" ]; then
    exit 0  # No active parallel work
fi

# Get status summary using Python helper
STATUS=$(python3 src/hooks/status_formatter.py "$EVENTS_LOG" "$PLAN_FILE" 2>/dev/null)

if [ -n "$STATUS" ]; then
    # Inject status into context
    cat <<EOF

---
**Parallel Workers Status:** $STATUS
---
EOF
fi

exit 0
