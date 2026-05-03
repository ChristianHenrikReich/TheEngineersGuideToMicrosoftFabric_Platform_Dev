"""Shared Fabric REST API client for workspace and lakehouse management."""

from __future__ import annotations

from pathlib import Path

import yaml
from azure.identity import AzureCliCredential
import requests

# Constants
REPO_ROOT = Path(__file__).resolve().parent
SOLUTION_CONFIG = REPO_ROOT / "lakehouse_solution.yml"
FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"


class FabricClient:
    """Base class for Fabric REST API operations."""

    def __init__(self, credential: AzureCliCredential | None = None):
        self.credential = credential or AzureCliCredential()
        self.token = None

    def _get_token(self) -> str:
        """Get Azure AD token for Fabric API."""
        if not self.token:
            token_obj = self.credential.get_token("https://api.fabric.microsoft.com/.default")
            self.token = token_obj.token
        return self.token

    def _api_request(self, method: str, endpoint: str, json_data: dict | None = None) -> dict:
        """Make authenticated request to Fabric API."""
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }
        
        url = f"{FABRIC_API_BASE}{endpoint}"
        response = requests.request(method, url, headers=headers, json=json_data)
        
        if response.status_code >= 400:
            print(f"API Error: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        if response.content:
            return response.json()
        return {}


def _resolve_aliases(data: dict | list | str, aliases: dict) -> dict | list | str:
    """Recursively resolve alias references in configuration data.
    
    Args:
        data: Configuration data (dict, list, or string)
        aliases: Alias mappings from the 'alias' section
        
    Returns:
        Configuration with all alias references replaced by actual values
    """
    if isinstance(data, dict):
        return {key: _resolve_aliases(value, aliases) for key, value in data.items()}
    elif isinstance(data, list):
        return [_resolve_aliases(item, aliases) for item in data]
    elif isinstance(data, str):
        # Replace alias reference with actual value if it matches
        return aliases.get(data, data)
    else:
        return data


def _preprocess_config(config_path: Path = SOLUTION_CONFIG) -> dict:
    """Load and preprocess configuration with alias resolution.
    
    Loads lakehouse_solution.yml and resolves any alias references.
    
    Returns:
        Preprocessed configuration with aliases resolved
    """
    if not config_path.is_file():
        raise SystemExit(f"Configuration not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    
    # Extract aliases if present
    aliases = data.get("alias", {})
    
    # Resolve aliases in the entire config (excluding the alias section itself)
    if aliases:
        resolved_data = {}
        for key, value in data.items():
            if key != "alias":
                resolved_data[key] = _resolve_aliases(value, aliases)
            else:
                resolved_data[key] = value  # Keep alias section as-is
        return resolved_data
    
    return data


def load_workspace_config(config_path: Path = SOLUTION_CONFIG) -> dict:
    """Load workspace configuration from lakehouse_solution.yml.
    
    Resolves aliases and returns the 'workspaces' section of the config.
    """
    data = _preprocess_config(config_path)

    if "workspaces" not in data:
        raise SystemExit(f"'workspaces' section not found in {config_path}")

    return data["workspaces"]


def load_solution_config(config_path: Path = SOLUTION_CONFIG) -> dict:
    """Load full lakehouse solution configuration.
    
    Resolves aliases and returns the complete config including solution_name and workspaces.
    """
    return _preprocess_config(config_path)
