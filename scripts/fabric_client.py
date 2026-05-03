"""Shared Fabric REST API client for workspace and lakehouse management."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from azure.identity import AzureCliCredential
import requests

# Constants
REPO_ROOT = Path(__file__).resolve().parent.parent
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


class FabricItemManager(FabricClient):
    """Generic manager for Fabric workspace items (lakehouses, warehouses, etc.).

    The item_type is the plural Fabric API path segment, e.g. "lakehouses",
    "warehouses". The singular form is derived for log messages.
    """

    def __init__(self, item_type: str, credential: AzureCliCredential | None = None):
        super().__init__(credential)
        self.item_type = item_type
        self.singular = item_type[:-1] if item_type.endswith("s") else item_type

    def list_items(self, workspace_id: str) -> dict[str, str]:
        """List all items of this type in a workspace.

        Returns:
            Dict mapping item display name to item ID.
        """
        result = self._api_request("GET", f"/workspaces/{workspace_id}/{self.item_type}")
        return {item["displayName"]: item["id"] for item in result.get("value", [])}

    def create_item(self, workspace_id: str, name: str, description: str = "") -> str:
        """Create a new item in a workspace."""
        payload: dict = {"displayName": name}
        if description:
            payload["description"] = description

        result = self._api_request(
            "POST", f"/workspaces/{workspace_id}/{self.item_type}", json_data=payload
        )
        item_id = result.get("id")
        if not item_id:
            raise RuntimeError(f"Failed to create {self.singular} '{name}': no ID returned")

        print(f"✓ Created {self.singular}: {name} ({item_id})")
        return item_id

    def get_or_create_item(
        self, workspace_id: str, name: str, description: str = ""
    ) -> tuple[str, bool]:
        """Get existing item ID or create a new item.

        Returns:
            Tuple of (item_id, was_created).
        """
        items = self.list_items(workspace_id)
        if name in items:
            print(f"✓ Found existing {self.singular}: {name} ({items[name]})")
            return items[name], False

        return self.create_item(workspace_id, name, description), True


def _resolve_aliases(data: dict | list | str, aliases: dict) -> dict | list | str:
    """Recursively resolve alias references in configuration data."""
    if isinstance(data, dict):
        return {key: _resolve_aliases(value, aliases) for key, value in data.items()}
    elif isinstance(data, list):
        return [_resolve_aliases(item, aliases) for item in data]
    elif isinstance(data, str):
        return aliases.get(data, data)
    else:
        return data


def _preprocess_config(config_path: Path = SOLUTION_CONFIG) -> dict:
    """Load and preprocess configuration with alias resolution."""
    if not config_path.is_file():
        raise SystemExit(f"Configuration not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    aliases = data.get("alias", {})
    if aliases:
        resolved_data = {}
        for key, value in data.items():
            if key != "alias":
                resolved_data[key] = _resolve_aliases(value, aliases)
            else:
                resolved_data[key] = value
        return resolved_data

    return data


def load_workspace_config(config_path: Path = SOLUTION_CONFIG) -> dict:
    """Load workspace configuration from lakehouse_solution.yml (aliases resolved)."""
    data = _preprocess_config(config_path)
    if "workspaces" not in data:
        raise SystemExit(f"'workspaces' section not found in {config_path}")
    return data["workspaces"]


def load_solution_config(config_path: Path = SOLUTION_CONFIG) -> dict:
    """Load full lakehouse solution configuration (aliases resolved)."""
    return _preprocess_config(config_path)


def get_workspace_id(
    workspace_type: str,
    environment: str,
    *,
    allow_env_override: bool = False,
    config: dict | None = None,
) -> str:
    """Get the workspace ID for a workspace type and environment.

    Args:
        workspace_type: Workspace type key (e.g. 'lakehouse', 'ingestion').
        environment: Target environment (dev/tst/prd).
        allow_env_override: If True, check for env var override
            ``{WORKSPACE_TYPE}_{ENVIRONMENT}_WORKSPACE_ID``.
        config: Optional preloaded workspace config.
    """
    if allow_env_override:
        env_var_name = f"{workspace_type.upper()}_{environment.upper()}_WORKSPACE_ID"
        if env_var_name in os.environ:
            return os.environ[env_var_name]

    if config is None:
        config = load_workspace_config()

    if workspace_type not in config:
        raise SystemExit(f"Workspace type '{workspace_type}' not found in {SOLUTION_CONFIG}")

    workspace_config = config[workspace_type]
    if environment not in workspace_config:
        valid_envs = [
            k for k, v in workspace_config.items() if isinstance(v, dict) and "id" in v
        ]
        raise SystemExit(
            f"Unknown environment '{environment}' for '{workspace_type}'. "
            f"Use one of: {valid_envs}"
        )

    env_config = workspace_config[environment]
    if not isinstance(env_config, dict) or "id" not in env_config:
        raise SystemExit(
            f"Invalid workspace configuration for {workspace_type}/{environment}. "
            f"Expected dict with 'id' key."
        )

    return env_config["id"]


def get_workspace_item_names(workspace_type: str, item_key: str) -> list[str]:
    """Get the list of item names declared under a workspace type.

    For example: workspace_type='lakehouse', item_key='lakehouses' returns
    the list of lakehouse names declared in lakehouse_solution.yml.
    """
    config = load_workspace_config()
    if workspace_type not in config:
        raise SystemExit(f"'{workspace_type}' workspace not found in lakehouse_solution.yml")

    workspace_config = config[workspace_type]
    if item_key not in workspace_config:
        raise SystemExit(
            f"'{item_key}' list not found under '{workspace_type}' in lakehouse_solution.yml"
        )

    items = workspace_config[item_key]
    if not isinstance(items, list) or not items:
        raise SystemExit(f"'{item_key}' must be a non-empty list")

    return [str(name) for name in items]


def setup_workspace_items(
    item_type: str,
    workspace_type: str,
    environment: str,
    item_key: str | None = None,
) -> None:
    """Setup items of a given type in the target workspace.

    Args:
        item_type: Fabric API plural item type, e.g. 'lakehouses', 'warehouses'.
        workspace_type: Workspace type that hosts the items (e.g. 'lakehouse').
        environment: Target environment (dev/tst/prd).
        item_key: Config key listing the item names. Defaults to ``item_type``.
    """
    item_key = item_key or item_type
    workspace_id = get_workspace_id(workspace_type, environment)
    item_names = get_workspace_item_names(workspace_type, item_key)
    manager = FabricItemManager(item_type)

    print(f"\n{'=' * 70}")
    print(f"Setting up {item_type} for {environment.upper()} environment")
    print(f"Workspace ID: {workspace_id}")
    print(f"{item_type.title()} to create: {', '.join(item_names)}")
    print(f"{'=' * 70}\n")

    created_count = 0
    for name in item_names:
        description = f"{name.title()} {manager.singular} for {environment.upper()} environment"
        _, was_created = manager.get_or_create_item(workspace_id, name, description)
        if was_created:
            created_count += 1

    print(f"\n{'=' * 70}")
    print(f"Summary: {created_count} {manager.singular}(s) created")
    print(f"{'=' * 70}")

