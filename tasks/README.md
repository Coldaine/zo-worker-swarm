# Task Definitions

This directory contains YAML task definition files for the Zo Worker Swarm.

## Task File Format

```yaml
tasks:
  - name: "Task Name"              # Required: Descriptive name
    ccr_instance: "general"        # Required: Which CCR instance to use
    command: "ls -la"              # Optional: Command to run on Zo
    prompt: "Analyze this output"  # Required: Prompt for Claude Code
    timeout: 300                   # Optional: Timeout in seconds (default: 300)
    dependencies: []               # Optional: List of task names to wait for
    tags: []                       # Optional: Tags for organization
    description: ""                # Optional: Task description
    output_file: "result.txt"      # Optional: Save output to file
```

## Available CCR Instances

- **general**: Z.ai GLM-4.6 - General purpose coding tasks
- **fast**: X.AI Grok - Fast responses, simple tasks
- **reasoning**: DeepSeek Reasoner - Complex reasoning, deep analysis
- **code-review**: DeepSeek Chat - Code review and analysis
- **smart**: Claude Sonnet 4 - Highest quality, most complex tasks

## Example Tasks

### Simple File Listing
```yaml
- name: "List Projects"
  ccr_instance: "fast"
  command: "ls -lah /Projects"
  prompt: "Summarize the directory structure"
  timeout: 60
```

### Code Analysis
```yaml
- name: "Analyze Python Code"
  ccr_instance: "general"
  command: |
    cd /Projects &&
    find . -name "*.py" | xargs head -100
  prompt: "Analyze code architecture and provide insights"
  timeout: 300
  tags: ["code-analysis", "python"]
```

### Sequential Tasks with Dependencies
```yaml
tasks:
  - name: "Setup"
    ccr_instance: "fast"
    command: "cd /Projects && pwd"
    prompt: "Confirm we're in the right directory"

  - name: "Analysis"
    ccr_instance: "general"
    command: "cat *.py"
    prompt: "Analyze the code"
    dependencies: ["Setup"]  # Waits for Setup to complete
```

## Task Organization

You can create multiple task files for different workflows:

- `code_analysis.yaml` - Code analysis tasks
- `system_audit.yaml` - System health and resource checks
- `documentation.yaml` - Documentation extraction and generation
- `performance.yaml` - Performance testing and benchmarking
- `deployment.yaml` - Deployment verification tasks

## Running Tasks

```bash
# Run a specific task file
python scripts/run.py execute tasks/your_tasks.yaml

# Run with options
python scripts/run.py execute tasks/your_tasks.yaml --quiet --no-save
```

## Best Practices

1. **Choose the right instance**: Match model capabilities to task complexity
   - Use `fast` for simple listing/summarization
   - Use `general` for standard coding tasks
   - Use `reasoning` for complex multi-step analysis
   - Use `code-review` for code quality analysis
   - Use `smart` for critical/complex tasks

2. **Set appropriate timeouts**: Consider task complexity
   - Simple tasks: 60-120s
   - Standard tasks: 180-300s
   - Complex tasks: 400-600s

3. **Use dependencies wisely**: Chain tasks when later tasks need earlier results

4. **Add tags and descriptions**: Make tasks searchable and understandable

5. **Test incrementally**: Start with one or two tasks before running large batches

## Troubleshooting

**Task times out**: Increase `timeout` value

**Wrong model used**: Check `ccr_instance` matches available instances

**Task fails**: Check `command` syntax and SSH connectivity to Zo

**Dependencies not working**: Ensure task names in `dependencies` match exactly
