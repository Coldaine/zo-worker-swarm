"""
Orchestrator
Main coordinator that brings together CCR management, task parsing, SSH execution, and results aggregation
"""

import asyncio
from pathlib import Path
from typing import Optional
from rich.console import Console

from ccr_manager import CCRManager
from task_parser import TaskParser
from ssh_executor import SSHExecutor
from results_aggregator import ResultsAggregator


class ZoWorkerSwarm:
    """Main orchestrator for the Zo Worker Swarm system"""

    def __init__(
        self,
        ssh_host: str = "zo",
        windows_host: str = "205.178.77.159",
        configs_dir: Optional[str] = None,
        results_dir: Optional[str] = None
    ):
        """Initialize the orchestrator

        Args:
            ssh_host: SSH host to connect to Zo
            windows_host: Windows machine IP for CCR callbacks
            configs_dir: Directory containing CCR configs
            results_dir: Directory to save results
        """
        self.console = Console()

        self.ccr_manager = CCRManager(configs_dir)
        self.ssh_executor = SSHExecutor(ssh_host, windows_host)
        self.aggregator = ResultsAggregator(results_dir)

    async def run(
        self,
        task_file: str,
        start_ccr: bool = True,
        stop_ccr_after: bool = False,
        verbose: bool = True,
        save_results: bool = True,
        generate_report: bool = True
    ) -> ResultsAggregator:
        """Run the complete workflow

        Args:
            task_file: Path to YAML task file
            start_ccr: Whether to start CCR instances (default: True)
            stop_ccr_after: Whether to stop CCR instances after execution (default: False)
            verbose: Print detailed progress (default: True)
            save_results: Save results to JSON (default: True)
            generate_report: Generate markdown report (default: True)

        Returns:
            ResultsAggregator with all results
        """
        try:
            # Step 1: Start CCR instances if requested
            if start_ccr:
                self.console.print("\\n[bold blue]STEP 1: Starting CCR Instances[/bold blue]")
                self.ccr_manager.start_all()
                self.console.print()

            # Step 2: Load and parse tasks
            self.console.print("[bold blue]STEP 2: Loading Tasks[/bold blue]")
            tasks = TaskParser.load_from_file(task_file)
            self.console.print(f"[+] Loaded {len(tasks)} tasks from {task_file}\\n")

            # Step 3: Determine execution order
            self.console.print("[bold blue]STEP 3: Planning Execution[/bold blue]")
            batches = TaskParser.get_execution_order(tasks)
            TaskParser.print_execution_plan(batches)

            # Step 4: Get CCR port mappings
            ccr_ports = {
                name: self.ccr_manager.get_instance_port(name)
                for name in self.ccr_manager.list_instances()
            }

            # Step 5: Execute tasks
            self.console.print("[bold blue]STEP 4: Executing Tasks[/bold blue]")
            results = await self.ssh_executor.execute_all_batches(
                batches,
                ccr_ports,
                verbose=verbose
            )

            # Step 6: Aggregate results
            self.aggregator.add_results(results)

            # Step 7: Display results
            self.console.print("\\n[bold blue]STEP 5: Results[/bold blue]")
            self.aggregator.print_summary()

            if verbose:
                self.aggregator.print_detailed_results()

            # Step 8: Save results
            if save_results:
                self.aggregator.save_results()

            if generate_report:
                self.aggregator.generate_markdown_report()

            # Step 9: Stop CCR if requested
            if stop_ccr_after:
                self.console.print("\\n[bold blue]STEP 6: Stopping CCR Instances[/bold blue]")
                self.ccr_manager.stop_all()

            return self.aggregator

        except Exception as e:
            self.console.print(f"\\n[bold red]ERROR: {e}[/bold red]")
            raise

    def status(self):
        """Show status of CCR instances"""
        self.ccr_manager.print_status()

    def start_ccr(self, instance_name: Optional[str] = None):
        """Start CCR instance(s)

        Args:
            instance_name: Specific instance to start, or None for all
        """
        if instance_name:
            self.ccr_manager.start_instance(instance_name)
        else:
            self.ccr_manager.start_all()

    def stop_ccr(self, instance_name: Optional[str] = None):
        """Stop CCR instance(s)

        Args:
            instance_name: Specific instance to stop, or None for all
        """
        if instance_name:
            self.ccr_manager.stop_instance(instance_name)
        else:
            self.ccr_manager.stop_all()


# Example usage
async def main():
    """Example workflow"""
    swarm = ZoWorkerSwarm()

    # Option 1: Run everything automatically
    task_file = "tasks/example_tasks.yaml"
    await swarm.run(
        task_file,
        start_ccr=True,
        stop_ccr_after=False,  # Keep CCR running for multiple runs
        verbose=True,
        save_results=True,
        generate_report=True
    )

    # Option 2: Manual control
    # swarm.start_ccr()
    # swarm.status()
    # results = await swarm.run(task_file, start_ccr=False)
    # swarm.stop_ccr()


if __name__ == "__main__":
    asyncio.run(main())
