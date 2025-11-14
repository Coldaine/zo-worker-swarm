#!/usr/bin/env python3
"""
Worker Agent Template

Each worker is an independent agent (spawned via Claude Code Task tool or subprocess)
that executes an assigned task and emits events to coordinate with the orchestrator.

Workers:
1. Execute assigned task
2. Emit progress events to events.jsonl
3. Save results to artifacts directory
4. Handle errors gracefully
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from event_logger import EventLogger


class WorkerAgent:
    """Worker agent for parallel task execution"""

    def __init__(
        self,
        task_id: str,
        prompt: str,
        task_config: Optional[Dict] = None,
        state_dir: str = ".claude/parallel-state"
    ):
        """
        Initialize worker

        Args:
            task_id: Unique task ID (e.g., "w1", "w2")
            prompt: Task prompt/instructions
            task_config: Optional additional task configuration
            state_dir: Directory for shared state
        """
        self.task_id = task_id
        self.prompt = prompt
        self.task_config = task_config or {}
        self.state_dir = Path(state_dir)

        # Initialize event logger
        self.logger = EventLogger(str(self.state_dir / "events.jsonl"))

        # Artifacts directory
        self.artifacts_dir = self.state_dir / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def emit_start(self) -> None:
        """Emit start event"""
        self.logger.emit_start(
            self.task_id,
            self.task_config.get("name", "Unknown Task"),
            prompt=self.prompt
        )

    def emit_progress(self, percent: int, message: str = "") -> None:
        """Emit progress event"""
        self.logger.emit_progress(self.task_id, percent, message)

    def save_artifact(self, result: Dict) -> str:
        """
        Save result to artifacts directory

        Args:
            result: Result dictionary

        Returns:
            Path to artifact file
        """
        artifact_path = self.artifacts_dir / f"{self.task_id}_result.json"

        with open(artifact_path, "w") as f:
            json.dump(result, f, indent=2)

        # Emit artifact event
        self.logger.emit_artifact(self.task_id, str(artifact_path))

        return str(artifact_path)

    def emit_done(self, status: str = "success") -> None:
        """Emit completion event"""
        self.logger.emit_done(self.task_id, status=status)

    def emit_error(self, error_message: str) -> None:
        """Emit error event"""
        self.logger.emit_error(self.task_id, error_message)

    def execute(self) -> Dict:
        """
        Execute worker task

        Override this method in subclasses for custom logic.
        Default implementation simulates work with progress updates.

        Returns:
            Result dictionary
        """
        print(f"[Worker {self.task_id}] Starting task")
        self.emit_start()

        try:
            # Simulate work with progress updates
            progress_steps = [
                (25, "Initializing..."),
                (50, "Processing..."),
                (75, "Finalizing..."),
                (100, "Complete")
            ]

            for percent, message in progress_steps:
                time.sleep(0.5)  # Simulate work
                print(f"[Worker {self.task_id}] {percent}% - {message}")
                self.emit_progress(percent, message)

            # Generate result
            result = {
                "task_id": self.task_id,
                "prompt": self.prompt,
                "task_name": self.task_config.get("name", "Unknown"),
                "target": self.task_config.get("target", "unknown"),
                "output": f"Completed: {self.prompt}",
                "success": True,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            # Save artifact
            artifact_path = self.save_artifact(result)
            print(f"[Worker {self.task_id}] Artifact saved: {artifact_path}")

            # Mark complete
            self.emit_done(status="success")
            print(f"[Worker {self.task_id}] Task completed successfully")

            return result

        except Exception as e:
            error_msg = f"Worker {self.task_id} failed: {str(e)}"
            print(f"[Worker {self.task_id}] ERROR: {e}")
            self.emit_error(error_msg)
            raise


class CustomWorker(WorkerAgent):
    """
    Example custom worker implementation

    Subclass WorkerAgent and override execute() for custom logic
    """

    def execute(self) -> Dict:
        """Custom execution logic"""
        print(f"[CustomWorker {self.task_id}] Custom execution starting")
        self.emit_start()

        try:
            # Custom logic here
            self.emit_progress(33, "Custom step 1")
            time.sleep(0.3)

            self.emit_progress(66, "Custom step 2")
            time.sleep(0.3)

            self.emit_progress(100, "Custom complete")

            result = {
                "task_id": self.task_id,
                "custom_output": "Custom worker result",
                "success": True,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            self.save_artifact(result)
            self.emit_done()

            return result

        except Exception as e:
            self.emit_error(str(e))
            raise


def main():
    """CLI entry point"""
    if len(sys.argv) < 3:
        print("Usage: worker_agent.py <task_id> <prompt> [task_config_json]")
        print("\nExamples:")
        print('  worker_agent.py w1 "Test module A"')
        print('  worker_agent.py w2 "Analyze file.py" \'{"name": "Analyze file.py", "target": "file.py"}\'')
        sys.exit(1)

    task_id = sys.argv[1]
    prompt = sys.argv[2]
    task_config = None

    if len(sys.argv) > 3:
        try:
            task_config = json.loads(sys.argv[3])
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in task_config: {sys.argv[3]}")
            sys.exit(1)

    # Create and execute worker
    worker = WorkerAgent(task_id, prompt, task_config)

    try:
        result = worker.execute()

        # Print result
        print("\n" + "=" * 60)
        print("WORKER RESULT")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        print("=" * 60)

        sys.exit(0)

    except Exception as e:
        print(f"\nWorker failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
