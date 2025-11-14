"""
Task Parser
Loads and validates YAML task definitions for execution on Zo
"""

import yaml
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class TaskDefinition:
    """Represents a single task to execute"""
    name: str
    ccr_instance: str
    command: str
    prompt: str
    timeout: int = 300
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    description: str = ""
    output_file: Optional[str] = None

    def __post_init__(self):
        """Validate task definition after initialization"""
        if not self.name:
            raise ValueError("Task name is required")
        if not self.ccr_instance:
            raise ValueError(f"Task '{self.name}': ccr_instance is required")
        if not self.command and not self.prompt:
            raise ValueError(f"Task '{self.name}': Either command or prompt is required")

    def __repr__(self):
        return f"Task('{self.name}', instance={self.ccr_instance}, timeout={self.timeout}s)"


class TaskParser:
    """Parses YAML task definition files"""

    VALID_INSTANCES = ["general", "fast", "reasoning", "code-review", "smart"]

    @staticmethod
    def load_from_file(file_path: str) -> List[TaskDefinition]:
        """Load task definitions from a YAML file

        Args:
            file_path: Path to YAML file

        Returns:
            List of TaskDefinition objects

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid or task definitions are malformed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Task file not found: {file_path}")

        with open(file_path, 'r') as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in {file_path}: {e}")

        if not isinstance(data, dict) or 'tasks' not in data:
            raise ValueError(f"Task file must contain 'tasks' key at root level")

        tasks_data = data['tasks']
        if not isinstance(tasks_data, list):
            raise ValueError(f"'tasks' must be a list")

        return TaskParser.parse_tasks(tasks_data)

    @staticmethod
    def parse_tasks(tasks_data: List[Dict]) -> List[TaskDefinition]:
        """Parse list of task dictionaries into TaskDefinition objects

        Args:
            tasks_data: List of task dictionaries

        Returns:
            List of TaskDefinition objects
        """
        tasks = []

        for i, task_dict in enumerate(tasks_data):
            try:
                # Validate CCR instance
                instance = task_dict.get('ccr_instance')
                if instance and instance not in TaskParser.VALID_INSTANCES:
                    print(f"[!] Warning: Task {i+1} uses unknown instance '{instance}'")
                    print(f"    Valid instances: {', '.join(TaskParser.VALID_INSTANCES)}")

                # Create task definition
                task = TaskDefinition(
                    name=task_dict.get('name', f'Task-{i+1}'),
                    ccr_instance=task_dict.get('ccr_instance', 'general'),
                    command=task_dict.get('command', ''),
                    prompt=task_dict.get('prompt', ''),
                    timeout=task_dict.get('timeout', 300),
                    dependencies=task_dict.get('dependencies', []),
                    tags=task_dict.get('tags', []),
                    description=task_dict.get('description', ''),
                    output_file=task_dict.get('output_file')
                )

                tasks.append(task)

            except Exception as e:
                print(f"[-] Error parsing task {i+1}: {e}")
                continue

        return tasks

    @staticmethod
    def validate_dependencies(tasks: List[TaskDefinition]) -> bool:
        """Validate that all task dependencies exist

        Args:
            tasks: List of task definitions

        Returns:
            True if all dependencies are valid, False otherwise
        """
        task_names = {task.name for task in tasks}
        all_valid = True

        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_names:
                    print(f"[-] Task '{task.name}' depends on non-existent task '{dep}'")
                    all_valid = False

        return all_valid

    @staticmethod
    def get_execution_order(tasks: List[TaskDefinition]) -> List[List[TaskDefinition]]:
        """Determine execution order based on dependencies

        Returns a list of "batches" where each batch contains tasks that can
        run in parallel (no dependencies between them).

        Args:
            tasks: List of task definitions

        Returns:
            List of task batches, where each batch is a list of tasks

        Example:
            [
                [task_a, task_b],  # Batch 1: No dependencies, run in parallel
                [task_c],           # Batch 2: Depends on task_a
                [task_d, task_e]    # Batch 3: Depend on task_c
            ]
        """
        # Validate dependencies first
        if not TaskParser.validate_dependencies(tasks):
            raise ValueError("Invalid task dependencies")

        # Build dependency graph
        task_map = {task.name: task for task in tasks}
        completed = set()
        batches = []

        while len(completed) < len(tasks):
            # Find tasks whose dependencies are all completed
            ready_tasks = []
            for task in tasks:
                if task.name not in completed:
                    deps_met = all(dep in completed for dep in task.dependencies)
                    if deps_met:
                        ready_tasks.append(task)

            if not ready_tasks:
                # Circular dependency detected
                remaining = [t.name for t in tasks if t.name not in completed]
                raise ValueError(f"Circular dependency detected among tasks: {remaining}")

            # Add this batch
            batches.append(ready_tasks)

            # Mark as completed
            for task in ready_tasks:
                completed.add(task.name)

        return batches

    @staticmethod
    def print_execution_plan(batches: List[List[TaskDefinition]]):
        """Print a formatted execution plan

        Args:
            batches: List of task batches from get_execution_order()
        """
        print("\n" + "="*80)
        print("TASK EXECUTION PLAN")
        print("="*80 + "\n")

        total_tasks = sum(len(batch) for batch in batches)
        print(f"Total tasks: {total_tasks}")
        print(f"Execution batches: {len(batches)}\n")

        for i, batch in enumerate(batches, 1):
            print(f"[*] Batch {i} ({len(batch)} task{'s' if len(batch) > 1 else ''} in parallel)")
            print("-" * 80)

            for task in batch:
                deps_str = f" [depends on: {', '.join(task.dependencies)}]" if task.dependencies else ""
                print(f"  - {task.name}")
                print(f"    Instance: {task.ccr_instance} | Timeout: {task.timeout}s{deps_str}")

            print()


if __name__ == "__main__":
    # Test the parser
    test_yaml = """
tasks:
  - name: "Test Task 1"
    ccr_instance: "fast"
    command: "echo 'Hello'"
    prompt: "Test prompt"
    timeout: 60

  - name: "Test Task 2"
    ccr_instance: "general"
    command: "echo 'World'"
    prompt: "Another test"
    dependencies: ["Test Task 1"]
    """

    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(test_yaml)
        temp_file = f.name

    try:
        tasks = TaskParser.load_from_file(temp_file)
        print(f"Loaded {len(tasks)} tasks:")
        for task in tasks:
            print(f"  {task}")

        batches = TaskParser.get_execution_order(tasks)
        TaskParser.print_execution_plan(batches)

    finally:
        Path(temp_file).unlink()
