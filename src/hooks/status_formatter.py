#!/usr/bin/env python3
"""
Status Formatter for Worker Progress

Reads events.jsonl and formats current status of all workers
for display in the main session.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


class StatusFormatter:
    """Format worker status from event log"""

    @classmethod
    def get_latest_status(cls, events_path: str, plan_path: str) -> str:
        """
        Get formatted status of all workers

        Args:
            events_path: Path to events.jsonl
            plan_path: Path to plan.json

        Returns:
            Formatted status string (e.g., "w1 80% | w2 done | w3 waiting")
        """
        # Load plan
        try:
            with open(plan_path) as f:
                plan = json.load(f)
        except FileNotFoundError:
            return ""

        # Load events
        events = cls._load_events(events_path)

        # Build status map
        status_map = cls._build_status_map(events)

        # Format status message
        parts = []
        for task in plan.get("tasks", []):
            task_id = task["id"]
            status = status_map.get(task_id, cls._format_waiting())
            parts.append(f"{task_id} {status}")

        return " | ".join(parts)

    @classmethod
    def get_detailed_status(cls, events_path: str, plan_path: str) -> Dict:
        """
        Get detailed status of all workers

        Args:
            events_path: Path to events.jsonl
            plan_path: Path to plan.json

        Returns:
            Dictionary with detailed status information
        """
        # Load plan
        try:
            with open(plan_path) as f:
                plan = json.load(f)
        except FileNotFoundError:
            return {}

        # Load events
        events = cls._load_events(events_path)

        # Build status map with details
        status_details = {}
        for task in plan.get("tasks", []):
            task_id = task["id"]
            task_events = [e for e in events if e.get("worker_id") == task_id]

            if not task_events:
                status_details[task_id] = {
                    "status": "waiting",
                    "progress": 0,
                    "message": "Not started"
                }
            else:
                latest = task_events[-1]
                event_type = latest.get("type")

                if event_type == "done":
                    status_details[task_id] = {
                        "status": "done",
                        "progress": 100,
                        "message": "Completed successfully"
                    }
                elif event_type == "error":
                    status_details[task_id] = {
                        "status": "error",
                        "progress": 0,
                        "message": latest.get("message", "Error occurred")
                    }
                elif event_type == "progress":
                    status_details[task_id] = {
                        "status": "running",
                        "progress": latest.get("percent", 0),
                        "message": latest.get("message", "In progress")
                    }
                elif event_type == "start":
                    status_details[task_id] = {
                        "status": "running",
                        "progress": 0,
                        "message": "Started"
                    }
                else:
                    status_details[task_id] = {
                        "status": "unknown",
                        "progress": 0,
                        "message": "Unknown status"
                    }

        return {
            "session_id": plan.get("session_id"),
            "total_tasks": plan.get("total_tasks", 0),
            "workers": status_details
        }

    @classmethod
    def _load_events(cls, events_path: str) -> List[dict]:
        """Load events from JSONL file"""
        events = []
        events_file = Path(events_path)

        if events_file.exists():
            with open(events_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

        return events

    @classmethod
    def _build_status_map(cls, events: List[dict]) -> Dict[str, str]:
        """Build status map from events"""
        status_map = {}

        for event in events:
            worker_id = event.get("worker_id")
            event_type = event.get("type")

            if event_type == "start":
                status_map[worker_id] = cls._format_running(0)
            elif event_type == "progress":
                percent = event.get("percent", 0)
                status_map[worker_id] = cls._format_running(percent)
            elif event_type == "done":
                status_map[worker_id] = cls._format_done()
            elif event_type == "error":
                status_map[worker_id] = cls._format_error()

        return status_map

    @classmethod
    def _format_running(cls, percent: int) -> str:
        """Format running status"""
        return f"⏳ {percent}%"

    @classmethod
    def _format_done(cls) -> str:
        """Format done status"""
        return "✓ done"

    @classmethod
    def _format_error(cls) -> str:
        """Format error status"""
        return "✗ error"

    @classmethod
    def _format_waiting(cls) -> str:
        """Format waiting status"""
        return "⏸ waiting"


def main():
    """CLI entry point"""
    if len(sys.argv) < 3:
        print("Usage: status_formatter.py <events.jsonl> <plan.json>", file=sys.stderr)
        sys.exit(1)

    events_path = sys.argv[1]
    plan_path = sys.argv[2]

    formatter = StatusFormatter()

    # Check if detailed output requested
    if len(sys.argv) > 3 and sys.argv[3] == "--detailed":
        status = formatter.get_detailed_status(events_path, plan_path)
        print(json.dumps(status, indent=2))
    else:
        status = formatter.get_latest_status(events_path, plan_path)
        print(status)


if __name__ == "__main__":
    main()
