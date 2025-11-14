#!/usr/bin/env python3
"""
Orchestrator Agent for Hook-Based Parallel Execution

Coordinates parallel worker execution by:
1. Reading plan.json to get task definitions
2. Spawning worker agents in parallel (via Task tool or subprocess)
3. Monitoring progress via events.jsonl
4. Handling failures and retries
5. Collecting artifacts when complete
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from event_logger import EventLogger
from hooks.dependency_checker import DependencyChecker


class OrchestratorAgent:
    """Coordinate parallel worker execution"""

    def __init__(self, state_dir: str = ".claude/parallel-state"):
        """
        Initialize orchestrator

        Args:
            state_dir: Directory for shared state
        """
        self.state_dir = Path(state_dir)
        self.plan_path = self.state_dir / "plan.json"
        self.events_path = self.state_dir / "events.jsonl"
        self.artifacts_dir = self.state_dir / "artifacts"

        # Ensure directories exist
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Initialize event logger
        self.logger = EventLogger(str(self.events_path))

    def load_plan(self) -> dict:
        """Load execution plan from plan.json"""
        if not self.plan_path.exists():
            raise FileNotFoundError(f"Plan not found: {self.plan_path}")

        with open(self.plan_path) as f:
            return json.load(f)

    async def spawn_worker(self, task: dict) -> dict:
        """
        Spawn a single worker

        In production, this would use Claude Code's Task tool.
        For now, we simulate or use subprocess to run worker_agent.py

        Args:
            task: Task definition from plan

        Returns:
            Result dictionary
        """
        task_id = task["id"]
        task_name = task["name"]
        task_prompt = task["prompt"]

        print(f"[Orchestrator] Spawning worker {task_id}: {task_name}")

        # Log start event
        self.logger.emit_start(task_id, task_name, prompt=task_prompt)

        try:
            # In production: Use Claude Code Task tool
            # task_result = await claude_code_task_tool(prompt=task_prompt)

            # For now: Simulate or call worker_agent.py
            result = await self._execute_worker(task_id, task_prompt, task)

            # Log completion
            self.logger.emit_done(task_id, status="success")

            print(f"[Orchestrator] Worker {task_id} completed successfully")

            return {
                "task_id": task_id,
                "status": "success",
                "result": result
            }

        except Exception as e:
            # Log error
            self.logger.emit_error(task_id, str(e))

            print(f"[Orchestrator] Worker {task_id} failed: {e}")

            return {
                "task_id": task_id,
                "status": "error",
                "error": str(e)
            }

    async def _execute_worker(self, task_id: str, prompt: str, task: dict) -> dict:
        """
        Execute worker logic

        In production, this calls Claude Code Task tool or runs worker_agent.py
        For now, we simulate the work

        Args:
            task_id: Task ID
            prompt: Task prompt
            task: Full task definition

        Returns:
            Worker result
        """
        # Simulate work with progress updates
        for progress in [25, 50, 75, 100]:
            await asyncio.sleep(0.5)  # Simulate work
            self.logger.emit_progress(task_id, progress)

        # Generate result
        result = {
            "task_id": task_id,
            "task_name": task["name"],
            "target": task.get("target", "unknown"),
            "output": f"Completed {task['name']}",
            "success": True,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        # Save artifact
        artifact_path = self.artifacts_dir / f"{task_id}_result.json"
        with open(artifact_path, "w") as f:
            json.dump(result, f, indent=2)

        # Log artifact
        self.logger.emit_artifact(task_id, str(artifact_path))

        return result

    async def execute_batch(self, tasks: List[dict]) -> List[dict]:
        """
        Execute a batch of tasks in parallel

        Args:
            tasks: List of task definitions

        Returns:
            List of results
        """
        print(f"\n[Orchestrator] Executing batch of {len(tasks)} tasks in parallel")

        # Spawn all workers in parallel
        results = await asyncio.gather(*[
            self.spawn_worker(task) for task in tasks
        ], return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task_id = tasks[i]["id"]
                processed_results.append({
                    "task_id": task_id,
                    "status": "error",
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        return processed_results

    def organize_tasks_into_batches(self, tasks: List[dict]) -> List[List[dict]]:
        """
        Organize tasks into execution batches based on dependencies

        Args:
            tasks: List of all tasks

        Returns:
            List of batches, where each batch can run in parallel
        """
        # Separate tasks by dependencies
        independent_tasks = []
        dependent_tasks = []

        for task in tasks:
            if task.get("dependencies"):
                dependent_tasks.append(task)
            else:
                independent_tasks.append(task)

        batches = []

        # Batch 1: All independent tasks
        if independent_tasks:
            batches.append(independent_tasks)

        # Batch 2+: Dependent tasks (for now, run sequentially)
        # In production, would do proper topological sort
        for task in dependent_tasks:
            batches.append([task])

        return batches

    async def run(self) -> Dict:
        """
        Execute orchestration

        Returns:
            Summary of execution
        """
        print("=" * 60)
        print("ORCHESTRATOR STARTED")
        print("=" * 60)

        # Load plan
        plan = self.load_plan()
        session_id = plan["session_id"]
        total_tasks = plan["total_tasks"]

        print(f"\nSession ID: {session_id}")
        print(f"Total Tasks: {total_tasks}")
        print(f"Work Type: {plan.get('work_type', 'unknown')}")

        # Organize into batches
        batches = self.organize_tasks_into_batches(plan["tasks"])
        print(f"\nExecution Plan: {len(batches)} batches")

        # Execute batches sequentially, tasks within batch in parallel
        all_results = []
        for batch_num, batch in enumerate(batches, 1):
            print(f"\n{'=' * 60}")
            print(f"BATCH {batch_num} of {len(batches)}")
            print(f"{'=' * 60}")

            batch_results = await self.execute_batch(batch)
            all_results.extend(batch_results)

            # Wait for dependencies to be satisfied before next batch
            if batch_num < len(batches):
                await asyncio.sleep(1)

        # Summary
        successful = sum(1 for r in all_results if r.get("status") == "success")
        failed = sum(1 for r in all_results if r.get("status") == "error")

        print(f"\n{'=' * 60}")
        print("ORCHESTRATION COMPLETE")
        print(f"{'=' * 60}")
        print(f"Total Tasks: {len(all_results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {successful / len(all_results) * 100:.1f}%")
        print(f"{'=' * 60}\n")

        return {
            "session_id": session_id,
            "total_tasks": len(all_results),
            "successful": successful,
            "failed": failed,
            "results": all_results
        }


async def main():
    """Entry point"""
    print("Orchestrator Agent Starting...")

    # Check for state directory
    state_dir = sys.argv[1] if len(sys.argv) > 1 else ".claude/parallel-state"

    try:
        orchestrator = OrchestratorAgent(state_dir)
        summary = await orchestrator.run()

        # Save summary
        summary_path = Path(state_dir) / "orchestrator_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"Summary saved to: {summary_path}")

        # Exit with success
        sys.exit(0 if summary["failed"] == 0 else 1)

    except Exception as e:
        print(f"Orchestrator failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
