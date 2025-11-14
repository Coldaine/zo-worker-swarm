#!/usr/bin/env python3
"""
Pattern Detector for Parallelizable Prompts

Detects whether a user prompt contains parallelizable work patterns.
Returns True if the prompt can be executed in parallel, False otherwise.
"""
import re
import sys
from typing import List, Optional


class PatternDetector:
    """Detect parallelizable patterns in user prompts"""

    # Patterns that indicate parallelizable work
    PATTERNS = [
        # Test patterns
        r'test.*(all|each|every).*(files?|modules?|components?|packages?)',
        r'run\s+tests?\s+(on|for|in|across)\s+(all|each|multiple)',
        r'test\s+(all|each|multiple)',

        # Analysis patterns
        r'analyze.*(files?|modules?|components?).*[A-Z,]',
        r'analyze\s+(all|each|multiple|these)',
        r'(review|check|inspect).*(all|each|multiple)',

        # Processing patterns
        r'process.*(in\s+parallel|concurrently|simultaneously)',
        r'(parallel|concurrent).*(process|execution|run)',
        r'process\s+(all|each|multiple)',

        # Generation patterns
        r'generate.*(reports?|docs?|summaries?).*(for|from)\s+(\w+,\s*)+',
        r'create.*(reports?|docs?).*(for|from)\s+(\w+,\s*)+',

        # Review patterns
        r'review.*(PRs?|pull\s+requests?|issues?).*\d+',
        r'check.*(all|each|multiple).*(files?|modules?)',

        # Multiple target patterns
        r'(analyze|test|process|review|check)\s+\w+,\s*\w+',  # comma-separated items
        r'for\s+(each|every|all)\s+(file|module|component)',

        # Explicit parallel keywords
        r'\b(parallel|concurrently|simultaneously|in\s+parallel)\b',
    ]

    # Exclusion patterns (things that look parallel but aren't)
    EXCLUSIONS = [
        r'what\s+(is|are)',  # Questions
        r'how\s+(do|does|can)',  # How-to questions
        r'why\s+',  # Why questions
        r'explain\s+',  # Explanations
        r'tell\s+me\s+about',  # Information requests
    ]

    @classmethod
    def is_parallelizable(cls, prompt: str) -> bool:
        """
        Check if prompt matches parallelizable patterns

        Args:
            prompt: User prompt to analyze

        Returns:
            True if parallelizable, False otherwise
        """
        if not prompt or not prompt.strip():
            return False

        prompt_lower = prompt.lower()

        # Check exclusions first
        for exclusion in cls.EXCLUSIONS:
            if re.search(exclusion, prompt_lower, re.IGNORECASE):
                return False

        # Check for parallelizable patterns
        for pattern in cls.PATTERNS:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                return True

        # Check for multiple comma-separated items (likely targets)
        if cls._has_multiple_targets(prompt):
            return True

        return False

    @classmethod
    def _has_multiple_targets(cls, prompt: str) -> bool:
        """Check if prompt has multiple comma-separated targets"""
        # Look for patterns like "files A, B, C" or "modules X, Y, Z"
        match = re.search(
            r'(files?|modules?|components?|packages?|PRs?)\s+([A-Z0-9]+(?:,\s*[A-Z0-9]+)+)',
            prompt,
            re.IGNORECASE
        )
        return match is not None

    @classmethod
    def get_match_info(cls, prompt: str) -> Optional[dict]:
        """
        Get detailed information about the matched pattern

        Args:
            prompt: User prompt to analyze

        Returns:
            Dictionary with match details or None if not parallelizable
        """
        if not cls.is_parallelizable(prompt):
            return None

        prompt_lower = prompt.lower()

        # Determine work type
        if re.search(r'\btest', prompt_lower):
            work_type = "test"
        elif re.search(r'\banalyze', prompt_lower):
            work_type = "analyze"
        elif re.search(r'\breview', prompt_lower):
            work_type = "review"
        elif re.search(r'\bgenerate', prompt_lower):
            work_type = "generate"
        elif re.search(r'\bprocess', prompt_lower):
            work_type = "process"
        else:
            work_type = "execute"

        # Find which pattern matched
        matched_pattern = None
        for pattern in cls.PATTERNS:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                matched_pattern = pattern
                break

        return {
            "work_type": work_type,
            "matched_pattern": matched_pattern,
            "prompt": prompt
        }


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: pattern_detector.py <prompt>", file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1]
    detector = PatternDetector()

    if detector.is_parallelizable(prompt):
        # Return 0 for True (parallelizable)
        info = detector.get_match_info(prompt)
        if info:
            print(f"Parallelizable: {info['work_type']}", file=sys.stderr)
        sys.exit(0)
    else:
        # Return 1 for False (not parallelizable)
        sys.exit(1)


if __name__ == "__main__":
    main()
