# Zo Worker Swarm 🐝

Execute parallel AI-powered tasks on remote Zo machine using multiple Claude Code instances routed through different AI models optimized for specific task types.

## Overview

Zo Worker Swarm orchestrates multiple Claude Code CLI instances, each connected to a different AI model via Claude Code Router (CCR), to execute tasks in parallel on a remote Zo machine via SSH. This enables:

- **Parallel Task Execution**: Run multiple tasks simultaneously on Zo
- **Model Optimization**: Route each task to the AI model best suited for it
- **Cost Efficiency**: Use fast/free models for simple tasks, premium models for complex ones
- **Automated Workflows**: Define complex multi-step workflows in YAML
- **Results Aggregation**: Automatic collection, analysis, and reporting of all results

## Architecture

```
Windows Machine                          Zo Machine (via SSH)
┌─────────────────────────┐             ┌──────────────────────┐
│ CCR Instance #1         │             │                      │
│ Port 3456 (GLM-4.6)     │◄───────────►│                      │
├─────────────────────────┤             │                      │
│ CCR Instance #2         │             │    Task Execution    │
│ Port 3457 (Grok)        │◄───────────►│                      │
├─────────────────────────┤             │                      │
│ CCR Instance #3         │             │                      │
│ Port 3458 (DeepSeek-R1) │◄───────────►│                      │
├─────────────────────────┤             │                      │
│ CCR Instance #4         │             │                      │
│ Port 3459 (DeepSeek)    │◄───────────►│                      │
├─────────────────────────┤             │                      │
│ CCR Instance #5         │             │                      │
│ Port 3460 (Claude S4)   │◄───────────►│                      │
└─────────────────────────┘             └──────────────────────┘
         ▲
         │
    Orchestrator
```

## Features

### 🚀 **Multi-Instance CCR Management**
- Automatically spawn and manage 5 CCR instances on different ports
- Each instance configured with a different AI model
- Health monitoring and status checks

### 📋 **YAML Task Definitions**
- Define tasks in simple, readable YAML format
- Specify which model to use per task
- Support for task dependencies and sequential execution
- Tags and metadata for organization

### ⚡ **Parallel Execution**
- Tasks run simultaneously on Zo via SSH
- Automatic batching based on dependencies
- Real-time progress monitoring

### 📊 **Comprehensive Reporting**
- Terminal dashboard with rich formatting
- JSON results export
- Markdown report generation
- Success rates, timing, and error tracking

### 🔐 **Automatic Secrets Management**
- Bitwarden Secrets Manager integration
- Automatic API key injection from secure vault
- No manual environment variable configuration
- Secure token storage with keychain support
- Team secret sharing with machine accounts

## Installation

### Prerequisites

1. **SSH Access to Zo**
   ```bash
   # Verify SSH connection
   ssh zo "echo 'Connected successfully'"
   ```

2. **Claude Code Router (CCR)**
   ```bash
   # Install CCR
   npm install -g claude-code-router

   # Verify installation
   ccr --version
   ```

3. **Python 3.8+**
   ```bash
   python --version
   ```

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/zo-worker-swarm.git
   cd zo-worker-swarm
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Keys** (Choose Option A or B)

   **Option A: Bitwarden Secrets Manager (Recommended)**

   Automatically manage all API keys with Bitwarden:
   ```bash
   # Set your BWS access token
   export BWS_ACCESS_TOKEN="your-bws-token"

   # Test the connection
   python src/secrets_manager.py
   ```

   📘 **[Complete BWS Setup Guide](docs/BWS_SETUP.md)**

   **Option B: Manual Environment Variables**

   Set API keys manually:
   ```bash
   export ZAI_API_KEY="your-zai-key"
   export XAI_API_KEY="your-xai-key"
   export OPENROUTER_API_KEY="your-openrouter-key"
   ```

## Usage

### Quick Start

```bash
# 1. API keys are automatically loaded from BWS (if configured)
#    Or set manually: export ZAI_API_KEY="..." XAI_API_KEY="..." OPENROUTER_API_KEY="..."

# 2. Start CCR instances
python scripts/run.py start-ccr

# 3. Check status
python scripts/run.py status

# 4. Run example tasks
python scripts/run.py execute tasks/example_zo_tasks.yaml

# 5. Stop CCR instances (optional)
python scripts/run.py stop-ccr
```

> **💡 Tip**: With Bitwarden Secrets Manager configured, API keys are automatically loaded. No manual environment variables needed! See [BWS Setup Guide](docs/BWS_SETUP.md).

### Task Definition Format

Create a YAML file in `tasks/` directory:

```yaml
tasks:
  - name: "Analyze Python Code"
    ccr_instance: "general"  # Which model to use
    command: |
      cd /Projects &&
      find . -name "*.py" | head -20 |
      xargs head -100
    prompt: "Analyze this Python code and provide architecture insights"
    timeout: 300
    tags: ["code-analysis"]
    description: "Code architecture analysis"

  - name: "Quick File Listing"
    ccr_instance: "fast"  # Fast model for simple tasks
    command: "ls -lah /Projects"
    prompt: "Summarize the project structure"
    timeout: 60

  - name: "Deep Code Review"
    ccr_instance: "smart"  # Premium model for complex analysis
    command: "cat /Projects/main.py"
    prompt: "Perform comprehensive code review with security analysis"
    timeout: 400
    dependencies: ["Analyze Python Code"]  # Run after first task
```

### Available CCR Instances

| Instance | Port | Model | Best For | Cost |
|----------|------|-------|----------|------|
| `general` | 3456 | Z.ai GLM-4.6 | General purpose coding | Paid |
| `fast` | 3457 | X.AI Grok | Quick responses, simple tasks | Paid |
| `reasoning` | 3458 | DeepSeek Reasoner | Complex reasoning, step-by-step analysis | Paid |
| `code-review` | 3459 | DeepSeek Chat | Code analysis, reviews | Paid |
| `smart` | 3460 | Claude Sonnet 4 | Highest quality, complex tasks | Paid |

### CLI Commands

```bash
# Execute tasks
python scripts/run.py execute <task_file.yaml>

# Options for execute:
  --no-start-ccr        # Don't start CCR (already running)
  --stop-after          # Stop CCR after execution
  --no-save             # Don't save results to JSON
  --no-report           # Don't generate markdown report
  --quiet               # Minimal output

# CCR Management
python scripts/run.py start-ccr              # Start all instances
python scripts/run.py start-ccr --instance fast  # Start specific instance
python scripts/run.py stop-ccr               # Stop all instances
python scripts/run.py status                 # Show instance status
```

### Advanced Usage

#### Task Dependencies

Tasks can depend on other tasks:

```yaml
tasks:
  - name: "Setup Environment"
    ccr_instance: "fast"
    command: "export PROJECT_DIR=/Projects"
    prompt: "Verify environment setup"

  - name: "Run Analysis"
    ccr_instance: "general"
    command: "cd $PROJECT_DIR && analyze.sh"
    prompt: "Analyze results"
    dependencies: ["Setup Environment"]  # Waits for setup to complete
```

#### Parallel Batches

The system automatically creates execution batches:
- **Batch 1**: All tasks with no dependencies (run in parallel)
- **Batch 2**: Tasks depending on Batch 1 (run in parallel)
- **Batch 3**: Tasks depending on Batch 2 (run in parallel)
- etc...

#### Custom SSH/Windows Hosts

```bash
python scripts/run.py execute tasks/my_tasks.yaml \
  --ssh-host my-remote-server \
  --windows-host 192.168.1.100
```

## Project Structure

```
zo-worker-swarm/
├── src/
│   ├── ccr_manager.py          # Manage CCR instances
│   ├── task_parser.py          # Parse YAML task definitions
│   ├── ssh_executor.py         # Execute tasks via SSH
│   ├── results_aggregator.py   # Collect and report results
│   └── orchestrator.py         # Main coordinator
├── configs/
│   ├── ccr-general.json        # GLM-4.6 config
│   ├── ccr-fast.json           # Llama-3.3 config
│   ├── ccr-reasoning.json      # DeepSeek Reasoner config
│   ├── ccr-code-review.json    # DeepSeek Chat config
│   └── ccr-smart.json          # Claude Sonnet 4 config
├── tasks/
│   ├── example_zo_tasks.yaml   # Example tasks
│   └── README.md               # Task definition guide
├── scripts/
│   └── run.py                  # CLI entry point
├── results/                    # Generated results (JSON, MD)
├── requirements.txt
└── README.md
```

## Example Workflows

### 1. Code Analysis Pipeline
```yaml
tasks:
  - name: "Find Python Files"
    ccr_instance: "fast"
    command: "find /Projects -name '*.py'"
    prompt: "List project structure"

  - name: "Analyze Architecture"
    ccr_instance: "general"
    command: "cat /Projects/**/*.py"
    prompt: "Analyze architecture patterns"
    dependencies: ["Find Python Files"]

  - name: "Security Review"
    ccr_instance: "smart"
    command: "cat /Projects/**/*.py"
    prompt: "Perform security analysis"
    dependencies: ["Analyze Architecture"]
```

### 2. System Audit
```yaml
tasks:
  - name: "Check Resources"
    ccr_instance: "fast"
    command: "free -h && df -h"
    prompt: "Summarize system resources"

  - name: "List Services"
    ccr_instance: "fast"
    command: "systemctl list-units --type=service"
    prompt: "Identify running services"

  - name: "Optimization Recommendations"
    ccr_instance: "reasoning"
    command: "du -sh /* 2>/dev/null"
    prompt: "Provide optimization strategy"
    dependencies: ["Check Resources", "List Services"]
```

### 3. Documentation Extraction
```yaml
tasks:
  - name: "Extract Decisions"
    ccr_instance: "reasoning"
    command: "cat /Projects/ARCHITECTURE.md"
    prompt: "Extract architectural decisions in structured format"
    timeout: 600
```

## Results

### Terminal Output
- Real-time progress updates
- Color-coded status indicators
- Summary statistics
- Detailed task results

### JSON Export
```json
{
  "timestamp": "2025-11-14T10:30:00",
  "summary": {
    "total_tasks": 8,
    "successful": 7,
    "failed": 1,
    "success_rate": 87.5,
    "total_duration": 245.3
  },
  "tasks": [...]
}
```

### Markdown Report
Automatically generated report with:
- Summary statistics
- Results by instance
- Detailed task outputs
- Error information

## Troubleshooting

### CCR Won't Start
```bash
# Check if ports are available
netstat -an | findstr "3456 3457 3458 3459 3460"

# Kill existing processes if needed
taskkill /F /IM ccr.exe
```

### SSH Connection Issues
```bash
# Test SSH connection
ssh zo "echo 'test'"

# Check SSH config
cat ~/.ssh/config

# Verify SSH key
ssh-add -l
```

### Task Timeout
Increase timeout in task definition:
```yaml
- name: "Long Running Task"
  timeout: 1200  # 20 minutes
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built on [Claude Code Router](https://github.com/anthropics/claude-code-router)
- Uses [Rich](https://rich.readthedocs.io/) for terminal UI
- Inspired by distributed task orchestration patterns

---

**Questions?** Open an issue on GitHub or check the documentation in `tasks/README.md`
