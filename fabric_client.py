"""Shared Fabric REST API client for workspace and lakehouse management."""

from __future__ import annotations

from pathlib import Path

import yaml
from azure.identity import AzureCliCredential
import requests

# Constants
REPO_ROOT = Path(__file__).resolve().parent
WORKSPACES_CONFIG = REPO_ROOT / "workspaces.yml"
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


def load_workspace_config(config_path: Path = WORKSPACES_CONFIG) -> dict:
    """Load workspace configuration from workspaces.yml."""
    if not config_path.is_file():
        raise SystemExit(f"Workspace config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return data
