# Experimental Branch: Hook-Based Parallel Orchestration

## Implementation Guide for `experimental/hook-based-orchestration`

This document provides a detailed implementation guide for building hook-based internal orchestration within Claude Code, inspired by the architecture proposed in [claude-parallel-workers](https://github.com/Coldaine/claude-parallel-workers).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Hook Implementation](#hook-implementation)
4. [Orchestrator Implementation](#orchestrator-implementation)
5. [Worker Implementation](#worker-implementation)
6. [Shared State System](#shared-state-system)
7. [Integration Testing](#integration-testing)
8. [Performance Benchmarks](#performance-benchmarks)

---

## Architecture Overview

### Execution Flow

```
User Prompt
    │
    ▼
[UserPromptSubmit Hook]
    ├─> Detect parallelizable pattern?
    │   ├─> Yes: Generate plan.json
    │   │   └─> Spawn Orchestrator (via Task tool)
    │   └─> No: Pass through unchanged
    │
    ▼
Main Session (continues normally)
    │
    ├──[PostToolUse Hook] ──> Read events.jsonl
    │                         └─> Inject status: "W1 80%; W2 done; W3 waiting"
    │
    ├──[PreToolUse Hook] ───> Check dependencies
    │                         └─> Block if artifacts not ready
    │
    └──[Stop Hook] ──────────> Verify all workers complete
                              └─> Wait or warn

Parallel Execution:
    Orchestrator
        ├─> Worker 1 (Task tool)
        ├─> Worker 2 (Task tool)  } Run concurrently
        └─> Worker 3 (Task tool)
            │
            └─> Write to events.jsonl
                └─> Save artifacts to artifacts/
```

### Key Design Principles

1. **Non-Intrusive**: Main session continues normally with minimal overhead
2. **Event-Driven**: All coordination via append-only event log
3. **Dependency-Aware**: PreToolUse hook enforces execution order
4. **Graceful**: Stop hook ensures clean termination
5. **Transparent**: Status updates injected into conversation context

---

## Directory Structure

```
zo-worker-swarm/
├── .claude/
│   ├── hooks/
│   │   ├── user-prompt-submit.sh       # Pattern detection & orchestrator spawn
│   │   ├── post-tool-use.sh            # Status injection
│   │   ├── pre-tool-use.sh             # Dependency validation
│   │   └── stop.sh                     # Completion verification
│   │
│   └── parallel-state/                 # Created at runtime
│       ├── events.jsonl                # Append-only event log
│       ├── plan.json                   # Task definitions
│       └── artifacts/                  # Worker outputs
│           ├── w1_result.json
│           ├── w2_result.json
│           └── w3_result.json
│
├── src/
│   ├── hooks/                          # Hook helper scripts
│   │   ├── pattern_detector.py         # Detect parallelizable patterns
│   │   ├── plan_generator.py           # Generate plan.json
│   │   ├── status_formatter.py         # Format status messages
│   │   └── dependency_checker.py       # Check task dependencies
│   │
│   ├── orchestrator_agent.py           # Orchestrator implementation
│   ├── worker_agent.py                 # Worker template
│   └── event_logger.py                 # Event log utilities
│
└── tests/
    ├── test_hooks.py                   # Hook unit tests
    ├── test_orchestrator.py            # Orchestrator tests
    └── test_integration.py             # End-to-end tests
```

---

## Hook Implementation

### 1. UserPromptSubmit Hook

**File:** `.claude/hooks/user-prompt-submit.sh`

**Purpose:** Detect parallelizable patterns and spawn orchestrator

#### Detectable Patterns

| User Prompt | Detection Pattern | Generated Tasks |
|-------------|-------------------|-----------------|
| "Test all Python files" | `test.*(all\|each).*files` | One worker per file |
| "Analyze modules A, B, C" | `analyze.*modules?\s+([A-Z],?\s*)+` | One worker per module |
| "Generate reports for Q1, Q2, Q3" | `generate.*reports?.*for.*` | One worker per period |
| "Process files in parallel" | `parallel.*process.*files?` | One worker per file |
| "Review PRs 123, 456, 789" | `review.*PRs?\s+(\d+,?\s*)+` | One worker per PR |

#### Implementation

```bash
#!/bin/bash
# .claude/hooks/user-prompt-submit.sh

# Get user prompt from stdin
USER_PROMPT=$(cat)

# Create state directory if needed
mkdir -p .claude/parallel-state/artifacts

# Check if parallelizable using Python helper
if python3 src/hooks/pattern_detector.py "$USER_PROMPT"; then
    # Generate plan.json
    python3 src/hooks/plan_generator.py "$USER_PROMPT" > .claude/parallel-state/plan.json

    # Generate modified prompt that includes orchestrator spawn
    cat <<EOF
$USER_PROMPT

[System: Parallelizable work detected. Spawning orchestrator...]

I'll handle this request using parallel workers. Let me start the orchestrator to coordinate the tasks.
EOF

    # Return exit code 0 to indicate we modified the prompt
    exit 0
else
    # Not parallelizable, pass through unchanged
    echo "$USER_PROMPT"
    exit 0
fi
```

#### Pattern Detector

**File:** `src/hooks/pattern_detector.py`

```python
#!/usr/bin/env python3
"""
Detect parallelizable patterns in user prompts
"""
import re
import sys

PATTERNS = [
    # Test patterns
    r'test.*(all|each).*(files?|modules?|components?)',
    r'run tests? (on|for|in) (all|each|multiple)',

    # Analysis patterns
    r'analyze.*(files?|modules?|components?).*[A-Z],',
    r'analyze (all|each|multiple)',

    # Processing patterns
    r'process.*(in parallel|concurrently|simultaneously)',
    r'(parallel|concurrent).*(process|execution|run)',

    # Generation patterns
    r'generate.*(reports?|docs?|summaries?).*(for|from) (\w+,\s*)+',

    # Review patterns
    r'review.*(PRs?|pull requests?).*\d+',
    r'check.*(all|each|multiple).*(files?|modules?)',
]

def is_parallelizable(prompt: str) -> bool:
    """Check if prompt matches parallelizable patterns"""
    prompt_lower = prompt.lower()

    for pattern in PATTERNS:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            return True

    return False

def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    prompt = sys.argv[1]
    if is_parallelizable(prompt):
        sys.exit(0)  # True
    else:
        sys.exit(1)  # False

if __name__ == "__main__":
    main()
```

#### Plan Generator

**File:** `src/hooks/plan_generator.py`

```python
#!/usr/bin/env python3
"""
Generate plan.json from user prompt
"""
import json
import re
import sys
import uuid

def extract_targets(prompt: str) -> list:
    """Extract items to process from prompt"""

    # Pattern 1: "modules A, B, C"
    module_match = re.search(r'modules?\s+([A-Z](?:,\s*[A-Z])*)', prompt, re.IGNORECASE)
    if module_match:
        return module_match.group(1).split(',')

    # Pattern 2: "files file1.py, file2.py"
    file_match = re.findall(r'\b(\w+\.(?:py|js|ts|java|go))\b', prompt)
    if file_match:
        return file_match

    # Pattern 3: "PRs 123, 456, 789"
    pr_match = re.findall(r'\b(\d+)\b', prompt)
    if pr_match:
        return [f"PR-{pr}" for pr in pr_match]

    # Pattern 4: "Q1, Q2, Q3"
    quarter_match = re.findall(r'\b(Q[1-4])\b', prompt, re.IGNORECASE)
    if quarter_match:
        return quarter_match

    # Default: no specific targets found
    return []

def generate_plan(prompt: str) -> dict:
    """Generate execution plan from prompt"""

    session_id = f"S{uuid.uuid4().hex[:8]}"
    targets = extract_targets(prompt)

    # Determine task type from prompt
    if re.search(r'test', prompt, re.IGNORECASE):
        task_type = "test"
        action = "Test"
    elif re.search(r'analyze', prompt, re.IGNORECASE):
        task_type = "analyze"
        action = "Analyze"
    elif re.search(r'review', prompt, re.IGNORECASE):
        task_type = "review"
        action = "Review"
    elif re.search(r'generate', prompt, re.IGNORECASE):
        task_type = "generate"
        action = "Generate"
    else:
        task_type = "process"
        action = "Process"

    # Create worker tasks
    tasks = []
    for i, target in enumerate(targets, 1):
        task = {
            "id": f"w{i}",
            "name": f"{action} {target}",
            "prompt": f"{action} {target}: {prompt}",
            "target": target.strip(),
            "dependencies": [],
            "status": "pending"
        }
        tasks.append(task)

    # Add merge task if multiple workers
    if len(tasks) > 1:
        tasks.append({
            "id": f"w{len(tasks) + 1}",
            "name": f"Merge Results",
            "prompt": f"Merge and summarize results from all workers",
            "dependencies": [f"w{i}" for i in range(1, len(tasks) + 1)],
            "status": "pending"
        })

    plan = {
        "session_id": session_id,
        "prompt": prompt,
        "task_type": task_type,
        "created_at": "{{ timestamp }}",
        "tasks": tasks
    }

    return plan

def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    prompt = sys.argv[1]
    plan = generate_plan(prompt)
    print(json.dumps(plan, indent=2))

if __name__ == "__main__":
    main()
```

---

### 2. PostToolUse Hook

**File:** `.claude/hooks/post-tool-use.sh`

**Purpose:** Inject worker status updates into context after each tool use

#### Implementation

```bash
#!/bin/bash
# .claude/hooks/post-tool-use.sh

STATE_DIR=".claude/parallel-state"
EVENTS_LOG="$STATE_DIR/events.jsonl"

# Check if parallel execution is active
if [ ! -f "$STATE_DIR/plan.json" ]; then
    exit 0  # No active parallel work
fi

# Get status summary using Python helper
STATUS=$(python3 src/hooks/status_formatter.py "$EVENTS_LOG" "$STATE_DIR/plan.json")

if [ -n "$STATUS" ]; then
    # Inject status into context
    cat <<EOF

---
**Parallel Workers Status:** $STATUS
---
EOF
fi

exit 0
```

#### Status Formatter

**File:** `src/hooks/status_formatter.py`

```python
#!/usr/bin/env python3
"""
Format worker status from events.jsonl
"""
import json
import sys
from pathlib import Path

def get_latest_status(events_path: str, plan_path: str) -> str:
    """Get formatted status of all workers"""

    # Load plan
    with open(plan_path) as f:
        plan = json.load(f)

    # Load events
    events = []
    if Path(events_path).exists():
        with open(events_path) as f:
            for line in f:
                events.append(json.loads(line))

    # Build status map
    status_map = {}
    for event in events:
        worker_id = event.get("worker_id")
        event_type = event.get("type")

        if event_type == "start":
            status_map[worker_id] = "⏳ running"
        elif event_type == "progress":
            percent = event.get("percent", 0)
            status_map[worker_id] = f"⏳ {percent}%"
        elif event_type == "done":
            status_map[worker_id] = "✓ done"
        elif event_type == "error":
            status_map[worker_id] = "✗ error"

    # Format status message
    parts = []
    for task in plan["tasks"]:
        task_id = task["id"]
        status = status_map.get(task_id, "⏸ waiting")
        parts.append(f"{task_id} {status}")

    return " | ".join(parts)

def main():
    if len(sys.argv) < 3:
        sys.exit(0)

    events_path = sys.argv[1]
    plan_path = sys.argv[2]

    status = get_latest_status(events_path, plan_path)
    print(status)

if __name__ == "__main__":
    main()
```

---

### 3. PreToolUse Hook

**File:** `.claude/hooks/pre-tool-use.sh`

**Purpose:** Validate dependencies before tool execution

#### Implementation

```bash
#!/bin/bash
# .claude/hooks/pre-tool-use.sh

# Get tool name and arguments
TOOL_NAME="$1"
TOOL_ARGS="$2"

STATE_DIR=".claude/parallel-state"

# Only check dependencies if parallel work is active
if [ ! -f "$STATE_DIR/plan.json" ]; then
    exit 0  # Allow tool to proceed
fi

# Check if this tool requires merged artifacts
# (e.g., Read, Edit, Write tools operating on merged results)
if [[ "$TOOL_ARGS" == *"artifacts/merged"* ]] || \
   [[ "$TOOL_ARGS" == *"final_result"* ]]; then

    # Check if merge task is complete
    if python3 src/hooks/dependency_checker.py "$STATE_DIR/events.jsonl" "$STATE_DIR/plan.json"; then
        exit 0  # Dependencies satisfied, allow tool
    else
        # Block tool execution
        cat <<EOF
⚠️ Dependencies not satisfied. Waiting for workers to complete...

Current status:
$(python3 src/hooks/status_formatter.py "$STATE_DIR/events.jsonl" "$STATE_DIR/plan.json")
EOF
        exit 1  # Block tool
    fi
fi

exit 0  # Allow tool by default
```

#### Dependency Checker

**File:** `src/hooks/dependency_checker.py`

```python
#!/usr/bin/env python3
"""
Check if task dependencies are satisfied
"""
import json
import sys
from pathlib import Path

def check_dependencies(events_path: str, plan_path: str) -> bool:
    """Check if all merge task dependencies are complete"""

    # Load plan
    with open(plan_path) as f:
        plan = json.load(f)

    # Find merge task
    merge_task = None
    for task in plan["tasks"]:
        if task.get("dependencies"):
            merge_task = task
            break

    if not merge_task:
        return True  # No merge task, all done

    # Load events
    completed = set()
    if Path(events_path).exists():
        with open(events_path) as f:
            for line in f:
                event = json.loads(line)
                if event.get("type") == "done":
                    completed.add(event.get("worker_id"))

    # Check if all dependencies are complete
    dependencies = merge_task.get("dependencies", [])
    return all(dep in completed for dep in dependencies)

def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    events_path = sys.argv[1]
    plan_path = sys.argv[2]

    if check_dependencies(events_path, plan_path):
        sys.exit(0)  # Dependencies satisfied
    else:
        sys.exit(1)  # Dependencies not satisfied

if __name__ == "__main__":
    main()
```

---

### 4. Stop Hook

**File:** `.claude/hooks/stop.sh`

**Purpose:** Verify all workers complete before session termination

#### Implementation

```bash
#!/bin/bash
# .claude/hooks/stop.sh

STATE_DIR=".claude/parallel-state"

# Check if parallel work is active
if [ ! -f "$STATE_DIR/plan.json" ]; then
    exit 0  # No parallel work, allow stop
fi

# Check if all workers are complete
if python3 src/hooks/completion_checker.py "$STATE_DIR/events.jsonl" "$STATE_DIR/plan.json"; then
    # All complete, clean up
    echo "✓ All parallel workers completed successfully"

    # Optionally archive results
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    mkdir -p .claude/parallel-state/archive
    tar -czf ".claude/parallel-state/archive/session_${TIMESTAMP}.tar.gz" \
        "$STATE_DIR/events.jsonl" \
        "$STATE_DIR/plan.json" \
        "$STATE_DIR/artifacts/"

    # Clean up for next run
    rm -rf "$STATE_DIR/events.jsonl" "$STATE_DIR/plan.json" "$STATE_DIR/artifacts"

    exit 0  # Allow stop
else
    # Workers still running
    cat <<EOF
⚠️ Warning: Parallel workers still running!

Status:
$(python3 src/hooks/status_formatter.py "$STATE_DIR/events.jsonl" "$STATE_DIR/plan.json")

Options:
1. Wait for completion (recommended)
2. Force stop (may lose work)

EOF
    exit 1  # Block stop (or exit 0 to allow with warning)
fi
```

#### Completion Checker

**File:** `src/hooks/completion_checker.py`

```python
#!/usr/bin/env python3
"""
Check if all workers have completed
"""
import json
import sys
from pathlib import Path

def all_complete(events_path: str, plan_path: str) -> bool:
    """Check if all tasks are complete"""

    # Load plan
    with open(plan_path) as f:
        plan = json.load(f)

    # Get all task IDs
    all_tasks = {task["id"] for task in plan["tasks"]}

    # Load events and find completed tasks
    completed = set()
    if Path(events_path).exists():
        with open(events_path) as f:
            for line in f:
                event = json.loads(line)
                if event.get("type") == "done":
                    completed.add(event.get("worker_id"))

    return all_tasks == completed

def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    events_path = sys.argv[1]
    plan_path = sys.argv[2]

    if all_complete(events_path, plan_path):
        sys.exit(0)  # Complete
    else:
        sys.exit(1)  # Incomplete

if __name__ == "__main__":
    main()
```

---

## Orchestrator Implementation

**File:** `src/orchestrator_agent.py`

**Purpose:** Spawn and coordinate parallel workers

### Implementation

```python
#!/usr/bin/env python3
"""
Orchestrator Agent for Hook-Based Parallel Execution

Spawned by UserPromptSubmit hook to coordinate parallel workers.
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class Orchestrator:
    """Coordinate parallel worker execution"""

    def __init__(self, state_dir: str = ".claude/parallel-state"):
        self.state_dir = Path(state_dir)
        self.plan_path = self.state_dir / "plan.json"
        self.events_path = self.state_dir / "events.jsonl"
        self.artifacts_dir = self.state_dir / "artifacts"

        # Ensure directories exist
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def load_plan(self) -> dict:
        """Load execution plan"""
        with open(self.plan_path) as f:
            return json.load(f)

    def emit_event(self, event: dict):
        """Write event to log"""
        event["timestamp"] = datetime.utcnow().isoformat() + "Z"
        with open(self.events_path, "a") as f:
            f.write(json.dumps(event) + "\n")

    async def spawn_worker(self, task: dict) -> dict:
        """Spawn a single worker via Task tool"""
        task_id = task["id"]
        task_prompt = task["prompt"]

        self.emit_event({
            "worker_id": task_id,
            "type": "start",
            "task": task["name"]
        })

        try:
            # In actual implementation, this would use Claude Code's Task tool
            # For now, simulate with subprocess or direct function call
            result = await self._execute_worker(task_id, task_prompt)

            # Save artifact
            artifact_path = self.artifacts_dir / f"{task_id}_result.json"
            with open(artifact_path, "w") as f:
                json.dump(result, f, indent=2)

            self.emit_event({
                "worker_id": task_id,
                "type": "artifact",
                "path": str(artifact_path)
            })

            self.emit_event({
                "worker_id": task_id,
                "type": "done",
                "status": "success"
            })

            return {"task_id": task_id, "status": "success", "result": result}

        except Exception as e:
            self.emit_event({
                "worker_id": task_id,
                "type": "error",
                "message": str(e)
            })
            return {"task_id": task_id, "status": "error", "error": str(e)}

    async def _execute_worker(self, task_id: str, prompt: str) -> dict:
        """Execute worker logic (placeholder)"""
        # In production, this would invoke:
        # - Claude Code Task tool with the prompt
        # - Worker would execute independently
        # - Return result when complete

        # Simulate work with progress updates
        for progress in [25, 50, 75, 100]:
            await asyncio.sleep(1)
            self.emit_event({
                "worker_id": task_id,
                "type": "progress",
                "percent": progress
            })

        return {
            "task_id": task_id,
            "output": f"Result from {task_id}",
            "success": True
        }

    async def run(self):
        """Execute orchestration"""
        plan = self.load_plan()

        print(f"Orchestrator started for session {plan['session_id']}")
        print(f"Tasks: {len(plan['tasks'])}")

        # Separate tasks by dependency
        independent_tasks = [t for t in plan["tasks"] if not t.get("dependencies")]
        merge_tasks = [t for t in plan["tasks"] if t.get("dependencies")]

        # Execute independent tasks in parallel
        print(f"\nSpawning {len(independent_tasks)} workers...")
        worker_results = await asyncio.gather(*[
            self.spawn_worker(task) for task in independent_tasks
        ])

        # Execute merge tasks sequentially
        for merge_task in merge_tasks:
            print(f"\nExecuting merge task: {merge_task['name']}")
            await self.spawn_worker(merge_task)

        print("\n✓ All tasks complete")

async def main():
    """Entry point"""
    orchestrator = Orchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Worker Implementation

**File:** `src/worker_agent.py`

**Purpose:** Template for worker agents spawned by orchestrator

### Implementation

```python
#!/usr/bin/env python3
"""
Worker Agent Template

Each worker is an independent Claude Code Task agent that:
1. Executes assigned task
2. Emits progress events
3. Saves results to artifacts
"""
import json
import sys
from datetime import datetime
from pathlib import Path

class Worker:
    """Worker agent for parallel task execution"""

    def __init__(self, task_id: str, prompt: str, state_dir: str = ".claude/parallel-state"):
        self.task_id = task_id
        self.prompt = prompt
        self.state_dir = Path(state_dir)
        self.events_path = self.state_dir / "events.jsonl"
        self.artifacts_dir = self.state_dir / "artifacts"

    def emit_event(self, event: dict):
        """Write event to shared log"""
        event["timestamp"] = datetime.utcnow().isoformat() + "Z"
        event["worker_id"] = self.task_id

        with open(self.events_path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def save_artifact(self, result: dict):
        """Save result to artifacts directory"""
        artifact_path = self.artifacts_dir / f"{self.task_id}_result.json"
        with open(artifact_path, "w") as f:
            json.dump(result, f, indent=2)

        self.emit_event({
            "type": "artifact",
            "path": str(artifact_path)
        })

    def execute(self) -> dict:
        """Execute task logic"""
        self.emit_event({"type": "start", "task": self.prompt})

        try:
            # Simulate work with progress updates
            for progress in [25, 50, 75, 100]:
                self.emit_event({"type": "progress", "percent": progress})
                # Do actual work here

            # Generate result
            result = {
                "task_id": self.task_id,
                "prompt": self.prompt,
                "output": f"Completed: {self.prompt}",
                "success": True
            }

            # Save result
            self.save_artifact(result)

            # Mark complete
            self.emit_event({"type": "done", "status": "success"})

            return result

        except Exception as e:
            self.emit_event({"type": "error", "message": str(e)})
            raise

def main():
    """Entry point"""
    if len(sys.argv) < 3:
        print("Usage: worker_agent.py <task_id> <prompt>")
        sys.exit(1)

    task_id = sys.argv[1]
    prompt = sys.argv[2]

    worker = Worker(task_id, prompt)
    result = worker.execute()

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
```

---

## Shared State System

### events.jsonl Format

Append-only log of all worker events:

```jsonl
{"timestamp": "2025-11-14T10:00:00Z", "worker_id": "w1", "type": "start", "task": "Analyze Module A"}
{"timestamp": "2025-11-14T10:00:15Z", "worker_id": "w1", "type": "progress", "percent": 25}
{"timestamp": "2025-11-14T10:00:30Z", "worker_id": "w1", "type": "progress", "percent": 50}
{"timestamp": "2025-11-14T10:00:45Z", "worker_id": "w1", "type": "progress", "percent": 75}
{"timestamp": "2025-11-14T10:01:00Z", "worker_id": "w1", "type": "progress", "percent": 100}
{"timestamp": "2025-11-14T10:01:05Z", "worker_id": "w1", "type": "artifact", "path": ".claude/parallel-state/artifacts/w1_result.json"}
{"timestamp": "2025-11-14T10:01:10Z", "worker_id": "w1", "type": "done", "status": "success"}
```

### plan.json Format

Task definitions and dependencies:

```json
{
  "session_id": "S1a2b3c4d",
  "prompt": "Analyze modules A, B, C for code quality",
  "task_type": "analyze",
  "created_at": "2025-11-14T10:00:00Z",
  "tasks": [
    {
      "id": "w1",
      "name": "Analyze Module A",
      "prompt": "Analyze module A for code quality",
      "target": "Module A",
      "dependencies": [],
      "status": "pending"
    },
    {
      "id": "w2",
      "name": "Analyze Module B",
      "prompt": "Analyze module B for code quality",
      "target": "Module B",
      "dependencies": [],
      "status": "pending"
    },
    {
      "id": "w3",
      "name": "Analyze Module C",
      "prompt": "Analyze module C for code quality",
      "target": "Module C",
      "dependencies": [],
      "status": "pending"
    },
    {
      "id": "w4",
      "name": "Merge Results",
      "prompt": "Merge and summarize analysis from all modules",
      "dependencies": ["w1", "w2", "w3"],
      "status": "pending"
    }
  ]
}
```

### Artifact Files

Each worker saves results to artifacts directory:

**w1_result.json:**
```json
{
  "task_id": "w1",
  "prompt": "Analyze module A for code quality",
  "output": {
    "module": "A",
    "quality_score": 8.5,
    "issues": ["Missing docstrings", "Complex function"],
    "recommendations": ["Add type hints", "Refactor large function"]
  },
  "success": true,
  "duration": 45.2
}
```

---

## Integration Testing

**File:** `tests/test_integration.py`

```python
#!/usr/bin/env python3
"""
Integration tests for hook-based orchestration
"""
import asyncio
import json
import pytest
import tempfile
from pathlib import Path

from src.orchestrator_agent import Orchestrator
from src.hooks.pattern_detector import is_parallelizable
from src.hooks.plan_generator import generate_plan

@pytest.fixture
def temp_state_dir():
    """Create temporary state directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir) / ".claude" / "parallel-state"
        state_dir.mkdir(parents=True)
        yield state_dir

def test_pattern_detection():
    """Test parallelizable pattern detection"""
    assert is_parallelizable("Test all Python files")
    assert is_parallelizable("Analyze modules A, B, C")
    assert is_parallelizable("Generate reports for Q1, Q2, Q3")
    assert not is_parallelizable("What is the weather today?")

def test_plan_generation():
    """Test plan generation from prompt"""
    prompt = "Analyze modules A, B, C"
    plan = generate_plan(prompt)

    assert plan["task_type"] == "analyze"
    assert len(plan["tasks"]) == 4  # 3 workers + 1 merge
    assert plan["tasks"][0]["target"] == "A"
    assert plan["tasks"][3]["dependencies"] == ["w1", "w2", "w3"]

@pytest.mark.asyncio
async def test_orchestrator_execution(temp_state_dir):
    """Test full orchestrator execution"""
    # Create plan
    plan = generate_plan("Test modules A, B")
    plan_path = temp_state_dir / "plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan, f)

    # Run orchestrator
    orchestrator = Orchestrator(str(temp_state_dir))
    await orchestrator.run()

    # Verify events were logged
    events_path = temp_state_dir / "events.jsonl"
    assert events_path.exists()

    events = []
    with open(events_path) as f:
        for line in f:
            events.append(json.loads(line))

    # Verify all workers started and completed
    start_events = [e for e in events if e["type"] == "start"]
    done_events = [e for e in events if e["type"] == "done"]

    assert len(start_events) == 3  # 2 workers + 1 merge
    assert len(done_events) == 3

    # Verify artifacts were created
    artifacts_dir = temp_state_dir / "artifacts"
    assert (artifacts_dir / "w1_result.json").exists()
    assert (artifacts_dir / "w2_result.json").exists()

def test_dependency_resolution():
    """Test that merge task waits for workers"""
    # This would test the PreToolUse hook's dependency checking
    pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Performance Benchmarks

### Test Scenarios

1. **Simple Parallel (3 workers, no dependencies)**
   - Measure total execution time vs sequential
   - Expected speedup: ~3x

2. **Complex Pipeline (5 workers + merge)**
   - Measure batch execution time
   - Expected speedup: ~3-4x

3. **Large Scale (10+ workers)**
   - Test scalability
   - Measure event log performance
   - Expected speedup: ~5-8x

### Benchmark Script

**File:** `tests/benchmark.py`

```python
#!/usr/bin/env python3
"""
Performance benchmarks for hook-based orchestration
"""
import asyncio
import time
from src.orchestrator_agent import Orchestrator
from src.hooks.plan_generator import generate_plan

async def benchmark_simple_parallel():
    """Benchmark simple parallel execution"""
    prompt = "Analyze modules A, B, C"
    plan = generate_plan(prompt)

    # Save plan
    with open(".claude/parallel-state/plan.json", "w") as f:
        json.dump(plan, f)

    # Time execution
    start = time.time()
    orchestrator = Orchestrator()
    await orchestrator.run()
    duration = time.time() - start

    print(f"Simple Parallel: {duration:.2f}s")
    print(f"Expected sequential: ~{duration * 3:.2f}s")
    print(f"Speedup: ~{3:.1f}x")

async def benchmark_complex_pipeline():
    """Benchmark pipeline with dependencies"""
    # Create plan with 5 workers + merge
    # Measure execution time
    pass

if __name__ == "__main__":
    asyncio.run(benchmark_simple_parallel())
```

---

## Next Steps

### Phase 1: Foundation (Week 1)
- [ ] Create `.claude/hooks/` directory structure
- [ ] Implement pattern detector and plan generator
- [ ] Build basic orchestrator agent
- [ ] Create worker template

### Phase 2: Hook Integration (Week 2)
- [ ] Implement all 4 hooks (UserPromptSubmit, PostToolUse, PreToolUse, Stop)
- [ ] Test pattern detection with real prompts
- [ ] Verify status injection works correctly
- [ ] Test dependency validation

### Phase 3: Testing (Week 3)
- [ ] Write unit tests for all components
- [ ] Create integration tests
- [ ] Run performance benchmarks
- [ ] Test failure scenarios

### Phase 4: Evaluation (Week 4)
- [ ] Compare performance vs external orchestration
- [ ] Evaluate user experience
- [ ] Assess maintenance complexity
- [ ] Document findings and recommendations

---

## Success Criteria

- ✅ Pattern detection accuracy > 90%
- ✅ Successfully spawn and coordinate 3+ workers
- ✅ Dependency resolution works correctly
- ✅ Status updates appear in main session
- ✅ Graceful handling of worker failures
- ✅ Performance comparable to external orchestration
- ✅ User can trigger parallel work via natural language

---

## Conclusion

This implementation guide provides a complete blueprint for hook-based parallel orchestration within Claude Code. The modular design separates concerns:

- **Hooks**: Detect patterns, inject status, validate dependencies
- **Orchestrator**: Spawn and coordinate workers
- **Workers**: Execute tasks independently
- **Shared State**: Coordinate via event log

The system is designed to be:
- **Non-intrusive**: Main session continues normally
- **Transparent**: User sees live status updates
- **Reliable**: Dependency validation prevents errors
- **Scalable**: Event-driven coordination scales well

Next: Begin Phase 1 implementation and test with simple use cases.
