#!/bin/bash
# User Prompt Submit Hook
# Detects parallelizable patterns and spawns orchestrator

# Get user prompt from stdin
USER_PROMPT=$(cat)

# Create state directory if needed
mkdir -p .claude/parallel-state/artifacts

# Check if parallelizable using Python helper
if python3 src/hooks/pattern_detector.py "$USER_PROMPT" 2>/dev/null; then
    echo "[Hook] Parallelizable pattern detected!" >&2

    # Generate plan.json
    python3 src/hooks/plan_generator.py "$USER_PROMPT" > .claude/parallel-state/plan.json 2>/dev/null

    echo "[Hook] Generated execution plan" >&2

    # Output modified prompt that includes orchestrator context
    cat <<EOF
$USER_PROMPT

[System: Parallelizable work detected. The orchestrator will coordinate parallel execution of tasks. You'll see status updates as workers progress.]
EOF

    exit 0
else
    # Not parallelizable, pass through unchanged
    echo "$USER_PROMPT"
    exit 0
fi
