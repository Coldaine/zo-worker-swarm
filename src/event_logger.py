#!/usr/bin/env python3
"""
Event Logger for Parallel Orchestration

Provides utilities for logging events to events.jsonl in an append-only fashion.
All workers and the orchestrator use this to coordinate via the event log.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from threading import Lock


class EventLogger:
    """Thread-safe event logger for parallel workers"""

    def __init__(self, events_path: str = ".claude/parallel-state/events.jsonl"):
        """
        Initialize event logger

        Args:
            events_path: Path to events.jsonl file
        """
        self.events_path = Path(events_path)
        self._lock = Lock()

        # Ensure directory exists
        self.events_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: dict) -> None:
        """
        Emit an event to the log

        Args:
            event: Event dictionary (will add timestamp if not present)
        """
        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Thread-safe append to file
        with self._lock:
            with open(self.events_path, 'a') as f:
                f.write(json.dumps(event) + '\n')

    def emit_start(self, worker_id: str, task_name: str, **kwargs) -> None:
        """Emit a task start event"""
        event = {
            "worker_id": worker_id,
            "type": "start",
            "task": task_name,
            **kwargs
        }
        self.emit(event)

    def emit_progress(self, worker_id: str, percent: int, message: str = "", **kwargs) -> None:
        """Emit a progress event"""
        event = {
            "worker_id": worker_id,
            "type": "progress",
            "percent": percent,
            "message": message,
            **kwargs
        }
        self.emit(event)

    def emit_artifact(self, worker_id: str, artifact_path: str, **kwargs) -> None:
        """Emit an artifact creation event"""
        event = {
            "worker_id": worker_id,
            "type": "artifact",
            "path": artifact_path,
            **kwargs
        }
        self.emit(event)

    def emit_done(self, worker_id: str, status: str = "success", **kwargs) -> None:
        """Emit a task completion event"""
        event = {
            "worker_id": worker_id,
            "type": "done",
            "status": status,
            **kwargs
        }
        self.emit(event)

    def emit_error(self, worker_id: str, message: str, **kwargs) -> None:
        """Emit an error event"""
        event = {
            "worker_id": worker_id,
            "type": "error",
            "message": message,
            **kwargs
        }
        self.emit(event)

    def read_events(self, since: Optional[str] = None) -> List[dict]:
        """
        Read events from log

        Args:
            since: Optional timestamp to read events after

        Returns:
            List of event dictionaries
        """
        events = []

        if not self.events_path.exists():
            return events

        with open(self.events_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)

                    # Filter by timestamp if requested
                    if since and event.get("timestamp", "") <= since:
                        continue

                    events.append(event)
                except json.JSONDecodeError:
                    continue

        return events

    def get_worker_events(self, worker_id: str) -> List[dict]:
        """
        Get all events for a specific worker

        Args:
            worker_id: Worker ID to filter by

        Returns:
            List of events for the worker
        """
        all_events = self.read_events()
        return [e for e in all_events if e.get("worker_id") == worker_id]

    def get_latest_event(self, worker_id: str) -> Optional[dict]:
        """
        Get the latest event for a worker

        Args:
            worker_id: Worker ID

        Returns:
            Latest event or None if no events
        """
        events = self.get_worker_events(worker_id)
        return events[-1] if events else None

    def clear(self) -> None:
        """Clear the event log (use with caution!)"""
        if self.events_path.exists():
            self.events_path.unlink()

    def archive(self, archive_path: Optional[str] = None) -> str:
        """
        Archive the current event log

        Args:
            archive_path: Optional custom archive path

        Returns:
            Path to archived file
        """
        if not self.events_path.exists():
            return ""

        if archive_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_dir = self.events_path.parent / "archive"
            archive_dir.mkdir(exist_ok=True)
            archive_path = archive_dir / f"events_{timestamp}.jsonl"

        # Copy to archive
        import shutil
        shutil.copy2(self.events_path, archive_path)

        return str(archive_path)


class EventReader:
    """Read and analyze events without modifying the log"""

    def __init__(self, events_path: str = ".claude/parallel-state/events.jsonl"):
        """
        Initialize event reader

        Args:
            events_path: Path to events.jsonl file
        """
        self.events_path = Path(events_path)

    def get_statistics(self) -> Dict:
        """
        Get statistics about events

        Returns:
            Dictionary with event statistics
        """
        events = self._read_all_events()

        workers = set(e.get("worker_id") for e in events if e.get("worker_id"))
        event_types = {}

        for event in events:
            event_type = event.get("type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1

        # Count completed workers
        completed_workers = set()
        error_workers = set()

        for event in events:
            if event.get("type") == "done":
                completed_workers.add(event.get("worker_id"))
            elif event.get("type") == "error":
                error_workers.add(event.get("worker_id"))

        return {
            "total_events": len(events),
            "total_workers": len(workers),
            "completed_workers": len(completed_workers),
            "error_workers": len(error_workers),
            "event_types": event_types,
            "workers": list(workers)
        }

    def get_timeline(self) -> List[dict]:
        """
        Get chronological timeline of events

        Returns:
            List of events in chronological order
        """
        events = self._read_all_events()
        return sorted(events, key=lambda e: e.get("timestamp", ""))

    def _read_all_events(self) -> List[dict]:
        """Read all events from file"""
        events = []

        if not self.events_path.exists():
            return events

        with open(self.events_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return events


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: event_logger.py <command> [args]")
        print("\nCommands:")
        print("  emit <worker_id> <type> [message]  - Emit an event")
        print("  read [events.jsonl]                 - Read all events")
        print("  stats [events.jsonl]                - Show statistics")
        sys.exit(1)

    command = sys.argv[1]

    if command == "emit":
        if len(sys.argv) < 4:
            print("Usage: event_logger.py emit <worker_id> <type> [message]")
            sys.exit(1)

        worker_id = sys.argv[2]
        event_type = sys.argv[3]
        message = sys.argv[4] if len(sys.argv) > 4 else ""

        logger = EventLogger()

        if event_type == "start":
            logger.emit_start(worker_id, message)
        elif event_type == "progress":
            logger.emit_progress(worker_id, 50, message)
        elif event_type == "done":
            logger.emit_done(worker_id)
        elif event_type == "error":
            logger.emit_error(worker_id, message)
        else:
            logger.emit({"worker_id": worker_id, "type": event_type, "message": message})

        print(f"Event emitted: {worker_id} - {event_type}")

    elif command == "read":
        events_path = sys.argv[2] if len(sys.argv) > 2 else ".claude/parallel-state/events.jsonl"
        logger = EventLogger(events_path)
        events = logger.read_events()

        for event in events:
            print(json.dumps(event))

    elif command == "stats":
        events_path = sys.argv[2] if len(sys.argv) > 2 else ".claude/parallel-state/events.jsonl"
        reader = EventReader(events_path)
        stats = reader.get_statistics()

        print(json.dumps(stats, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
