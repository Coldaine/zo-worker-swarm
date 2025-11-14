"""
SSH Executor
Executes tasks on Zo via SSH, using Claude Code routed through CCR instances
"""

import asyncio
import subprocess
import time
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from task_parser import TaskDefinition


@dataclass
class TaskResult:
    """Result from executing a task"""
    task_name: str
    status: str  # 'success', 'failed', 'timeout'
    output: str
    error: str
    duration_seconds: float
    start_time: datetime
    end_time: datetime
    ccr_instance: str
    ccr_port: int

    def __repr__(self):
        status_icon = "[+]" if self.status == "success" else "[-]"
        return f"{status_icon} {self.task_name} ({self.duration_seconds:.1f}s) - {self.status}"


class SSHExecutor:
    """Executes tasks on Zo via SSH"""

    def __init__(self, ssh_host: str = "zo", windows_host: str = "205.178.77.159"):
        """Initialize SSH executor

        Args:
            ssh_host: SSH host to connect to (from SSH config)
            windows_host: Windows machine IP/hostname for CCR callbacks
        """
        self.ssh_host = ssh_host
        self.windows_host = windows_host

    async def execute_task(
        self,
        task: TaskDefinition,
        ccr_port: int,
        verbose: bool = False
    ) -> TaskResult:
        """Execute a single task on Zo

        Args:
            task: Task definition
            ccr_port: CCR instance port to use
            verbose: Print detailed output

        Returns:
            TaskResult object with execution results
        """
        start_time = datetime.now()

        if verbose:
            print(f"\n[*] Executing: {task.name}")
            print(f"    Instance: {task.ccr_instance} (port {ccr_port})")
            print(f"    Timeout: {task.timeout}s")

        # Build the SSH command that will execute on Zo
        ssh_cmd = self._build_ssh_command(task, ccr_port)

        try:
            # Execute the command
            process = await asyncio.create_subprocess_shell(
                ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=task.timeout
                )

                output = stdout.decode('utf-8') if stdout else ""
                error = stderr.decode('utf-8') if stderr else ""
                status = "success" if process.returncode == 0 else "failed"

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                output = ""
                error = f"Task timed out after {task.timeout} seconds"
                status = "timeout"

        except Exception as e:
            output = ""
            error = f"Exception during execution: {str(e)}"
            status = "failed"

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = TaskResult(
            task_name=task.name,
            status=status,
            output=output,
            error=error,
            duration_seconds=duration,
            start_time=start_time,
            end_time=end_time,
            ccr_instance=task.ccr_instance,
            ccr_port=ccr_port
        )

        if verbose:
            self._print_result(result)

        return result

    def _build_ssh_command(self, task: TaskDefinition, ccr_port: int) -> str:
        """Build the SSH command to execute on Zo

        The command structure is:
        1. SSH into Zo
        2. Set CCR environment variables (host, port)
        3. Execute the task command (if any)
        4. Pipe output to Claude Code with the task prompt
        5. Claude Code connects back to Windows CCR instance

        Args:
            task: Task definition
            ccr_port: CCR port to connect to

        Returns:
            Complete SSH command string
        """
        # Environment variables for CCR connection
        env_vars = f"export CCR_HOST={self.windows_host} && export CCR_PORT={ccr_port}"

        # Build Claude Code command
        # We'll use the --anthropic-api-url flag to point to our CCR instance
        ccr_url = f"http://{self.windows_host}:{ccr_port}"
        claude_cmd = f'claude code -p "{task.prompt}"'

        if task.command:
            # If there's a command, execute it and pipe to Claude
            full_cmd = f"{env_vars} && {task.command} | {claude_cmd} --anthropic-api-url {ccr_url}"
        else:
            # No command, just execute Claude with the prompt
            full_cmd = f"{env_vars} && {claude_cmd} --anthropic-api-url {ccr_url}"

        # Wrap in SSH command
        ssh_cmd = f'ssh {self.ssh_host} "{full_cmd}"'

        return ssh_cmd

    async def execute_batch(
        self,
        tasks: List[TaskDefinition],
        ccr_ports: Dict[str, int],
        verbose: bool = False
    ) -> List[TaskResult]:
        """Execute multiple tasks in parallel

        Args:
            tasks: List of tasks to execute
            ccr_ports: Mapping of instance name to port number
            verbose: Print detailed output

        Returns:
            List of TaskResult objects
        """
        if verbose:
            print(f"\n[*] Executing batch of {len(tasks)} tasks in parallel...")

        # Create tasks with their corresponding CCR ports
        async_tasks = []
        for task in tasks:
            ccr_port = ccr_ports.get(task.ccr_instance)
            if ccr_port is None:
                print(f"[-] Error: No CCR port found for instance '{task.ccr_instance}'")
                continue

            async_tasks.append(self.execute_task(task, ccr_port, verbose))

        # Execute all tasks in parallel
        results = await asyncio.gather(*async_tasks)

        return results

    async def execute_all_batches(
        self,
        batches: List[List[TaskDefinition]],
        ccr_ports: Dict[str, int],
        verbose: bool = False
    ) -> List[TaskResult]:
        """Execute all task batches sequentially (batches in parallel internally)

        Args:
            batches: List of task batches from task_parser.get_execution_order()
            ccr_ports: Mapping of instance name to port number
            verbose: Print detailed output

        Returns:
            List of all TaskResult objects
        """
        all_results = []

        for i, batch in enumerate(batches, 1):
            if verbose:
                print(f"\n{'='*80}")
                print(f"BATCH {i}/{len(batches)}")
                print(f"{'='*80}")

            batch_results = await self.execute_batch(batch, ccr_ports, verbose)
            all_results.extend(batch_results)

            # Check if all tasks in batch succeeded
            failed_tasks = [r for r in batch_results if r.status != "success"]
            if failed_tasks and i < len(batches):
                print(f"\n[!] Warning: {len(failed_tasks)} task(s) failed in batch {i}")
                print("    Continuing to next batch...")

        return all_results

    def _print_result(self, result: TaskResult):
        """Print formatted task result

        Args:
            result: TaskResult object
        """
        status_icons = {
            "success": "[+]",
            "failed": "[-]",
            "timeout": "[!]"
        }
        icon = status_icons.get(result.status, "[?]")

        print(f"\n{icon} {result.task_name} - {result.status.upper()}")
        print(f"   Duration: {result.duration_seconds:.1f}s")

        if result.output:
            print(f"   Output preview:")
            # Show first 200 chars of output
            preview = result.output[:200]
            if len(result.output) > 200:
                preview += "..."
            print(f"   {preview}")

        if result.error:
            print(f"   Error: {result.error}")


# Example usage
async def main():
    """Test the SSH executor"""
    from task_parser import TaskDefinition

    # Create a simple test task
    task = TaskDefinition(
        name="Test Task",
        ccr_instance="fast",
        command="echo 'Hello from Zo'",
        prompt="Summarize this output",
        timeout=30
    )

    executor = SSHExecutor()
    result = await executor.execute_task(task, ccr_port=3457, verbose=True)

    print(f"\nResult: {result}")


if __name__ == "__main__":
    asyncio.run(main())
