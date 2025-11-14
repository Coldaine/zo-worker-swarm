# Branch Strategy: Zo Worker Swarm Evolution

## Executive Summary

This document outlines the strategy for evolving Zo Worker Swarm into two distinct branches:

1. **Main Branch** (`main`): Production-ready external orchestration with full feature enumeration
2. **Experimental Branch** (`experimental/hook-based-orchestration`): Hook-based internal orchestration inspired by claude-parallel-workers

## Architecture Comparison

### Current: Zo Worker Swarm (External Orchestration)
```
Windows Machine                          Zo Machine (via SSH)
┌─────────────────────────┐             ┌──────────────────────┐
│ Python Orchestrator     │             │                      │
│   ┌─────────────────┐   │             │                      │
│   │ CCR #1 (GLM)    │───┼────────────►│  Task Execution      │
│   │ CCR #2 (Grok)   │───┼────────────►│                      │
│   │ CCR #3 (DSR1)   │───┼────────────►│                      │
│   │ CCR #4 (DS)     │───┼────────────►│                      │
│   │ CCR #5 (Claude) │───┼────────────►│                      │
│   └─────────────────┘   │             │                      │
└─────────────────────────┘             └──────────────────────┘
```

**Key Characteristics:**
- Multiple independent Claude Code CLI instances
- External Python orchestrator coordinates execution
- YAML-based task definitions
- Model-specific routing via CCR
- SSH-based remote execution
- Post-execution results aggregation
- No real-time inter-worker communication

### Proposed: Hook-Based Internal Orchestration
```
Claude Code Session
┌────────────────────────────────────────────────────────────┐
│  Main Session                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Hook Layer                                            │ │
│  │  • UserPromptSubmit: Detect parallelizable patterns  │ │
│  │  • PostToolUse: Inject worker status updates         │ │
│  │  • PreToolUse: Validate dependencies                 │ │
│  │  • Stop: Verify completion                           │ │
│  └──────────────────────────────────────────────────────┘ │
│                           │                                │
│                           ▼                                │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Orchestrator (spawned via Task tool)                 │ │
│  │  • Parses plan.json                                  │ │
│  │  • Spawns Worker 1, Worker 2, Worker 3...           │ │
│  │  • Writes events.jsonl (append-only log)             │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │               │
│  │ (Task)   │  │ (Task)   │  │ (Task)   │               │
│  └──────────┘  └──────────┘  └──────────┘               │
│       │              │              │                     │
│       └──────────────┴──────────────┘                     │
│                      │                                     │
│                      ▼                                     │
│            Shared State Store                             │
│            • events.jsonl                                 │
│            • plan.json                                    │
│            • artifacts/*                                  │
└────────────────────────────────────────────────────────────┘
```

**Key Characteristics:**
- Single Claude Code session with spawned workers
- Hook-based lifecycle management
- Natural language task detection
- Real-time status updates in main session context
- Shared state via JSONL event log
- Dependency resolution before tool execution
- Graceful termination with completion verification

## Branch 1: Main Branch Strategy

**Branch Name:** `main`
**Purpose:** Production-ready external orchestration with enhanced functionality

### Goals

1. **Maintain Current Architecture**: Preserve the proven external orchestration model
2. **Complete Feature Implementation**: Fill gaps in current functionality
3. **Enhance Documentation**: Provide comprehensive guides for all features
4. **Production Hardening**: Add error handling, logging, monitoring

### Full Feature Enumeration

#### ✅ Implemented Features

1. **CCR Instance Management**
   - Multi-instance spawning (5 models: GLM-4.6, Grok, DeepSeek-R1, DeepSeek, Claude Sonnet 4)
   - Health monitoring and status checks
   - Port management (3456-3460)
   - Process lifecycle control (start/stop)

2. **YAML Task Definitions**
   - Task name, description, tags
   - CCR instance selection
   - Command execution strings
   - Prompt configuration
   - Timeout specification
   - Dependency declarations

3. **Task Execution**
   - SSH remote execution
   - Dependency-based batching
   - Parallel execution within batches
   - Timeout enforcement

4. **Results Aggregation**
   - Terminal dashboard with Rich formatting
   - JSON export
   - Markdown report generation
   - Success rate tracking

5. **Secrets Management**
   - Bitwarden Secrets Manager integration
   - Automatic API key injection
   - Fallback to environment variables

#### 🚧 Partially Implemented Features

1. **Error Handling & Recovery**
   - Basic timeout handling
   - **Missing**: Retry logic with exponential backoff
   - **Missing**: Partial failure recovery (continue with successful tasks)
   - **Missing**: Detailed error classification (network, timeout, command, model)

2. **Monitoring & Observability**
   - Basic console output
   - **Missing**: Structured logging with levels (DEBUG, INFO, WARN, ERROR)
   - **Missing**: Performance metrics (task duration, queue time, model latency)
   - **Missing**: Real-time progress tracking (percentage completion)

3. **Task Management**
   - Basic dependency handling
   - **Missing**: Conditional task execution (if/then/else)
   - **Missing**: Task retry policies per task
   - **Missing**: Task priorities (high/medium/low)
   - **Missing**: Task cancellation mid-execution

#### ❌ Missing Features

1. **Advanced Orchestration**
   - Dynamic task generation based on results
   - Task result validation and quality checks
   - Multi-stage pipelines (dev → test → prod)
   - Task result caching and reuse
   - Rollback mechanisms for failed workflows

2. **Resource Management**
   - Concurrent task limits (max parallel tasks)
   - Model-specific rate limiting
   - Cost tracking and budgets per workflow
   - Resource quotas (CPU, memory, tokens)

3. **Collaboration & Sharing**
   - Task library/marketplace
   - Workflow templates
   - Team workspaces
   - Shared result repositories

4. **Integration & Extensibility**
   - Webhook notifications (Slack, Discord, email)
   - Custom transformers for input/output
   - Plugin system for custom executors
   - API for external integrations

5. **Testing & Quality**
   - Task dry-run mode (validate without execution)
   - Integration tests for workflows
   - Synthetic test data generation
   - Performance benchmarking suite

### Implementation Roadmap

#### Phase 1: Core Enhancements (Weeks 1-2)
- [ ] Add structured logging with configurable levels
- [ ] Implement retry logic with exponential backoff
- [ ] Add task cancellation support
- [ ] Enhance error classification and reporting
- [ ] Add real-time progress tracking

#### Phase 2: Production Hardening (Weeks 3-4)
- [ ] Add resource limits (max concurrent tasks)
- [ ] Implement cost tracking per workflow
- [ ] Add task dry-run validation mode
- [ ] Create comprehensive integration tests
- [ ] Add performance metrics collection

#### Phase 3: Advanced Features (Weeks 5-6)
- [ ] Implement conditional task execution
- [ ] Add task result caching
- [ ] Create webhook notification system
- [ ] Develop plugin system for custom executors
- [ ] Add workflow templates library

### Success Criteria

- All core features (Phase 1) tested and documented
- Production deployment successful with monitoring
- User documentation complete with examples
- CI/CD pipeline established
- Performance benchmarks meet targets

## Branch 2: Experimental Branch Strategy

**Branch Name:** `experimental/hook-based-orchestration`
**Purpose:** Prototype internal orchestration using Claude Code hooks

### Goals

1. **Proof of Concept**: Validate hook-based orchestration within Claude Code
2. **Natural Language Interface**: Enable task spawning from conversational prompts
3. **Real-Time Coordination**: Implement shared state and event streaming
4. **Evaluate Viability**: Determine if this approach should be merged to main

### Architecture Components

#### 1. Hook System

**Location:** `.claude/hooks/` (requires Claude Code hooks support)

##### UserPromptSubmit Hook
```bash
# .claude/hooks/user-prompt-submit.sh
# Detect parallelizable patterns and spawn orchestrator
```

**Responsibilities:**
- Parse user prompt for parallelizable keywords ("analyze these files", "test all modules")
- Generate `plan.json` with task breakdown
- Spawn orchestrator agent via Task tool
- Return modified prompt with orchestrator context

**Pattern Detection Examples:**
- "Test all Python files" → Parallel file processing
- "Analyze modules A, B, C" → Parallel module analysis
- "Generate reports for Q1, Q2, Q3" → Parallel report generation

##### PostToolUse Hook
```bash
# .claude/hooks/post-tool-use.sh
# Inject worker status updates into context
```

**Responsibilities:**
- Read `events.jsonl` for new events since last check
- Format status summary (e.g., "W1 80% processing; W2 ✓ done; W3 waiting")
- Inject status into context for main session awareness
- Update progress indicators

##### PreToolUse Hook
```bash
# .claude/hooks/pre-tool-use.sh
# Validate dependencies before tool execution
```

**Responsibilities:**
- Check if tool requires merged artifacts
- Verify all dependencies completed via events.jsonl
- Block execution if prerequisites not satisfied
- Rewrite tool inputs with artifact paths

##### Stop Hook
```bash
# .claude/hooks/stop.sh
# Verify completion before session termination
```

**Responsibilities:**
- Check if all workers completed
- Wait for in-progress tasks with timeout
- Clean up temporary files
- Generate final summary

#### 2. Shared State Store

**Location:** `.claude/parallel-state/`

```
.claude/parallel-state/
├── events.jsonl          # Append-only event log
├── plan.json            # Task definitions and dependencies
└── artifacts/           # Worker outputs
    ├── worker_1_result.json
    ├── worker_2_result.json
    └── worker_3_result.json
```

##### events.jsonl Format
```jsonl
{"timestamp": "2025-11-14T10:00:00Z", "worker_id": "w1", "type": "start", "task": "analyze_module_a"}
{"timestamp": "2025-11-14T10:00:30Z", "worker_id": "w1", "type": "progress", "percent": 50, "message": "Processing..."}
{"timestamp": "2025-11-14T10:01:00Z", "worker_id": "w1", "type": "artifact", "path": "artifacts/worker_1_result.json"}
{"timestamp": "2025-11-14T10:01:05Z", "worker_id": "w1", "type": "done", "status": "success"}
```

##### plan.json Format
```json
{
  "session_id": "R42",
  "tasks": [
    {
      "id": "w1",
      "name": "Analyze Module A",
      "prompt": "Analyze module A for code quality",
      "dependencies": [],
      "status": "pending"
    },
    {
      "id": "w2",
      "name": "Analyze Module B",
      "prompt": "Analyze module B for code quality",
      "dependencies": [],
      "status": "pending"
    },
    {
      "id": "w3",
      "name": "Merge Results",
      "prompt": "Merge analysis results from W1 and W2",
      "dependencies": ["w1", "w2"],
      "status": "pending"
    }
  ]
}
```

#### 3. Orchestrator Agent

**Implementation:** Python script spawned via Claude Code Task tool

**Responsibilities:**
1. Read `plan.json` to get task definitions
2. Spawn worker agents in parallel using Task tool
3. Monitor worker progress via `events.jsonl`
4. Write status events to `events.jsonl`
5. Handle worker failures and retries
6. Coordinate artifact collection

**Key Functions:**
```python
def spawn_workers(plan):
    """Spawn parallel workers from plan"""

def monitor_progress():
    """Watch events.jsonl for status updates"""

def handle_failure(worker_id, error):
    """Handle worker failures with retry logic"""

def collect_artifacts():
    """Gather results when all workers complete"""
```

#### 4. Worker Agents

**Implementation:** Claude Code Task agents spawned by orchestrator

**Responsibilities:**
1. Execute assigned task from `plan.json`
2. Emit events to `events.jsonl` (start, progress, artifact, done, error)
3. Save results to `artifacts/` directory
4. Handle errors gracefully with detailed logging

**Worker Lifecycle:**
```python
# Worker W1 example
def worker_main(task_id, task_config):
    emit_event({"type": "start", "worker_id": task_id})

    try:
        for progress in execute_task(task_config):
            emit_event({"type": "progress", "percent": progress})

        result = finalize_task()
        save_artifact(task_id, result)
        emit_event({"type": "artifact", "path": f"artifacts/{task_id}_result.json"})
        emit_event({"type": "done", "status": "success"})

    except Exception as e:
        emit_event({"type": "error", "message": str(e)})
        raise
```

### Implementation Roadmap

#### Phase 1: Foundation (Week 1)
- [ ] Create hook scaffolding (.claude/hooks/)
- [ ] Implement shared state store (events.jsonl, plan.json)
- [ ] Build basic orchestrator agent
- [ ] Create simple worker template

#### Phase 2: Hook Integration (Week 2)
- [ ] Implement UserPromptSubmit pattern detection
- [ ] Build PostToolUse status injection
- [ ] Create PreToolUse dependency validation
- [ ] Add Stop hook completion verification

#### Phase 3: Testing & Refinement (Week 3)
- [ ] Test with simple parallel tasks (3 workers)
- [ ] Validate dependency resolution
- [ ] Test failure handling and retries
- [ ] Measure performance vs external orchestration

#### Phase 4: Evaluation (Week 4)
- [ ] Compare performance metrics
- [ ] Evaluate user experience (natural language vs YAML)
- [ ] Assess maintenance complexity
- [ ] Decide on merge strategy or continuation

### Success Criteria

- Successfully spawn and coordinate 3+ parallel workers
- Dependency resolution works correctly
- Hooks integrate seamlessly with Claude Code
- User can trigger parallel work via natural language
- Performance comparable to external orchestration
- Clear decision on production viability

## Comparison Matrix

| Feature | Main Branch (External) | Experimental (Hook-Based) |
|---------|----------------------|---------------------------|
| **Orchestration** | Python external | Claude Code internal |
| **Task Definition** | YAML files | Natural language + plan.json |
| **Worker Spawning** | CCR instances | Task tool agents |
| **Coordination** | SSH + Python | Hooks + events.jsonl |
| **Real-Time Status** | Post-execution only | Live updates in session |
| **Dependency Resolution** | Pre-execution batching | Runtime validation |
| **Model Selection** | Explicit (YAML) | Implicit (orchestrator decision) |
| **Setup Complexity** | High (CCR, SSH, configs) | Medium (hooks only) |
| **Execution Location** | Remote (Zo via SSH) | Local or remote (flexible) |
| **Results Format** | JSON + Markdown | Artifacts + inline |
| **User Interface** | CLI with YAML | Conversational |
| **Maintenance** | Python codebase | Bash hooks + Python |
| **Scalability** | High (separate processes) | Medium (single session) |
| **Resource Isolation** | Excellent (separate VMs) | Good (separate agents) |

## Decision Framework

### When to Use Main Branch
- Production workflows with complex dependencies
- Multi-model routing requirements
- Remote execution on specific infrastructure
- Batch processing of large workloads
- Formal task definitions and auditing
- Team collaboration with shared tasks

### When to Use Experimental Branch
- Ad-hoc analysis during development
- Natural language task definition preferred
- Single-session convenience important
- Real-time status updates critical
- Prototype/exploration workflows
- Local development environments

## Migration Path

### If Experimental Proves Viable

1. **Hybrid Mode**: Support both external and hook-based in main
2. **Gradual Migration**: Port high-value workflows to hooks
3. **Feature Parity**: Ensure hooks support all main features
4. **Documentation**: Comprehensive guides for both modes
5. **Deprecation**: Phase out external if hooks superior

### If Experimental Has Limitations

1. **Extract Learnings**: Port good ideas to main (e.g., better status updates)
2. **Keep Separate**: Maintain experimental for specific use cases
3. **Archive**: Document findings and archive if not viable
4. **Focus on Main**: Invest all resources in external orchestration

## Timeline

```
Week 1-2:  Main Branch Phase 1 (Core Enhancements)
Week 1:    Experimental Phase 1 (Foundation)
Week 2:    Experimental Phase 2 (Hook Integration)
Week 3-4:  Main Branch Phase 2 (Production Hardening)
Week 3:    Experimental Phase 3 (Testing)
Week 4:    Experimental Phase 4 (Evaluation)
Week 5-6:  Main Branch Phase 3 (Advanced Features)
Week 5-6:  Decision & Integration (if experimental viable)
```

## Next Steps

1. **Create Branches**
   ```bash
   git checkout -b main  # Ensure main is up to date
   git checkout -b experimental/hook-based-orchestration
   ```

2. **Document Current State**
   - Full feature inventory on main
   - Architecture diagrams
   - API documentation

3. **Begin Parallel Development**
   - Team A: Main branch enhancements
   - Team B: Experimental hook implementation

4. **Regular Sync**
   - Weekly demos of progress
   - Bi-weekly architecture reviews
   - Monthly decision checkpoint

## Conclusion

This dual-branch strategy allows us to:
- **Preserve** the proven external orchestration model
- **Explore** innovative hook-based internal coordination
- **Learn** from both approaches
- **Decide** on the best path forward based on evidence

Both branches have clear goals, success criteria, and evaluation metrics. The comparison matrix helps us understand trade-offs, and the decision framework guides when to use each approach.

The experimental branch is a low-risk, high-reward exploration that could significantly improve user experience if successful, while the main branch continues to deliver production value with enhanced features and hardening.
