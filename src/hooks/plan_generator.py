#!/usr/bin/env python3
"""
Plan Generator for Parallel Execution

Generates execution plan (plan.json) from user prompts by extracting
targets and creating task definitions with dependencies.
"""
import json
import re
import sys
import uuid
from datetime import datetime
from typing import List, Dict, Optional


class PlanGenerator:
    """Generate execution plans from user prompts"""

    @classmethod
    def extract_targets(cls, prompt: str) -> List[str]:
        """
        Extract items to process from prompt

        Args:
            prompt: User prompt

        Returns:
            List of target items (files, modules, PRs, etc.)
        """
        targets = []

        # Pattern 1: Comma-separated items "modules A, B, C"
        module_match = re.search(
            r'(?:files?|modules?|components?|packages?)\s+([A-Z][A-Za-z0-9]*(?:,\s*[A-Z][A-Za-z0-9]*)+)',
            prompt,
            re.IGNORECASE
        )
        if module_match:
            items = module_match.group(1).split(',')
            targets = [item.strip() for item in items]
            return targets

        # Pattern 2: File names "file1.py, file2.py, file3.js"
        file_matches = re.findall(
            r'\b([\w\-]+\.(?:py|js|ts|tsx|jsx|java|go|rs|cpp|c|h|rb|php|swift))\b',
            prompt
        )
        if file_matches:
            return file_matches

        # Pattern 3: PR numbers "PRs 123, 456, 789"
        pr_matches = re.findall(r'\b(\d{2,})\b', prompt)
        if pr_matches and re.search(r'\b(?:PR|pull\s+request)', prompt, re.IGNORECASE):
            return [f"PR-{pr}" for pr in pr_matches]

        # Pattern 4: Quarters "Q1, Q2, Q3, Q4"
        quarter_matches = re.findall(r'\b(Q[1-4])\b', prompt, re.IGNORECASE)
        if quarter_matches:
            return [q.upper() for q in quarter_matches]

        # Pattern 5: Months "January, February, March"
        month_matches = re.findall(
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b',
            prompt,
            re.IGNORECASE
        )
        if month_matches:
            return month_matches

        # Pattern 6: Generic "all files" or "each module" - create default targets
        if re.search(r'(all|each|every)\s+(files?|modules?|components?)', prompt, re.IGNORECASE):
            # Generate generic targets
            return ["Item1", "Item2", "Item3"]

        # Pattern 7: Look for quoted items
        quoted_matches = re.findall(r'["\']([^"\']+)["\']', prompt)
        if quoted_matches:
            return quoted_matches

        return targets

    @classmethod
    def determine_work_type(cls, prompt: str) -> tuple:
        """
        Determine the type of work and action verb

        Args:
            prompt: User prompt

        Returns:
            Tuple of (work_type, action_verb)
        """
        prompt_lower = prompt.lower()

        if re.search(r'\btest', prompt_lower):
            return ("test", "Test")
        elif re.search(r'\banalyze', prompt_lower):
            return ("analyze", "Analyze")
        elif re.search(r'\breview', prompt_lower):
            return ("review", "Review")
        elif re.search(r'\bgenerate', prompt_lower):
            return ("generate", "Generate")
        elif re.search(r'\bcreate', prompt_lower):
            return ("create", "Create")
        elif re.search(r'\bprocess', prompt_lower):
            return ("process", "Process")
        elif re.search(r'\bcheck', prompt_lower):
            return ("check", "Check")
        else:
            return ("execute", "Execute")

    @classmethod
    def generate_plan(cls, prompt: str, targets: Optional[List[str]] = None) -> dict:
        """
        Generate execution plan from prompt

        Args:
            prompt: User prompt
            targets: Optional list of targets (will be extracted if not provided)

        Returns:
            Plan dictionary with tasks and dependencies
        """
        # Generate session ID
        session_id = f"S{uuid.uuid4().hex[:8]}"

        # Extract targets if not provided
        if targets is None:
            targets = cls.extract_targets(prompt)

        # If no targets found, create a single task
        if not targets:
            targets = ["default"]

        # Determine work type
        work_type, action_verb = cls.determine_work_type(prompt)

        # Create worker tasks
        tasks = []
        for i, target in enumerate(targets, 1):
            task = {
                "id": f"w{i}",
                "name": f"{action_verb} {target}",
                "prompt": f"{action_verb} {target}: {prompt}",
                "target": target.strip(),
                "dependencies": [],
                "status": "pending",
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            tasks.append(task)

        # Add merge task if multiple workers
        if len(tasks) > 1:
            merge_task = {
                "id": f"w{len(tasks) + 1}",
                "name": "Merge Results",
                "prompt": f"Merge and summarize results from all {work_type} workers",
                "dependencies": [f"w{i}" for i in range(1, len(tasks) + 1)],
                "status": "pending",
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            tasks.append(merge_task)

        # Create plan
        plan = {
            "session_id": session_id,
            "prompt": prompt,
            "work_type": work_type,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "total_tasks": len(tasks),
            "tasks": tasks
        }

        return plan

    @classmethod
    def save_plan(cls, plan: dict, output_path: str = ".claude/parallel-state/plan.json"):
        """
        Save plan to JSON file

        Args:
            plan: Plan dictionary
            output_path: Path to save plan
        """
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(plan, f, indent=2)

    @classmethod
    def load_plan(cls, plan_path: str = ".claude/parallel-state/plan.json") -> dict:
        """
        Load plan from JSON file

        Args:
            plan_path: Path to plan file

        Returns:
            Plan dictionary
        """
        with open(plan_path) as f:
            return json.load(f)


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: plan_generator.py <prompt>", file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1]
    generator = PlanGenerator()

    # Generate plan
    plan = generator.generate_plan(prompt)

    # Output to stdout
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
