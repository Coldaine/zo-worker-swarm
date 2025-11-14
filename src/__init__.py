"""
Zo Worker Swarm
Parallel AI-powered task execution on remote Zo machine
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .orchestrator import ZoWorkerSwarm
from .ccr_manager import CCRManager
from .task_parser import TaskParser, TaskDefinition
from .ssh_executor import SSHExecutor, TaskResult
from .results_aggregator import ResultsAggregator
from .secrets_manager import SecretsManager, get_secrets_manager

__all__ = [
    "ZoWorkerSwarm",
    "CCRManager",
    "TaskParser",
    "TaskDefinition",
    "SSHExecutor",
    "TaskResult",
    "ResultsAggregator",
    "SecretsManager",
    "get_secrets_manager"
]
