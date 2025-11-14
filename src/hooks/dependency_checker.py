#!/usr/bin/env python3
"""
Dependency Checker for Task Dependencies

Checks if task dependencies are satisfied by reading events.jsonl
and verifying that all prerequisite tasks have completed.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional


class DependencyChecker:
    """Check if task dependencies are satisfied"""

    @classmethod
    def check_dependencies(
        cls,
        events_path: str,
        plan_path: str,
        task_id: Optional[str] = None
    ) -> bool:
        """
        Check if dependencies are satisfied for a specific task or all tasks

        Args:
            events_path: Path to events.jsonl
            plan_path: Path to plan.json
            task_id: Optional specific task ID to check (checks all if None)

        Returns:
            True if dependencies satisfied, False otherwise
        """
        # Load plan
        try:
            with open(plan_path) as f:
                plan = json.load(f)
        except FileNotFoundError:
            return True  # No plan means no dependencies

        # Get completed tasks
        completed = cls._get_completed_tasks(events_path)

        # Check specific task or all tasks
        if task_id:
            task = cls._find_task(plan, task_id)
            if not task:
                return True  # Task not found, allow execution
            return cls._check_task_dependencies(task, completed)
        else:
            # Check all tasks with dependencies
            for task in plan.get("tasks", []):
                if task.get("dependencies"):
                    if not cls._check_task_dependencies(task, completed):
                        return False
            return True

    @classmethod
    def get_blocking_dependencies(
        cls,
        events_path: str,
        plan_path: str,
        task_id: str
    ) -> List[str]:
        """
        Get list of dependencies that are blocking a task

        Args:
            events_path: Path to events.jsonl
            plan_path: Path to plan.json
            task_id: Task ID to check

        Returns:
            List of blocking dependency task IDs
        """
        # Load plan
        try:
            with open(plan_path) as f:
                plan = json.load(f)
        except FileNotFoundError:
            return []

        # Find task
        task = cls._find_task(plan, task_id)
        if not task:
            return []

        # Get completed tasks
        completed = cls._get_completed_tasks(events_path)

        # Find blocking dependencies
        dependencies = task.get("dependencies", [])
        blocking = [dep for dep in dependencies if dep not in completed]

        return blocking

    @classmethod
    def get_ready_tasks(cls, events_path: str, plan_path: str) -> List[str]:
        """
        Get list of tasks that are ready to execute (dependencies satisfied)

        Args:
            events_path: Path to events.jsonl
            plan_path: Path to plan.json

        Returns:
            List of task IDs that are ready to execute
        """
        # Load plan
        try:
            with open(plan_path) as f:
                plan = json.load(f)
        except FileNotFoundError:
            return []

        # Get completed and started tasks
        completed = cls._get_completed_tasks(events_path)
        started = cls._get_started_tasks(events_path)

        ready_tasks = []
        for task in plan.get("tasks", []):
            task_id = task["id"]

            # Skip if already started or completed
            if task_id in started or task_id in completed:
                continue

            # Check if dependencies satisfied
            if cls._check_task_dependencies(task, completed):
                ready_tasks.append(task_id)

        return ready_tasks

    @classmethod
    def _get_completed_tasks(cls, events_path: str) -> Set[str]:
        """Get set of completed task IDs"""
        completed = set()
        events_file = Path(events_path)

        if events_file.exists():
            with open(events_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event = json.loads(line)
                            if event.get("type") == "done" and event.get("status") == "success":
                                completed.add(event.get("worker_id"))
                        except json.JSONDecodeError:
                            continue

        return completed

    @classmethod
    def _get_started_tasks(cls, events_path: str) -> Set[str]:
        """Get set of started task IDs"""
        started = set()
        events_file = Path(events_path)

        if events_file.exists():
            with open(events_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event = json.loads(line)
                            if event.get("type") == "start":
                                started.add(event.get("worker_id"))
                        except json.JSONDecodeError:
                            continue

        return started

    @classmethod
    def _find_task(cls, plan: dict, task_id: str) -> Optional[dict]:
        """Find task by ID in plan"""
        for task in plan.get("tasks", []):
            if task["id"] == task_id:
                return task
        return None

    @classmethod
    def _check_task_dependencies(cls, task: dict, completed: Set[str]) -> bool:
        """Check if all dependencies for a task are completed"""
        dependencies = task.get("dependencies", [])
        return all(dep in completed for dep in dependencies)


def main():
    """CLI entry point"""
    if len(sys.argv) < 3:
        print("Usage: dependency_checker.py <events.jsonl> <plan.json> [task_id]", file=sys.stderr)
        sys.exit(1)

    events_path = sys.argv[1]
    plan_path = sys.argv[2]
    task_id = sys.argv[3] if len(sys.argv) > 3 else None

    checker = DependencyChecker()

    # Check dependencies
    if task_id:
        # Check specific task
        if checker.check_dependencies(events_path, plan_path, task_id):
            print(f"Task {task_id}: Dependencies satisfied", file=sys.stderr)
            sys.exit(0)
        else:
            blocking = checker.get_blocking_dependencies(events_path, plan_path, task_id)
            print(f"Task {task_id}: Waiting for {', '.join(blocking)}", file=sys.stderr)
            sys.exit(1)
    else:
        # Check all tasks
        if checker.check_dependencies(events_path, plan_path):
            print("All dependencies satisfied", file=sys.stderr)
            sys.exit(0)
        else:
            # Show ready tasks
            ready = checker.get_ready_tasks(events_path, plan_path)
            print(f"Ready tasks: {', '.join(ready)}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
