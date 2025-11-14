#!/bin/bash
# Stop Hook
# Verify all workers complete before session termination

STATE_DIR=".claude/parallel-state"
EVENTS_LOG="$STATE_DIR/events.jsonl"
PLAN_FILE="$STATE_DIR/plan.json"

# Check if parallel work is active
if [ ! -f "$PLAN_FILE" ]; then
    exit 0  # No parallel work, allow stop
fi

# Helper script to check completion
check_completion() {
    python3 - <<EOF
import json
import sys
from pathlib import Path

def all_complete(events_path, plan_path):
    # Load plan
    with open(plan_path) as f:
        plan = json.load(f)

    all_tasks = {task["id"] for task in plan["tasks"]}

    # Load events
    completed = set()
    if Path(events_path).exists():
        with open(events_path) as f:
            for line in f:
                event = json.loads(line.strip())
                if event.get("type") == "done":
                    completed.add(event.get("worker_id"))

    return all_tasks == completed

if all_complete("$EVENTS_LOG", "$PLAN_FILE"):
    sys.exit(0)
else:
    sys.exit(1)
EOF
}

if check_completion; then
    # All complete, clean up
    echo "✓ All parallel workers completed successfully" >&2

    # Archive results
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    ARCHIVE_DIR="$STATE_DIR/archive"
    mkdir -p "$ARCHIVE_DIR"

    # Archive the session
    tar -czf "$ARCHIVE_DIR/session_${TIMESTAMP}.tar.gz" \
        "$EVENTS_LOG" \
        "$PLAN_FILE" \
        "$STATE_DIR/artifacts/" 2>/dev/null

    echo "Archived session to: $ARCHIVE_DIR/session_${TIMESTAMP}.tar.gz" >&2

    # Clean up for next run
    rm -f "$EVENTS_LOG" "$PLAN_FILE"
    rm -rf "$STATE_DIR/artifacts"

    exit 0  # Allow stop
else
    # Workers still running
    echo "⚠️  Warning: Parallel workers still running!" >&2
    echo "" >&2

    STATUS=$(python3 src/hooks/status_formatter.py "$EVENTS_LOG" "$PLAN_FILE" 2>/dev/null)
    echo "Status: $STATUS" >&2
    echo "" >&2
    echo "Recommend waiting for completion or use Ctrl+C to force stop" >&2

    # Allow stop anyway (or exit 1 to block)
    exit 0
fi
