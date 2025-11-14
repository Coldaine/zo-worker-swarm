"""
CCR Instance Manager
Manages multiple Claude Code Router instances on different ports with different models.
"""

import subprocess
import json
import os
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional

class CCRInstance:
    """Represents a single CCR instance configuration"""
    def __init__(self, name: str, config_path: str, port: int, model_name: str):
        self.name = name
        self.config_path = config_path
        self.port = port
        self.model_name = model_name
        self.process = None
        self.pid = None

    def __repr__(self):
        return f"CCRInstance(name={self.name}, port={self.port}, model={self.model_name})"


class CCRManager:
    """Manages multiple CCR instances"""

    # Pre-defined instance configurations
    INSTANCES = {
        "general": {
            "config": "ccr-general.json",
            "port": 3456,
            "model": "zai/glm-4.6",
            "description": "General purpose coding (Z.ai GLM-4.6)"
        },
        "fast": {
            "config": "ccr-fast.json",
            "port": 3457,
            "model": "xai/grok-beta",
            "description": "Ultra-fast responses (X.AI Grok)"
        },
        "reasoning": {
            "config": "ccr-reasoning.json",
            "port": 3458,
            "model": "deepseek/reasoner",
            "description": "Deep reasoning tasks (DeepSeek Reasoner)"
        },
        "code-review": {
            "config": "ccr-code-review.json",
            "port": 3459,
            "model": "deepseek/chat",
            "description": "Code review and analysis (DeepSeek Chat)"
        },
        "smart": {
            "config": "ccr-smart.json",
            "port": 3460,
            "model": "claude-sonnet-4",
            "description": "Highest quality (Claude Sonnet 4)"
        }
    }

    def __init__(self, configs_dir: str = None):
        """Initialize CCR Manager

        Args:
            configs_dir: Directory containing CCR config files
        """
        if configs_dir is None:
            # Default to configs directory in project root
            project_root = Path(__file__).parent.parent
            configs_dir = project_root / "configs"

        self.configs_dir = Path(configs_dir)
        self.instances: Dict[str, CCRInstance] = {}
        self.running_instances: Dict[str, subprocess.Popen] = {}

        # Load instances
        self._load_instances()

    def _load_instances(self):
        """Load instance configurations"""
        for name, config in self.INSTANCES.items():
            config_path = self.configs_dir / config["config"]
            if config_path.exists():
                self.instances[name] = CCRInstance(
                    name=name,
                    config_path=str(config_path),
                    port=config["port"],
                    model_name=config["model"]
                )

    def start_instance(self, instance_name: str) -> bool:
        """Start a specific CCR instance

        Args:
            instance_name: Name of the instance to start

        Returns:
            True if started successfully, False otherwise
        """
        if instance_name not in self.instances:
            print(f"❌ Instance '{instance_name}' not found")
            return False

        if instance_name in self.running_instances:
            print(f"⚠️  Instance '{instance_name}' is already running")
            return False

        instance = self.instances[instance_name]

        # Start CCR with specific config
        cmd = ["ccr", "start", "--config", instance.config_path]

        try:
            print(f"🚀 Starting {instance_name} on port {instance.port} ({instance.model_name})...")

            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait a bit for startup
            time.sleep(2)

            # Check if it's running
            if self._check_instance_health(instance.port):
                self.running_instances[instance_name] = process
                print(f"✅ {instance_name} started successfully")
                return True
            else:
                print(f"❌ {instance_name} failed to start")
                process.kill()
                return False

        except Exception as e:
            print(f"❌ Error starting {instance_name}: {e}")
            return False

    def stop_instance(self, instance_name: str) -> bool:
        """Stop a specific CCR instance

        Args:
            instance_name: Name of the instance to stop

        Returns:
            True if stopped successfully, False otherwise
        """
        if instance_name not in self.running_instances:
            print(f"⚠️  Instance '{instance_name}' is not running")
            return False

        try:
            instance = self.instances[instance_name]
            print(f"🛑 Stopping {instance_name}...")

            # Use ccr stop command
            subprocess.run(["ccr", "stop", "--port", str(instance.port)])

            # Remove from running instances
            del self.running_instances[instance_name]
            print(f"✅ {instance_name} stopped")
            return True

        except Exception as e:
            print(f"❌ Error stopping {instance_name}: {e}")
            return False

    def start_all(self) -> int:
        """Start all configured instances

        Returns:
            Number of instances successfully started
        """
        print("🚀 Starting all CCR instances...\n")
        success_count = 0

        for instance_name in self.instances.keys():
            if self.start_instance(instance_name):
                success_count += 1
            print()  # Blank line between instances

        print(f"✅ Started {success_count}/{len(self.instances)} instances")
        return success_count

    def stop_all(self) -> int:
        """Stop all running instances

        Returns:
            Number of instances successfully stopped
        """
        print("🛑 Stopping all CCR instances...\n")
        success_count = 0

        # Copy keys to avoid dict size change during iteration
        for instance_name in list(self.running_instances.keys()):
            if self.stop_instance(instance_name):
                success_count += 1
            print()

        print(f"✅ Stopped {success_count} instances")
        return success_count

    def status(self) -> Dict[str, Dict]:
        """Get status of all instances

        Returns:
            Dictionary with instance status information
        """
        status_info = {}

        for name, instance in self.instances.items():
            is_running = self._check_instance_health(instance.port)
            status_info[name] = {
                "running": is_running,
                "port": instance.port,
                "model": instance.model_name,
                "config": instance.config_path,
                "description": self.INSTANCES[name]["description"]
            }

        return status_info

    def print_status(self):
        """Print formatted status of all instances"""
        status = self.status()

        print("\n" + "="*80)
        print("CCR INSTANCE STATUS")
        print("="*80 + "\n")

        for name, info in status.items():
            status_icon = "🟢" if info["running"] else "🔴"
            status_text = "RUNNING" if info["running"] else "STOPPED"

            print(f"{status_icon} {name.upper():<15} [{status_text}]")
            print(f"   Port:        {info['port']}")
            print(f"   Model:       {info['model']}")
            print(f"   Description: {info['description']}")
            print()

    def _check_instance_health(self, port: int, timeout: int = 2) -> bool:
        """Check if a CCR instance is responding

        Args:
            port: Port number to check
            timeout: Request timeout in seconds

        Returns:
            True if instance is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"http://127.0.0.1:{port}/health",
                timeout=timeout
            )
            return response.status_code == 200
        except:
            return False

    def get_instance_port(self, instance_name: str) -> Optional[int]:
        """Get the port number for an instance

        Args:
            instance_name: Name of the instance

        Returns:
            Port number or None if instance not found
        """
        instance = self.instances.get(instance_name)
        return instance.port if instance else None

    def list_instances(self) -> List[str]:
        """Get list of available instance names

        Returns:
            List of instance names
        """
        return list(self.instances.keys())


if __name__ == "__main__":
    # Test the manager
    manager = CCRManager()
    manager.print_status()
