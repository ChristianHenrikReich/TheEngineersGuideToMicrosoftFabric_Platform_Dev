"""Setup warehouses in Fabric workspace using Fabric REST API.

This script creates warehouse items in the Fabric workspace using the Fabric REST API.
Warehouse names are read from lakehouse_solution.yml (data-driven configuration).

Prerequisites:
    - Azure CLI: az login
    - Authentication via AzureCliCredential

Local usage:
    az login
    python setup_warehouses.py --environment dev

This will:
1. Read warehouse names from lakehouse_solution.yml
2. Get the target workspace ID for the environment
3. Create each warehouse using Fabric REST API
"""

from __future__ import annotations

import argparse
import sys

from fabric_client import FabricClient, load_workspace_config


class FabricWarehouseManager(FabricClient):
    """Manage Fabric warehouses via REST API."""

    def list_warehouses(self, workspace_id: str) -> dict[str, str]:
        """List all warehouses in a workspace.
        
        Args:
            workspace_id: The workspace ID
            
        Returns:
            Dict mapping warehouse display name to warehouse ID
        """
        result = self._api_request("GET", f"/workspaces/{workspace_id}/warehouses")
        warehouses = {}
        
        for warehouse in result.get("value", []):
            warehouses[warehouse["displayName"]] = warehouse["id"]
        
        return warehouses

    def create_warehouse(self, workspace_id: str, warehouse_name: str, description: str = "") -> str:
        """Create a new warehouse in a workspace.
        
        Args:
            workspace_id: The workspace ID
            warehouse_name: Warehouse display name
            description: Optional warehouse description
            
        Returns:
            Warehouse ID
        """
        payload = {
            "displayName": warehouse_name,
        }
        if description:
            payload["description"] = description
        
        result = self._api_request("POST", f"/workspaces/{workspace_id}/warehouses", json_data=payload)
        warehouse_id = result.get("id")
        
        if not warehouse_id:
            raise RuntimeError(f"Failed to create warehouse '{warehouse_name}': no ID returned")
        
        print(f"✓ Created warehouse: {warehouse_name} ({warehouse_id})")
        return warehouse_id

    def get_or_create_warehouse(self, workspace_id: str, warehouse_name: str, description: str = "") -> tuple[str, bool]:
        """Get existing warehouse ID or create new warehouse.
        
        Args:
            workspace_id: The workspace ID
            warehouse_name: Warehouse display name
            description: Optional warehouse description
            
        Returns:
            Tuple of (warehouse_id, was_created)
        """
        warehouses = self.list_warehouses(workspace_id)
        
        if warehouse_name in warehouses:
            warehouse_id = warehouses[warehouse_name]
            print(f"✓ Found existing warehouse: {warehouse_name} ({warehouse_id})")
            return warehouse_id, False
        
        warehouse_id = self.create_warehouse(workspace_id, warehouse_name, description)
        return warehouse_id, True


def get_workspace_id(environment: str) -> str:
    """Get the lakehouse workspace ID for the given environment."""
    config = load_workspace_config()
    
    if "lakehouse" not in config:
        raise SystemExit("'lakehouse' workspace not found in lakehouse_solution.yml")
    
    lakehouse_config = config["lakehouse"]
    
    if environment not in lakehouse_config:
        # Show only valid environment keys (filter out non-string values like 'warehouses')
        valid_envs = [k for k, v in lakehouse_config.items() if isinstance(v, str)]
        raise SystemExit(f"Unknown environment '{environment}'. Use one of: {valid_envs}")
    
    workspace_id = lakehouse_config[environment]
    
    if not isinstance(workspace_id, str):
        raise SystemExit(f"Invalid workspace ID for environment '{environment}'")
    
    return workspace_id


def get_warehouse_names() -> list[str]:
    """Get the list of warehouse names from lakehouse_solution.yml."""
    config = load_workspace_config()
    
    if "lakehouse" not in config:
        raise SystemExit("'lakehouse' workspace not found in lakehouse_solution.yml")
    
    lakehouse_config = config["lakehouse"]
    if "warehouses" not in lakehouse_config:
        raise SystemExit("'warehouses' list not found under 'lakehouse' in lakehouse_solution.yml")
    
    warehouses = lakehouse_config["warehouses"]
    if not isinstance(warehouses, list) or not warehouses:
        raise SystemExit("'warehouses' must be a non-empty list")
    
    return [str(name) for name in warehouses]


def setup_warehouses(environment: str) -> None:
    """Setup warehouses in the Fabric workspace.
    
    Args:
        environment: Target environment (dev/tst/prd)
    """
    workspace_id = get_workspace_id(environment)
    warehouse_names = get_warehouse_names()
    manager = FabricWarehouseManager()
    
    print(f"\n{'='*70}")
    print(f"Setting up warehouses for {environment.upper()} environment")
    print(f"Workspace ID: {workspace_id}")
    print(f"Warehouses to create: {', '.join(warehouse_names)}")
    print(f"{'='*70}\n")
    
    created_count = 0
    for warehouse_name in warehouse_names:
        description = f"{warehouse_name.title()} warehouse for {environment.upper()} environment"
        _, was_created = manager.get_or_create_warehouse(workspace_id, warehouse_name, description)
        if was_created:
            created_count += 1
    
    print(f"\n{'='*70}")
    print(f"Summary: {created_count} warehouse(s) created")
    print(f"{'='*70}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Setup warehouses in Fabric workspace using Fabric REST API."
    )
    parser.add_argument(
        "--environment", "-e",
        required=True,
        choices=["dev", "tst", "prd"],
        help="Target environment"
    )
    args = parser.parse_args(argv)
    
    try:
        setup_warehouses(args.environment)
        return 0
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
