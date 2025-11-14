#!/usr/bin/env python3
"""
Zo Worker Swarm - CLI Entry Point
Orchestrates parallel task execution on Zo using multiple CCR instances
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestrator import ZoWorkerSwarm


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(
        description="Zo Worker Swarm - Execute tasks on Zo using multiple AI models in parallel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run tasks from a file
  python run.py execute tasks/example_tasks.yaml

  # Start CCR instances only
  python run.py start-ccr

  # Check CCR instance status
  python run.py status

  # Stop all CCR instances
  python run.py stop-ccr

  # Run tasks with specific options
  python run.py execute tasks/my_tasks.yaml --no-start-ccr --stop-after
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Execute command
    execute_parser = subparsers.add_parser('execute', help='Execute tasks from a file')
    execute_parser.add_argument('task_file', help='Path to YAML task file')
    execute_parser.add_argument(
        '--no-start-ccr',
        action='store_true',
        help='Do not start CCR instances (assumes they are already running)'
    )
    execute_parser.add_argument(
        '--stop-after',
        action='store_true',
        help='Stop CCR instances after execution'
    )
    execute_parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save results to file'
    )
    execute_parser.add_argument(
        '--no-report',
        action='store_true',
        help='Do not generate markdown report'
    )
    execute_parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output (no detailed task output)'
    )
    execute_parser.add_argument(
        '--ssh-host',
        default='zo',
        help='SSH host to connect to (default: zo)'
    )
    execute_parser.add_argument(
        '--windows-host',
        default='205.178.77.159',
        help='Windows machine IP for CCR (default: 205.178.77.159)'
    )

    # Start CCR command
    start_parser = subparsers.add_parser('start-ccr', help='Start CCR instances')
    start_parser.add_argument(
        '--instance',
        help='Specific instance to start (default: all)'
    )

    # Stop CCR command
    stop_parser = subparsers.add_parser('stop-ccr', help='Stop CCR instances')
    stop_parser.add_argument(
        '--instance',
        help='Specific instance to stop (default: all)'
    )

    # Status command
    subparsers.add_parser('status', help='Show CCR instance status')

    return parser


async def run_execute(args):
    """Execute tasks command"""
    swarm = ZoWorkerSwarm(
        ssh_host=args.ssh_host,
        windows_host=args.windows_host
    )

    await swarm.run(
        task_file=args.task_file,
        start_ccr=not args.no_start_ccr,
        stop_ccr_after=args.stop_after,
        verbose=not args.quiet,
        save_results=not args.no_save,
        generate_report=not args.no_report
    )


def run_start_ccr(args):
    """Start CCR instances command"""
    swarm = ZoWorkerSwarm()
    swarm.start_ccr(args.instance if hasattr(args, 'instance') else None)


def run_stop_ccr(args):
    """Stop CCR instances command"""
    swarm = ZoWorkerSwarm()
    swarm.stop_ccr(args.instance if hasattr(args, 'instance') else None)


def run_status(args):
    """Show status command"""
    swarm = ZoWorkerSwarm()
    swarm.status()


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'execute':
            asyncio.run(run_execute(args))
        elif args.command == 'start-ccr':
            run_start_ccr(args)
        elif args.command == 'stop-ccr':
            run_stop_ccr(args)
        elif args.command == 'status':
            run_status(args)
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\\n\\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
