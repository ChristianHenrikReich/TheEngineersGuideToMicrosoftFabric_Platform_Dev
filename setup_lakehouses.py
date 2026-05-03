"""Setup lakehouses in Fabric workspace using Fabric REST API.

This script creates lakehouse items in the Fabric workspace using the Fabric REST API.
Lakehouse names are read from workspaces.yml (data-driven configuration).

Prerequisites:
    - Azure CLI: az login
    - Authentication via AzureCliCredential

Local usage:
    az login
    python setup_lakehouses.py --environment dev

This will:
1. Read lakehouse names from workspaces.yml
2. Get the target workspace ID for the environment
3. Create each lakehouse using Fabric REST API
"""

from __future__ import annotations

import argparse
import sys

from fabric_client import FabricClient, load_workspace_config


class FabricLakehouseManager(FabricClient):
    """Manage Fabric lakehouses via REST API."""

    def list_lakehouses(self, workspace_id: str) -> dict[str, str]:
        """List all lakehouses in a workspace.
        
        Args:
            workspace_id: The workspace ID
            
        Returns:
            Dict mapping lakehouse display name to lakehouse ID
        """
        result = self._api_request("GET", f"/workspaces/{workspace_id}/lakehouses")
        lakehouses = {}
        
        for lakehouse in result.get("value", []):
            lakehouses[lakehouse["displayName"]] = lakehouse["id"]
        
        return lakehouses

    def create_lakehouse(self, workspace_id: str, lakehouse_name: str, description: str = "") -> str:
        """Create a new lakehouse in a workspace.
        
        Args:
            workspace_id: The workspace ID
            lakehouse_name: Lakehouse display name
            description: Optional lakehouse description
            
        Returns:
            Lakehouse ID
        """
        payload = {
            "displayName": lakehouse_name,
        }
        if description:
            payload["description"] = description
        
        result = self._api_request("POST", f"/workspaces/{workspace_id}/lakehouses", json_data=payload)
        lakehouse_id = result.get("id")
        
        if not lakehouse_id:
            raise RuntimeError(f"Failed to create lakehouse '{lakehouse_name}': no ID returned")
        
        print(f"✓ Created lakehouse: {lakehouse_name} ({lakehouse_id})")
        return lakehouse_id

    def get_or_create_lakehouse(self, workspace_id: str, lakehouse_name: str, description: str = "") -> tuple[str, bool]:
        """Get existing lakehouse ID or create new lakehouse.
        
        Args:
            workspace_id: The workspace ID
            lakehouse_name: Lakehouse display name
            description: Optional lakehouse description
            
        Returns:
            Tuple of (lakehouse_id, was_created)
        """
        lakehouses = self.list_lakehouses(workspace_id)
        
        if lakehouse_name in lakehouses:
            lakehouse_id = lakehouses[lakehouse_name]
            print(f"✓ Found existing lakehouse: {lakehouse_name} ({lakehouse_id})")
            return lakehouse_id, False
        
        lakehouse_id = self.create_lakehouse(workspace_id, lakehouse_name, description)
        return lakehouse_id, True


def get_workspace_id(environment: str) -> str:
    """Get the lakehouse workspace ID for the given environment."""
    config = load_workspace_config()
    
    if "lakehouse" not in config:
        raise SystemExit("'lakehouse' workspace not found in workspaces.yml")
    
    lakehouse_config = config["lakehouse"]
    
    if environment not in lakehouse_config:
        # Show only valid environment keys (filter out non-string values like 'lakehouses')
        valid_envs = [k for k, v in lakehouse_config.items() if isinstance(v, str)]
        raise SystemExit(f"Unknown environment '{environment}'. Use one of: {valid_envs}")
    
    workspace_id = lakehouse_config[environment]
    
    if not isinstance(workspace_id, str):
        raise SystemExit(f"Invalid workspace ID for environment '{environment}'")
    
    return workspace_id


def get_lakehouse_names() -> list[str]:
    """Get the list of lakehouse names from lakehouse_solution.yml."""
    config = load_workspace_config()
    
    if "lakehouse" not in config:
        raise SystemExit("'lakehouse' workspace not found in lakehouse_solution.yml")
    
    lakehouse_config = config["lakehouse"]
    if "lakehouses" not in lakehouse_config:
        raise SystemExit("'lakehouses' list not found under 'lakehouse' in lakehouse_solution.yml")
    
    lakehouses = lakehouse_config["lakehouses"]
    if not isinstance(lakehouses, list) or not lakehouses:
        raise SystemExit("'lakehouses' must be a non-empty list")
    
    return [str(name) for name in lakehouses]


def setup_lakehouses(environment: str) -> None:
    """Setup lakehouses in the Fabric workspace.
    
    Args:
        environment: Target environment (dev/tst/prd)
    """
    workspace_id = get_workspace_id(environment)
    lakehouse_names = get_lakehouse_names()
    manager = FabricLakehouseManager()
    
    print(f"\n{'='*70}")
    print(f"Setting up lakehouses for {environment.upper()} environment")
    print(f"Workspace ID: {workspace_id}")
    print(f"Lakehouses to create: {', '.join(lakehouse_names)}")
    print(f"{'='*70}\n")
    
    created_count = 0
    for lakehouse_name in lakehouse_names:
        description = f"{lakehouse_name.title()} lakehouse for {environment.upper()} environment"
        _, was_created = manager.get_or_create_lakehouse(workspace_id, lakehouse_name, description)
        if was_created:
            created_count += 1
    
    print(f"\n{'='*70}")
    print(f"Summary: {created_count} lakehouse(es) created")
    print(f"{'='*70}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Setup lakehouses in Fabric workspace using Fabric REST API."
    )
    parser.add_argument(
        "--environment", "-e",
        required=True,
        choices=["dev", "tst", "prd"],
        help="Target environment"
    )
    args = parser.parse_args(argv)
    
    try:
        setup_lakehouses(args.environment)
        return 0
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
