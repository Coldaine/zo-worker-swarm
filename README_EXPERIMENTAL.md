# Experimental Branch: Hook-Based Parallel Orchestration

This is the experimental branch implementing hook-based internal orchestration for Zo Worker Swarm, inspired by [claude-parallel-workers](https://github.com/Coldaine/claude-parallel-workers).

## Status: Phase 1 Complete

All Phase 1 (Foundation) components have been implemented and tested:

- ✅ Pattern detector for parallelizable prompts
- ✅ Plan generator from natural language
- ✅ Event logger (events.jsonl)
- ✅ Status formatter for live updates
- ✅ Dependency checker for task coordination
- ✅ Orchestrator agent for worker management
- ✅ Worker agent template
- ✅ All 4 Claude Code hooks
- ✅ Integration tests (18 tests passing)

## Quick Start

### 1. Test Pattern Detection

```bash
# Test if a prompt is parallelizable
python3 src/hooks/pattern_detector.py "Test modules A, B, C"
# Exit code 0 = parallelizable

python3 src/hooks/pattern_detector.py "What is Python?"
# Exit code 1 = not parallelizable
```

### 2. Generate Execution Plan

```bash
# Generate plan from prompt
python3 src/hooks/plan_generator.py "Analyze modules A, B, C" > .claude/parallel-state/plan.json

# View generated plan
cat .claude/parallel-state/plan.json
```

### 3. Run Orchestrator

```bash
# Run orchestrator with a plan
python3 src/orchestrator_agent.py .claude/parallel-state

# Output shows:
# - Session ID
# - Batch execution (parallel within batches)
# - Worker progress
# - Success/failure summary
```

### 4. Run Integration Tests

```bash
# Run all tests
python3 tests/test_integration.py

# Should see: "Ran 18 tests in X.XXs - OK"
```

## Architecture

```
User Prompt
    ↓
[UserPromptSubmit Hook] → Detect pattern → Generate plan.json
    ↓
[Orchestrator Agent] → Spawn workers in parallel
    ↓                      ↓
  Worker 1              Worker 2         Worker 3
    ↓                      ↓                 ↓
  events.jsonl ←────────────────────────────┘
    ↓
[PostToolUse Hook] → Inject status updates
    ↓
[PreToolUse Hook] → Validate dependencies
    ↓
[Stop Hook] → Verify completion
```

## Components

### Hooks (.claude/hooks/)

1. **user-prompt-submit.sh** - Detects parallelizable patterns, generates plan
2. **post-tool-use.sh** - Injects worker status into session context
3. **pre-tool-use.sh** - Validates dependencies before tool execution
4. **stop.sh** - Verifies completion before session termination

### Core Modules (src/)

1. **hooks/pattern_detector.py** - Detect parallelizable patterns in prompts
2. **hooks/plan_generator.py** - Generate execution plans from prompts
3. **hooks/status_formatter.py** - Format worker status for display
4. **hooks/dependency_checker.py** - Check task dependencies
5. **event_logger.py** - Thread-safe event logging to events.jsonl
6. **orchestrator_agent.py** - Coordinate parallel worker execution
7. **worker_agent.py** - Worker template for task execution

### Shared State (.claude/parallel-state/)

- **plan.json** - Task definitions and dependencies
- **events.jsonl** - Append-only event log for coordination
- **artifacts/** - Worker output files

## Test Results

All 18 integration tests passing:

```
Pattern Detection:
✅ Test patterns (test all files, run tests)
✅ Analyze patterns (analyze modules, check files)
✅ Parallel keywords (in parallel, concurrently)
✅ Exclusions (questions, explanations)

Plan Generation:
✅ From module lists (A, B, C)
✅ From file lists (file1.py, file2.py)
✅ From quarters (Q1, Q2, Q3)

Event Logging:
✅ Emit events (start, progress, artifact, done)
✅ Filter by worker ID

Status Formatting:
✅ Waiting status (no events)
✅ Running status (with progress)
✅ Done status (completed)

Dependency Checking:
✅ Dependencies not satisfied (initial state)
✅ Dependencies satisfied (after completion)
✅ Get ready tasks

Orchestrator:
✅ Load plan
✅ Organize batches
✅ Execute full orchestration (3 workers, 100% success)
```

## Supported Patterns

The pattern detector recognizes these parallelizable patterns:

### Test Patterns
- "Test all Python files"
- "Run tests on each module"
- "Test modules A, B, C"

### Analysis Patterns
- "Analyze files X, Y, Z"
- "Analyze all components"
- "Review each module"

### Processing Patterns
- "Process files in parallel"
- "Run concurrently"
- "Process all files"

### Generation Patterns
- "Generate reports for Q1, Q2, Q3"
- "Create docs for modules A, B"

### Explicit Patterns
- Any prompt containing "parallel", "concurrently", or "simultaneously"

## Example Usage

### Example 1: Test Multiple Modules

```bash
# Generate plan
python3 src/hooks/plan_generator.py "Test modules A, B, C" > .claude/parallel-state/plan.json

# Run orchestrator
python3 src/orchestrator_agent.py

# Output:
# Session ID: S1a2b3c4d
# Total Tasks: 4 (3 workers + 1 merge)
# Batch 1: w1, w2, w3 (parallel)
# Batch 2: w4 (merge, after w1-w3 complete)
```

### Example 2: Analyze Files

```bash
# Generate plan
python3 src/hooks/plan_generator.py "Analyze main.py, utils.py, config.py" > .claude/parallel-state/plan.json

# Check plan
cat .claude/parallel-state/plan.json

# {
#   "session_id": "S...",
#   "work_type": "analyze",
#   "tasks": [
#     {"id": "w1", "target": "main.py", ...},
#     {"id": "w2", "target": "utils.py", ...},
#     {"id": "w3", "target": "config.py", ...},
#     {"id": "w4", "name": "Merge Results", "dependencies": ["w1", "w2", "w3"]}
#   ]
# }
```

### Example 3: Monitor Progress

```bash
# In one terminal, run orchestrator
python3 src/orchestrator_agent.py &

# In another terminal, watch events
tail -f .claude/parallel-state/events.jsonl

# See events stream in real-time:
# {"worker_id": "w1", "type": "start", ...}
# {"worker_id": "w1", "type": "progress", "percent": 25, ...}
# {"worker_id": "w2", "type": "start", ...}
# {"worker_id": "w1", "type": "progress", "percent": 50, ...}
# ...
```

### Example 4: Check Status

```bash
# Get formatted status
python3 src/hooks/status_formatter.py .claude/parallel-state/events.jsonl .claude/parallel-state/plan.json

# Output: w1 75% | w2 done | w3 waiting | w4 waiting
```

## Next Steps

### Phase 2: Hook Integration (Week 2)
- [ ] Test hooks with Claude Code CLI
- [ ] Validate pattern detection with real prompts
- [ ] Verify status injection works in live session
- [ ] Test dependency validation in practice

### Phase 3: Testing & Refinement (Week 3)
- [ ] Test with complex real-world tasks
- [ ] Benchmark performance vs external orchestration
- [ ] Handle edge cases and failures
- [ ] Optimize event log performance

### Phase 4: Evaluation (Week 4)
- [ ] Compare with main branch approach
- [ ] Gather user feedback
- [ ] Document learnings
- [ ] Decide on merge or continuation

## Known Limitations

1. **No actual Claude Code Task tool integration yet** - Currently simulates worker execution
2. **Simplified dependency resolution** - Only supports simple linear dependencies
3. **No retry logic** - Workers fail permanently on errors
4. **No rate limiting** - All workers spawn immediately
5. **Limited error recovery** - Partial failures don't recover

These will be addressed in later phases.

## Comparison with Main Branch

| Feature | Main (External) | Experimental (Hooks) |
|---------|----------------|---------------------|
| Task Definition | YAML files | Natural language |
| Orchestration | External Python | Internal hooks |
| Worker Spawning | CCR instances | Task tool agents |
| Status Updates | Post-execution | Real-time |
| Setup Complexity | High | Medium |
| User Interface | CLI | Conversational |
| **Tests Passing** | ✅ Existing | ✅ 18/18 |

## Documentation

- [BRANCH_STRATEGY.md](BRANCH_STRATEGY.md) - Overall dual-branch strategy
- [EXPERIMENTAL_IMPLEMENTATION.md](EXPERIMENTAL_IMPLEMENTATION.md) - Complete implementation guide
- [FEATURES.md](FEATURES.md) - Main branch feature enumeration

## Contributing

This is an experimental branch. To contribute:

1. Ensure all tests pass: `python3 tests/test_integration.py`
2. Add tests for new functionality
3. Update documentation
4. Submit PR with clear description

## License

MIT License - Same as main branch

---

**Branch Created:** 2025-11-14
**Status:** Phase 1 Complete ✅
**Tests:** 18/18 Passing ✅
**Next Phase:** Hook Integration (Week 2)
