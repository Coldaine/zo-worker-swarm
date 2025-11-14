"""
Results Aggregator
Collects, analyzes, and reports on task execution results
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.text import Text

from ssh_executor import TaskResult


class ResultsAggregator:
    """Aggregates and reports on task execution results"""

    def __init__(self, results_dir: str = None):
        """Initialize results aggregator

        Args:
            results_dir: Directory to save results (default: project/results/)
        """
        if results_dir is None:
            project_root = Path(__file__).parent.parent
            results_dir = project_root / "results"

        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)

        self.console = Console()
        self.results: List[TaskResult] = []

    def add_results(self, results: List[TaskResult]):
        """Add task results to the aggregator

        Args:
            results: List of TaskResult objects
        """
        self.results.extend(results)

    def get_summary_stats(self) -> Dict:
        """Calculate summary statistics

        Returns:
            Dictionary with summary statistics
        """
        if not self.results:
            return {}

        total_tasks = len(self.results)
        successful = sum(1 for r in self.results if r.status == "success")
        failed = sum(1 for r in self.results if r.status == "failed")
        timeout = sum(1 for r in self.results if r.status == "timeout")

        total_duration = sum(r.duration_seconds for r in self.results)
        avg_duration = total_duration / total_tasks if total_tasks > 0 else 0

        # Group by instance
        by_instance = {}
        for result in self.results:
            instance = result.ccr_instance
            if instance not in by_instance:
                by_instance[instance] = {"count": 0, "success": 0, "duration": 0}

            by_instance[instance]["count"] += 1
            if result.status == "success":
                by_instance[instance]["success"] += 1
            by_instance[instance]["duration"] += result.duration_seconds

        return {
            "total_tasks": total_tasks,
            "successful": successful,
            "failed": failed,
            "timeout": timeout,
            "success_rate": (successful / total_tasks * 100) if total_tasks > 0 else 0,
            "total_duration": total_duration,
            "average_duration": avg_duration,
            "by_instance": by_instance
        }

    def print_summary(self):
        """Print formatted summary to console"""
        if not self.results:
            self.console.print("[yellow]No results to display[/yellow]")
            return

        stats = self.get_summary_stats()

        # Create summary panel
        summary_text = f"""
[bold]Total Tasks:[/bold] {stats['total_tasks']}
[green]✅ Successful:[/green] {stats['successful']}
[red]❌ Failed:[/red] {stats['failed']}
[yellow]⏱️  Timeout:[/yellow] {stats['timeout']}
[bold]Success Rate:[/bold] {stats['success_rate']:.1f}%

[bold]Duration:[/bold]
  Total: {stats['total_duration']:.1f}s
  Average: {stats['average_duration']:.1f}s per task
        """

        self.console.print(Panel(
            summary_text.strip(),
            title="📊 Execution Summary",
            border_style="blue"
        ))

        # Instance breakdown table
        if stats['by_instance']:
            table = Table(title="\\n📦 Results by Instance")
            table.add_column("Instance", style="cyan")
            table.add_column("Tasks", justify="right")
            table.add_column("Success", justify="right")
            table.add_column("Success %", justify="right")
            table.add_column("Avg Duration", justify="right")

            for instance, data in stats['by_instance'].items():
                success_rate = (data['success'] / data['count'] * 100) if data['count'] > 0 else 0
                avg_dur = data['duration'] / data['count'] if data['count'] > 0 else 0

                table.add_row(
                    instance,
                    str(data['count']),
                    str(data['success']),
                    f"{success_rate:.1f}%",
                    f"{avg_dur:.1f}s"
                )

            self.console.print(table)

    def print_detailed_results(self):
        """Print detailed results for each task"""
        if not self.results:
            return

        self.console.print("\\n" + "="*80)
        self.console.print("[bold]DETAILED TASK RESULTS[/bold]")
        self.console.print("="*80 + "\\n")

        for i, result in enumerate(self.results, 1):
            # Status icon and color
            if result.status == "success":
                status_text = "[green]✅ SUCCESS[/green]"
            elif result.status == "failed":
                status_text = "[red]❌ FAILED[/red]"
            else:
                status_text = "[yellow]⏱️  TIMEOUT[/yellow]"

            self.console.print(f"[bold]{i}. {result.task_name}[/bold] - {status_text}")
            self.console.print(f"   Instance: {result.ccr_instance} (port {result.ccr_port})")
            self.console.print(f"   Duration: {result.duration_seconds:.2f}s")
            self.console.print(f"   Time: {result.start_time.strftime('%H:%M:%S')} - {result.end_time.strftime('%H:%M:%S')}")

            if result.output:
                # Show first 500 chars of output
                preview = result.output[:500]
                if len(result.output) > 500:
                    preview += f"... ({len(result.output) - 500} more chars)"

                self.console.print("   [dim]Output:[/dim]")
                self.console.print(f"   {preview}")

            if result.error:
                self.console.print(f"   [red]Error: {result.error}[/red]")

            self.console.print()  # Blank line between results

    def save_results(self, filename: str = None) -> Path:
        """Save results to JSON file

        Args:
            filename: Output filename (default: results-TIMESTAMP.json)

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"results-{timestamp}.json"

        output_path = self.results_dir / filename

        # Convert results to dict
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_summary_stats(),
            "tasks": [
                {
                    "name": r.task_name,
                    "status": r.status,
                    "output": r.output,
                    "error": r.error,
                    "duration_seconds": r.duration_seconds,
                    "start_time": r.start_time.isoformat(),
                    "end_time": r.end_time.isoformat(),
                    "ccr_instance": r.ccr_instance,
                    "ccr_port": r.ccr_port
                }
                for r in self.results
            ]
        }

        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2)

        self.console.print(f"\\n💾 Results saved to: [cyan]{output_path}[/cyan]")

        return output_path

    def generate_markdown_report(self, filename: str = None) -> Path:
        """Generate markdown report of results

        Args:
            filename: Output filename (default: report-TIMESTAMP.md)

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"report-{timestamp}.md"

        output_path = self.results_dir / filename

        stats = self.get_summary_stats()

        # Build markdown content
        md_lines = [
            "# Zo Worker Swarm - Execution Report",
            f"\\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n",
            "## Summary",
            f"- **Total Tasks**: {stats['total_tasks']}",
            f"- **Successful**: {stats['successful']} ✅",
            f"- **Failed**: {stats['failed']} ❌",
            f"- **Timeout**: {stats['timeout']} ⏱️",
            f"- **Success Rate**: {stats['success_rate']:.1f}%",
            f"- **Total Duration**: {stats['total_duration']:.1f}s",
            f"- **Average Duration**: {stats['average_duration']:.1f}s per task",
            "\\n## Results by Instance\\n"
        ]

        # Instance breakdown
        if stats['by_instance']:
            md_lines.append("| Instance | Tasks | Success | Success % | Avg Duration |")
            md_lines.append("|----------|-------|---------|-----------|--------------|")

            for instance, data in stats['by_instance'].items():
                success_rate = (data['success'] / data['count'] * 100) if data['count'] > 0 else 0
                avg_dur = data['duration'] / data['count'] if data['count'] > 0 else 0

                md_lines.append(
                    f"| {instance} | {data['count']} | {data['success']} | "
                    f"{success_rate:.1f}% | {avg_dur:.1f}s |"
                )

        # Detailed results
        md_lines.append("\\n## Detailed Task Results\\n")

        for i, result in enumerate(self.results, 1):
            status_emoji = {"success": "✅", "failed": "❌", "timeout": "⏱️"}.get(result.status, "❓")

            md_lines.extend([
                f"### {i}. {result.task_name} {status_emoji}",
                f"- **Status**: {result.status}",
                f"- **Instance**: {result.ccr_instance} (port {result.ccr_port})",
                f"- **Duration**: {result.duration_seconds:.2f}s",
                f"- **Time**: {result.start_time.strftime('%H:%M:%S')} - {result.end_time.strftime('%H:%M:%S')}"
            ])

            if result.output:
                md_lines.append("\\n**Output:**")
                md_lines.append("```")
                # Limit output in markdown
                output_lines = result.output.split('\\n')[:50]
                md_lines.extend(output_lines)
                if len(result.output.split('\\n')) > 50:
                    md_lines.append("... (output truncated)")
                md_lines.append("```")

            if result.error:
                md_lines.append(f"\\n**Error:** `{result.error}`")

            md_lines.append("")  # Blank line

        with open(output_path, 'w') as f:
            f.write('\\n'.join(md_lines))

        self.console.print(f"📄 Markdown report saved to: [cyan]{output_path}[/cyan]")

        return output_path

    def display_live_dashboard(self):
        """Display a live updating dashboard (for future use with async execution)"""
        # Placeholder for rich live dashboard
        # This would be used with rich.live.Live for real-time updates
        pass


if __name__ == "__main__":
    # Test the aggregator
    from ssh_executor import TaskResult
    from datetime import datetime, timedelta

    # Create some test results
    test_results = [
        TaskResult(
            task_name="Test Task 1",
            status="success",
            output="Task completed successfully",
            error="",
            duration_seconds=5.2,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=5.2),
            ccr_instance="fast",
            ccr_port=3457
        ),
        TaskResult(
            task_name="Test Task 2",
            status="failed",
            output="",
            error="Connection timeout",
            duration_seconds=30.0,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=30),
            ccr_instance="general",
            ccr_port=3456
        )
    ]

    aggregator = ResultsAggregator()
    aggregator.add_results(test_results)
    aggregator.print_summary()
    aggregator.print_detailed_results()
