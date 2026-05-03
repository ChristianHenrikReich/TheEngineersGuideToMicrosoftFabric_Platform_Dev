"""Setup Fabric workspaces and update lakehouse_solution.yml with their IDs.

This script ensures all Fabric workspaces match the configuration defined in
lakehouse_solution.yml, treating the YAML file as the source of truth.

For each workspace defined in the configuration:
- Creates the workspace if it doesn't exist
- Updates capacity assignment if different from config
- Ensures administrators have access
- Updates lakehouse_solution.yml with actual workspace IDs

Workspace naming convention: {solution_name}-{workspace_type}-{environment}
Solution name: main
Examples: main-ingestion-dev, main-lakehouse-prd, main-lakehouse_processing-tst

Local usage:
    az login
    python scripts/setup_workspaces.py

This will:
1. List all accessible Fabric workspaces
2. Create missing workspaces based on lakehouse_solution.yml
3. Update existing workspaces to match configuration (capacity, administrators)
4. Update lakehouse_solution.yml with actual workspace IDs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests
import yaml

from fabric_client import FabricClient, load_workspace_config, load_solution_config, SOLUTION_CONFIG


class FabricWorkspaceManager(FabricClient):
    """Manage Fabric workspaces via REST API."""

    def list_workspaces(self) -> dict[str, str]:
        """List all accessible workspaces.
        
        Returns:
            Dict mapping workspace name to workspace ID
        """
        result = self._api_request("GET", "/workspaces")
        workspaces = {}
        
        for workspace in result.get("value", []):
            workspaces[workspace["displayName"]] = workspace["id"]
        
        return workspaces

    def create_workspace(self, name: str, description: str = "", capacity_id: str | None = None) -> str:
        """Create a new workspace.
        
        Args:
            name: Workspace display name
            description: Optional workspace description
            capacity_id: Optional Fabric capacity ID to assign workspace to
            
        Returns:
            Workspace ID
            
        Raises:
            RuntimeError: If workspace creation fails or returns no ID
        """
        payload = {
            "displayName": name,
        }
        if description:
            payload["description"] = description
        if capacity_id and capacity_id != "REPLACE_WITH_YOUR_CAPACITY_ID":
            payload["capacityId"] = capacity_id
            print(f"  → Assigning to capacity: {capacity_id}")
        
        print(f"  → Calling Fabric API to create workspace '{name}'...")
        
        try:
            result = self._api_request("POST", "/workspaces", json_data=payload)
        except requests.exceptions.HTTPError as e:
            print(f"\n❌ FAILED to create workspace '{name}'")
            print(f"   HTTP Error: {e}")
            
            # Check for specific error code in response
            if e.response is not None and e.response.status_code == 409:
                try:
                    error_data = e.response.json()
                    if error_data.get("errorCode") == "WorkspaceNameAlreadyExists":
                        print(f"\n   ⚠️  WORKSPACE NAME ALREADY EXISTS")
                        print(f"   The workspace '{name}' exists in the tenant but you can't see it.")
                        print(f"   This usually means:")
                        print(f"   1. Workspace exists from a previous creation")
                        print(f"   2. Service principal lacks Viewer/Member access to the existing workspace")
                        print(f"\n   Solutions:")
                        print(f"   → Grant service principal 'Viewer' or 'Member' role on the existing workspace")
                        print(f"   → Or delete the existing workspace and run this script again")
                        print(f"   → Or rename the workspace in Fabric portal and run this script again")
                        raise SystemExit(1)
                except (ValueError, AttributeError):
                    pass
            
            print(f"   This usually means:")
            print(f"   1. Service principal lacks 'Workspace creation' permission")
            print(f"   2. Tenant setting 'Service principals can use Fabric APIs' is disabled")
            print(f"   3. Service principal is not in an enabled security group")
            if capacity_id:
                print(f"   4. Invalid capacity ID or no permission on capacity")
            raise
        
        workspace_id = result.get("id")
        
        if not workspace_id:
            raise RuntimeError(f"Failed to create workspace '{name}': no ID returned from API")
        
        print(f"✓ Created workspace: {name} ({workspace_id})")
        return workspace_id

    def get_workspace_details(self, workspace_id: str) -> dict:
        """Get workspace details including current capacity.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            Workspace details dict with capacityId
        """
        # Use admin API because regular API doesn't return capacityId
        return self._api_request("GET", f"/admin/workspaces/{workspace_id}")

    def update_workspace_capacity(self, workspace_id: str, capacity_id: str) -> None:
        """Update workspace capacity assignment.
        
        Args:
            workspace_id: Workspace ID
            capacity_id: Target capacity ID
            
        Raises:
            requests.HTTPError: If API call fails
        """
        payload = {"capacityId": capacity_id}
        
        try:
            # Use assignToCapacity endpoint (returns 202 Accepted)
            self._api_request(
                "POST",
                f"/workspaces/{workspace_id}/assignToCapacity",
                json_data=payload
            )
            print(f"  ✓ Updated capacity to {capacity_id}")
        except requests.exceptions.HTTPError as e:
            print(f"  ⚠️  Failed to update capacity: {e}")
            if e.response is not None:
                print(f"     Status: {e.response.status_code}")
                print(f"     Response: {e.response.text}")
            # Don't fail the whole process for capacity update failures

    def add_workspace_user(self, workspace_id: str, identifier: str, role: str = "Admin", principal_type: str = "Group") -> None:
        """Add a user or group to a workspace using role assignments.
        
        Args:
            workspace_id: Workspace ID
            identifier: User email (UPN), group Object ID, or app client ID
            role: Workspace role (Admin, Member, Contributor, Viewer)
            principal_type: Type of principal (User, Group, ServicePrincipal)
            
        Raises:
            requests.HTTPError: If API call fails
        """
        payload = {
            "principal": {
                "id": identifier,
                "type": principal_type
            },
            "role": role
        }
        
        try:
            self._api_request(
                "POST",
                f"/workspaces/{workspace_id}/roleAssignments",
                json_data=payload
            )
            print(f"  ✓ Added {principal_type.lower()} '{identifier}' as {role}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                # User/group already has access
                print(f"  ℹ️  {principal_type} '{identifier}' already has access")
            else:
                print(f"  ⚠️  Failed to add {principal_type.lower()} '{identifier}': {e}")
                # Don't fail the whole process for admin assignment failures

    def get_or_create_workspace(self, name: str, description: str = "", capacity_id: str | None = None, administrators: list[str] | None = None) -> str:
        """Get existing workspace or create new workspace, updating to match config.
        
        Args:
            name: Workspace display name
            description: Optional workspace description
            capacity_id: Optional Fabric capacity ID to assign workspace to
            administrators: Optional list of admin users/groups to add
            
        Returns:
            Workspace ID
        """
        workspaces = self.list_workspaces()
        
        if name in workspaces:
            workspace_id = workspaces[name]
            print(f"✓ Found existing workspace: {name} ({workspace_id})")
            
            # Update workspace to match configuration (source of truth)
            print(f"  → Checking workspace configuration...")
            
            # Check and update capacity if specified and different
            if capacity_id and capacity_id != "REPLACE_WITH_YOUR_CAPACITY_ID":
                try:
                    details = self.get_workspace_details(workspace_id)
                    current_capacity = details.get("capacityId")
                    
                    if current_capacity != capacity_id:
                        print(f"  → Capacity mismatch: {current_capacity} → {capacity_id}")
                        self.update_workspace_capacity(workspace_id, capacity_id)
                    else:
                        print(f"  ✓ Capacity already correct: {capacity_id}")
                except Exception as e:
                    print(f"  ⚠️  Could not verify/update capacity: {e}")
            
            # Ensure administrators have access
            if administrators:
                print(f"  → Ensuring administrators have access...")
                for admin in administrators:
                    principal_type = "User" if "@" in admin else "Group"
                    self.add_workspace_user(workspace_id, admin, role="Admin", principal_type=principal_type)
            
            return workspace_id
        
        # Create new workspace
        workspace_id = self.create_workspace(name, description, capacity_id)
        
        # Add administrators to newly created workspace
        if administrators:
            print(f"  → Adding administrators...")
            for admin in administrators:
                principal_type = "User" if "@" in admin else "Group"
                self.add_workspace_user(workspace_id, admin, role="Admin", principal_type=principal_type)
        
        return workspace_id


def save_workspace_config(config: dict, solution_name: str, config_path: Path = SOLUTION_CONFIG) -> None:
    """Save workspace configuration to lakehouse_solution.yml.
    
    Preserves non-environment properties like 'lakehouses' lists.
    Structure: each environment is {id: workspace_id, capacity: capacity_id}
    """
    full_config = {
        "solution_name": solution_name,
        "workspaces": config
    }
    
    with config_path.open("w", encoding="utf-8") as fh:
        # Write header comment
        fh.write("# Fabric lakehouse solution configuration\n")
        fh.write("# Auto-generated by setup_workspaces.py\n")
        fh.write("# Workspace naming: {solution_name}-{workspace_type}-{environment}\n")
        fh.write("# Values may be overridden at runtime via env vars.\n\n")
        
        # Write YAML content
        yaml.safe_dump(
            full_config,
            fh,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    
    print(f"\n✓ Updated {config_path}")


def setup_workspaces(dry_run: bool = False) -> None:
    """Setup all workspaces and update configuration."""
    # Load current workspace configuration
    full_config = load_solution_config()
    solution_name = full_config.get("solution_name", "main")
    config = full_config.get("workspaces", {})
    
    manager = FabricWorkspaceManager()
    
    print("Setting up Fabric workspaces...")
    print(f"Configuration file: {SOLUTION_CONFIG}\n")
    
    # Fetch existing workspaces from Fabric API
    print("Fetching existing workspaces from Fabric...")
    try:
        existing_workspaces = manager.list_workspaces()
        print(f"Found {len(existing_workspaces)} existing workspace(s)")
        
        if existing_workspaces:
            print("Existing workspaces:")
            for name, ws_id in list(existing_workspaces.items())[:5]:
                print(f"  - {name} ({ws_id})")
            if len(existing_workspaces) > 5:
                print(f"  ... and {len(existing_workspaces) - 5} more")
        else:
            print("\n⚠️  WARNING: No workspaces found!")
            print("   This could mean:")
            print("   1. Service principal can't list workspaces (permission issue)")
            print("   2. No workspaces exist yet (expected on first run)")
            print("   3. Service principal doesn't have Viewer access to any workspace\n")
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ FAILED to list workspaces from Fabric API")
        print(f"   HTTP Error: {e}")
        print(f"   Check service principal permissions!")
        raise
    
    print()
    updated = False
    
    for workspace_type, environments in config.items():
        if not isinstance(environments, dict):
            continue  # Skip non-workspace entries
        
        print(f"\n--- Workspace type: {workspace_type} ---")
        
        for environment, env_config in environments.items():
            # Skip non-environment properties (e.g., 'lakehouses', 'warehouses' lists)
            if not isinstance(env_config, dict):
                continue
            if 'id' not in env_config:
                continue  # Skip if not a proper workspace config
            
            # Generate workspace name following convention
            workspace_name = f"{solution_name}-{workspace_type}-{environment}"
            
            # Get desired configuration (source of truth)
            current_id = env_config.get('id', '')
            capacity_id = env_config.get('capacity')
            administrators = env_config.get('administrators', [])
            
            print(f"\n{workspace_name}:")
            print(f"  Config ID: {current_id}")
            if capacity_id and capacity_id != "REPLACE_WITH_YOUR_CAPACITY_ID":
                print(f"  Capacity: {capacity_id}")
            if administrators:
                print(f"  Administrators: {', '.join(administrators)}")
            
            if not dry_run:
                # Get or create workspace and update to match configuration
                description = f"{workspace_type.replace('_', ' ').title()} workspace for {environment.upper()} environment"
                
                workspace_id = manager.get_or_create_workspace(
                    workspace_name, 
                    description, 
                    capacity_id,
                    administrators=administrators
                )
                
                # Update config if ID changed
                if current_id != workspace_id:
                    config[workspace_type][environment]['id'] = workspace_id
                    updated = True
            else:
                # Dry run - show what would happen
                if workspace_name in existing_workspaces:
                    actual_id = existing_workspaces[workspace_name]
                    print(f"  [DRY RUN] Would verify/update existing workspace: {actual_id}")
                    if capacity_id and capacity_id != "REPLACE_WITH_YOUR_CAPACITY_ID":
                        print(f"  [DRY RUN] Would ensure capacity is: {capacity_id}")
                    if administrators:
                        print(f"  [DRY RUN] Would ensure administrators: {', '.join(administrators)}")
                else:
                    print(f"  [DRY RUN] Would create workspace: {workspace_name}")
                    if capacity_id and capacity_id != "REPLACE_WITH_YOUR_CAPACITY_ID":
                        print(f"  [DRY RUN] Would assign capacity: {capacity_id}")
                    if administrators:
                        print(f"  [DRY RUN] Would add administrators: {', '.join(administrators)}")
    
    # Save updated configuration
    if updated and not dry_run:
        save_workspace_config(config, solution_name)
        print("\n✅ All workspaces configured successfully!")
    elif dry_run:
        print("\n✅ Dry run completed. Use without --dry-run to apply changes.")
    else:
        print("\n✅ All workspaces already configured.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Setup Fabric workspaces and update lakehouse_solution.yml"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args(argv)

    try:
        setup_workspaces(dry_run=args.dry_run)
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
