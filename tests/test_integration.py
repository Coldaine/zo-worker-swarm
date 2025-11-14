#!/usr/bin/env python3
"""
Integration Tests for Hook-Based Orchestration

Tests the complete workflow from pattern detection to worker execution.
"""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hooks.pattern_detector import PatternDetector
from hooks.plan_generator import PlanGenerator
from hooks.status_formatter import StatusFormatter
from hooks.dependency_checker import DependencyChecker
from event_logger import EventLogger
from orchestrator_agent import OrchestratorAgent
from worker_agent import WorkerAgent


class TestPatternDetection(unittest.TestCase):
    """Test parallelizable pattern detection"""

    def test_test_pattern(self):
        """Test detection of test patterns"""
        self.assertTrue(PatternDetector.is_parallelizable("Test all Python files"))
        self.assertTrue(PatternDetector.is_parallelizable("Run tests on all modules"))

    def test_analyze_pattern(self):
        """Test detection of analyze patterns"""
        self.assertTrue(PatternDetector.is_parallelizable("Analyze modules A, B, C"))
        self.assertTrue(PatternDetector.is_parallelizable("Analyze all files"))

    def test_parallel_keyword(self):
        """Test detection of explicit parallel keywords"""
        self.assertTrue(PatternDetector.is_parallelizable("Process files in parallel"))
        self.assertTrue(PatternDetector.is_parallelizable("Run concurrently"))

    def test_exclusions(self):
        """Test that questions are excluded"""
        self.assertFalse(PatternDetector.is_parallelizable("What is Python?"))
        self.assertFalse(PatternDetector.is_parallelizable("How does this work?"))
        self.assertFalse(PatternDetector.is_parallelizable("Explain the concept"))


class TestPlanGeneration(unittest.TestCase):
    """Test plan generation from prompts"""

    def test_generate_from_modules(self):
        """Test plan generation from module list"""
        prompt = "Analyze modules A, B, C"
        plan = PlanGenerator.generate_plan(prompt)

        self.assertEqual(plan["work_type"], "analyze")
        self.assertEqual(len(plan["tasks"]), 4)  # 3 workers + 1 merge
        self.assertEqual(plan["tasks"][0]["target"], "A")
        self.assertEqual(plan["tasks"][1]["target"], "B")
        self.assertEqual(plan["tasks"][2]["target"], "C")
        self.assertEqual(plan["tasks"][3]["name"], "Merge Results")
        self.assertEqual(plan["tasks"][3]["dependencies"], ["w1", "w2", "w3"])

    def test_generate_from_files(self):
        """Test plan generation from file list"""
        prompt = "Test file1.py, file2.py, file3.js"
        plan = PlanGenerator.generate_plan(prompt)

        self.assertEqual(plan["work_type"], "test")
        self.assertGreaterEqual(len(plan["tasks"]), 3)

    def test_generate_from_quarters(self):
        """Test plan generation from quarters"""
        prompt = "Generate reports for Q1, Q2, Q3"
        plan = PlanGenerator.generate_plan(prompt)

        self.assertEqual(plan["work_type"], "generate")
        self.assertEqual(len(plan["tasks"]), 4)  # 3 workers + 1 merge


class TestEventLogging(unittest.TestCase):
    """Test event logging functionality"""

    def setUp(self):
        """Create temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.events_path = os.path.join(self.temp_dir, "events.jsonl")

    def tearDown(self):
        """Clean up temporary directory"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_emit_events(self):
        """Test emitting various event types"""
        logger = EventLogger(self.events_path)

        logger.emit_start("w1", "Test Task")
        logger.emit_progress("w1", 50, "Halfway done")
        logger.emit_artifact("w1", "/path/to/artifact.json")
        logger.emit_done("w1", "success")

        # Read events
        events = logger.read_events()
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0]["type"], "start")
        self.assertEqual(events[1]["type"], "progress")
        self.assertEqual(events[2]["type"], "artifact")
        self.assertEqual(events[3]["type"], "done")

    def test_get_worker_events(self):
        """Test filtering events by worker"""
        logger = EventLogger(self.events_path)

        logger.emit_start("w1", "Task 1")
        logger.emit_start("w2", "Task 2")
        logger.emit_done("w1", "success")

        w1_events = logger.get_worker_events("w1")
        self.assertEqual(len(w1_events), 2)
        self.assertEqual(w1_events[0]["worker_id"], "w1")
        self.assertEqual(w1_events[1]["worker_id"], "w1")


class TestStatusFormatting(unittest.TestCase):
    """Test status formatting from events"""

    def setUp(self):
        """Create temporary directory and test data"""
        self.temp_dir = tempfile.mkdtemp()
        self.events_path = os.path.join(self.temp_dir, "events.jsonl")
        self.plan_path = os.path.join(self.temp_dir, "plan.json")

        # Create test plan
        plan = {
            "session_id": "test123",
            "total_tasks": 3,
            "tasks": [
                {"id": "w1", "name": "Task 1", "dependencies": []},
                {"id": "w2", "name": "Task 2", "dependencies": []},
                {"id": "w3", "name": "Task 3", "dependencies": ["w1", "w2"]}
            ]
        }
        with open(self.plan_path, "w") as f:
            json.dump(plan, f)

    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_status_waiting(self):
        """Test status when no events"""
        status = StatusFormatter.get_latest_status(self.events_path, self.plan_path)
        self.assertIn("waiting", status)

    def test_status_running(self):
        """Test status with running workers"""
        logger = EventLogger(self.events_path)
        logger.emit_start("w1", "Task 1")
        logger.emit_progress("w1", 50)

        status = StatusFormatter.get_latest_status(self.events_path, self.plan_path)
        self.assertIn("50%", status)

    def test_status_done(self):
        """Test status with completed workers"""
        logger = EventLogger(self.events_path)
        logger.emit_start("w1", "Task 1")
        logger.emit_done("w1", "success")

        status = StatusFormatter.get_latest_status(self.events_path, self.plan_path)
        self.assertIn("done", status)


class TestDependencyChecking(unittest.TestCase):
    """Test dependency checking"""

    def setUp(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.events_path = os.path.join(self.temp_dir, "events.jsonl")
        self.plan_path = os.path.join(self.temp_dir, "plan.json")

        # Create plan with dependencies
        plan = {
            "session_id": "test123",
            "tasks": [
                {"id": "w1", "name": "Task 1", "dependencies": []},
                {"id": "w2", "name": "Task 2", "dependencies": []},
                {"id": "w3", "name": "Merge", "dependencies": ["w1", "w2"]}
            ]
        }
        with open(self.plan_path, "w") as f:
            json.dump(plan, f)

    def tearDown(self):
        """Cleanup"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_dependencies_not_satisfied(self):
        """Test that dependencies are not satisfied initially"""
        result = DependencyChecker.check_dependencies(
            self.events_path, self.plan_path, "w3"
        )
        self.assertFalse(result)

    def test_dependencies_satisfied(self):
        """Test that dependencies are satisfied when workers complete"""
        logger = EventLogger(self.events_path)
        logger.emit_done("w1", "success")
        logger.emit_done("w2", "success")

        result = DependencyChecker.check_dependencies(
            self.events_path, self.plan_path, "w3"
        )
        self.assertTrue(result)

    def test_get_ready_tasks(self):
        """Test getting ready tasks"""
        # Initially, w1 and w2 are ready (no dependencies)
        ready = DependencyChecker.get_ready_tasks(self.events_path, self.plan_path)
        self.assertEqual(set(ready), {"w1", "w2"})

        # After w1 and w2 complete, w3 is ready
        logger = EventLogger(self.events_path)
        logger.emit_start("w1", "Task 1")
        logger.emit_start("w2", "Task 2")
        logger.emit_done("w1", "success")
        logger.emit_done("w2", "success")

        ready = DependencyChecker.get_ready_tasks(self.events_path, self.plan_path)
        self.assertEqual(ready, ["w3"])


class TestOrchestratorAgent(unittest.TestCase):
    """Test orchestrator agent"""

    def setUp(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = os.path.join(self.temp_dir, "parallel-state")
        os.makedirs(self.state_dir)

        # Create test plan
        plan = {
            "session_id": "test123",
            "work_type": "test",
            "total_tasks": 3,
            "tasks": [
                {"id": "w1", "name": "Test A", "prompt": "Test module A", "target": "A", "dependencies": []},
                {"id": "w2", "name": "Test B", "prompt": "Test module B", "target": "B", "dependencies": []},
                {"id": "w3", "name": "Merge", "prompt": "Merge results", "dependencies": ["w1", "w2"]}
            ]
        }

        plan_path = os.path.join(self.state_dir, "plan.json")
        with open(plan_path, "w") as f:
            json.dump(plan, f)

    def tearDown(self):
        """Cleanup"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_load_plan(self):
        """Test loading plan"""
        orchestrator = OrchestratorAgent(self.state_dir)
        plan = orchestrator.load_plan()
        self.assertEqual(plan["session_id"], "test123")
        self.assertEqual(len(plan["tasks"]), 3)

    def test_organize_batches(self):
        """Test organizing tasks into batches"""
        orchestrator = OrchestratorAgent(self.state_dir)
        plan = orchestrator.load_plan()
        batches = orchestrator.organize_tasks_into_batches(plan["tasks"])

        # Should have 2 batches: [w1, w2] and [w3]
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0]), 2)  # w1, w2
        self.assertEqual(len(batches[1]), 1)  # w3

    def test_execute_orchestrator(self):
        """Test full orchestrator execution"""
        async def run_test():
            orchestrator = OrchestratorAgent(self.state_dir)
            summary = await orchestrator.run()

            self.assertEqual(summary["total_tasks"], 3)
            self.assertEqual(summary["successful"], 3)
            self.assertEqual(summary["failed"], 0)

        asyncio.run(run_test())


def run_all_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPatternDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestPlanGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestEventLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestStatusFormatting))
    suite.addTests(loader.loadTestsFromTestCase(TestDependencyChecking))
    suite.addTests(loader.loadTestsFromTestCase(TestOrchestratorAgent))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
