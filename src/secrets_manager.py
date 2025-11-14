"""
Bitwarden Secrets Manager Integration
Automatically retrieves API keys from Bitwarden Secrets Manager
"""

import os
from typing import Dict, Optional
from pathlib import Path

try:
    from bitwarden_sdk import BitwardenClient, DeviceType, client_settings_from_dict
except ImportError:
    BitwardenClient = None
    print("⚠️  Warning: bitwarden-sdk not installed. Run: pip install bitwarden-sdk")


class SecretsManager:
    """Manages API keys and secrets from Bitwarden Secrets Manager"""

    # Map of config key names to BWS secret names/IDs
    SECRET_MAPPINGS = {
        "ZAI_API_KEY": "ZAI_API_KEY",
        "XAI_API_KEY": "XAI_API_KEY",
        "OPENROUTER_API_KEY": "OPENROUTER_API_KEY",
        "GROQ_API_KEY": "GROQ_API_KEY",  # Legacy, optional
        "GEMINI_API_KEY": "GEMINI_API_KEY",
        "OPENAI_API_KEY": "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY"
    }

    def __init__(self, access_token: Optional[str] = None, project_id: Optional[str] = None):
        """Initialize Secrets Manager

        Args:
            access_token: BWS access token (defaults to BWS_ACCESS_TOKEN env var)
            project_id: BWS project ID to filter secrets (optional)
        """
        self.access_token = access_token or os.getenv("BWS_ACCESS_TOKEN")
        self.project_id = project_id or os.getenv("BWS_PROJECT_ID")
        self.client = None
        self._secrets_cache: Dict[str, str] = {}

        if not self.access_token:
            print("⚠️  BWS_ACCESS_TOKEN not set. Secrets Manager features disabled.")
            print("   Set via: export BWS_ACCESS_TOKEN='your-token-here'")
            return

        if BitwardenClient is None:
            print("⚠️  Bitwarden SDK not installed. Cannot fetch secrets from BWS.")
            return

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Bitwarden SDK client"""
        try:
            # Configure client settings
            settings = client_settings_from_dict({
                "api_url": os.getenv("BWS_API_URL", "https://api.bitwarden.com"),
                "identity_url": os.getenv("BWS_IDENTITY_URL", "https://identity.bitwarden.com"),
                "device_type": DeviceType.SDK
            })

            # Create client
            self.client = BitwardenClient(settings)

            # Authenticate
            self.client.access_token_login(self.access_token)

            print("✅ Connected to Bitwarden Secrets Manager")

        except Exception as e:
            print(f"❌ Failed to initialize Bitwarden SDK: {e}")
            self.client = None

    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a single secret value by name

        Args:
            secret_name: Name of the secret in BWS

        Returns:
            Secret value or None if not found
        """
        if not self.client:
            # Fallback to environment variable
            return os.getenv(secret_name)

        # Check cache first
        if secret_name in self._secrets_cache:
            return self._secrets_cache[secret_name]

        try:
            # List all secrets
            secrets_response = self.client.secrets().list(self.project_id)

            # Find secret by name
            for secret in secrets_response.data:
                if secret.key == secret_name:
                    # Get full secret details
                    secret_detail = self.client.secrets().get(secret.id)
                    value = secret_detail.value

                    # Cache it
                    self._secrets_cache[secret_name] = value
                    return value

            print(f"⚠️  Secret '{secret_name}' not found in BWS. Checking environment...")
            return os.getenv(secret_name)

        except Exception as e:
            print(f"❌ Error fetching secret '{secret_name}': {e}")
            return os.getenv(secret_name)

    def get_all_secrets(self) -> Dict[str, str]:
        """Get all configured API keys

        Returns:
            Dictionary mapping secret names to values
        """
        secrets = {}

        for key_name in self.SECRET_MAPPINGS.keys():
            value = self.get_secret(self.SECRET_MAPPINGS[key_name])
            if value:
                secrets[key_name] = value

        return secrets

    def inject_secrets_into_env(self):
        """Inject all secrets into environment variables

        This makes them available to child processes via os.getenv()
        """
        secrets = self.get_all_secrets()

        for key, value in secrets.items():
            os.environ[key] = value

        print(f"✅ Injected {len(secrets)} secrets into environment")

    def substitute_secrets_in_config(self, config_dict: dict) -> dict:
        """Replace secret placeholders in config with actual values

        Replaces ${SECRET_NAME} patterns with values from BWS

        Args:
            config_dict: Configuration dictionary (e.g., parsed CCR config)

        Returns:
            Config dict with secrets substituted
        """
        import re
        import json

        # Convert to JSON string for easier substitution
        config_str = json.dumps(config_dict)

        # Find all ${VAR_NAME} patterns
        pattern = r'\$\{([A-Z_]+)\}'

        def replace_secret(match):
            var_name = match.group(1)
            value = self.get_secret(var_name)
            if value:
                return value
            else:
                print(f"⚠️  Secret '{var_name}' not found, leaving placeholder")
                return match.group(0)

        # Replace all patterns
        config_str = re.sub(pattern, replace_secret, config_str)

        # Convert back to dict
        return json.loads(config_str)

    def list_available_secrets(self):
        """List all secrets available in BWS (for debugging)"""
        if not self.client:
            print("❌ BWS client not initialized")
            return

        try:
            secrets_response = self.client.secrets().list(self.project_id)

            print(f"\n📦 Available secrets in BWS:")
            print("─" * 60)

            for secret in secrets_response.data:
                project_info = f"(Project: {secret.project_id})" if secret.project_id else ""
                print(f"  • {secret.key} {project_info}")
                print(f"    ID: {secret.id}")

            print()

        except Exception as e:
            print(f"❌ Error listing secrets: {e}")


# Singleton instance for easy access
_secrets_manager_instance: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global SecretsManager instance

    Returns:
        SecretsManager instance
    """
    global _secrets_manager_instance

    if _secrets_manager_instance is None:
        _secrets_manager_instance = SecretsManager()

    return _secrets_manager_instance


# Example usage
if __name__ == "__main__":
    # Test the secrets manager
    sm = SecretsManager()

    # List available secrets
    sm.list_available_secrets()

    # Get specific secret
    zai_key = sm.get_secret("ZAI_API_KEY")
    if zai_key:
        print(f"✅ ZAI_API_KEY: {zai_key[:10]}...")

    # Get all secrets
    all_secrets = sm.get_all_secrets()
    print(f"\n✅ Retrieved {len(all_secrets)} secrets")

    # Inject into environment
    sm.inject_secrets_into_env()
