#!/usr/bin/env python3
"""Grant admin access to existing workspaces using admin API to discover them.

This script:
1. Uses admin API to list ALL workspaces in tenant (even ones you can't access)
2. Finds workspaces matching your solution configuration
3. Grants administrator access to the specified users/groups
"""

from __future__ import annotations

import argparse
import sys

import requests

from fabric_client import FabricClient, load_solution_config


class WorkspaceAccessGranter(FabricClient):
    """Grant workspace access using admin discovery."""

    def list_all_workspaces_admin(self) -> dict[str, str]:
        """List ALL workspaces in tenant using admin API.
        
        Returns:
            Dict mapping workspace name to workspace ID
            
        Note:
            Requires Fabric Administrator role
        """
        print("Fetching ALL tenant workspaces via admin API...")
        result = self._api_request("GET", "/admin/workspaces")
        
        workspaces = {}
        for workspace in result.get("value", []):
            workspaces[workspace["name"]] = workspace["id"]
        
        print(f"✓ Found {len(workspaces)} workspace(s) in tenant")
        return workspaces

    def add_workspace_user(
        self, 
        workspace_id: str, 
        identifier: str, 
        role: str = "Admin", 
        principal_type: str = "Group"
    ) -> bool:
        """Add a user or group to a workspace.
        
        Args:
            workspace_id: Workspace ID
            identifier: User email (UPN) or group name
            role: Workspace role (Admin, Member, Contributor, Viewer)
            principal_type: Type of principal (User, Group, App)
            
        Returns:
            True if successful, False otherwise
        """
        payload = {
            "identifier": identifier,
            "groupUserAccessRight": role,
            "principalType": principal_type
        }
        
        try:
            self._api_request(
                "POST",
                f"/workspaces/{workspace_id}/users",
                json_data=payload
            )
            print(f"  ✓ Added {principal_type.lower()} '{identifier}' as {role}")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                print(f"  ℹ️  {principal_type} '{identifier}' already has access")
                return True
            else:
                print(f"  ✗ Failed: HTTP {e.response.status_code}")
                if hasattr(e.response, 'text'):
                    print(f"    {e.response.text}")
                return False


def main() -> int:
    """Grant admin access to workspaces."""
    parser = argparse.ArgumentParser(
        description="Grant admin access to existing Fabric workspaces"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--workspace-type",
        choices=["ingestion", "lakehouse_processing", "lakehouse"],
        help="Only process workspaces of this type",
    )
    parser.add_argument(
        "--environment",
        choices=["dev", "tst", "prd"],
        help="Only process workspaces for this environment",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_solution_config()
    solution_name = config.get("solution_name", "main")
    workspaces_config = config.get("workspaces", {})
    alias = config.get("alias", {})

    # Initialize manager
    manager = WorkspaceAccessGranter()

    print(f"{'='*80}")
    print(f"Grant Workspace Access")
    print(f"Solution: {solution_name}")
    print(f"{'='*80}\n")

    print("Using workspace IDs from configuration...")
    print()
    
    total = 0
    success = 0
    failed = 0

    # Process each workspace in configuration
    for workspace_type, environments in workspaces_config.items():
        # Skip non-workspace entries
        if not isinstance(environments, dict):
            continue

        # Filter by workspace type if specified
        if args.workspace_type and workspace_type != args.workspace_type:
            continue

        print(f"\n--- Workspace type: {workspace_type} ---")

        for env, workspace_config in environments.items():
            # Skip non-environment entries
            if not isinstance(workspace_config, dict) or "id" not in workspace_config:
                continue

            # Filter by environment if specified
            if args.environment and env != args.environment:
                continue

            workspace_name = f"{solution_name}-{workspace_type}-{env}"
            workspace_id = workspace_config["id"]
            administrators = workspace_config.get("administrators", [])

            # Resolve administrators (replace alias references)
            resolved_admins = []
            for admin in administrators:
                if admin in alias:
                    resolved_admins.append(alias[admin])
                else:
                    resolved_admins.append(admin)

            total += 1
            print(f"\n[{total}] {workspace_name}")
            print(f"  Workspace ID: {workspace_id}")

            if not resolved_admins:
                print(f"  ℹ️  No administrators configured")
                success += 1
                continue

            print(f"  Administrators: {', '.join(resolved_admins)}")

            if args.dry_run:
                print(f"  [DRY RUN] Would add administrators")
                success += 1
                continue

            # Add each administrator
            workspace_success = True
            for admin in resolved_admins:
                # Determine principal type
                principal_type = "User" if "@" in admin else "Group"
                
                if not manager.add_workspace_user(
                    workspace_id, admin, role="Admin", principal_type=principal_type
                ):
                    workspace_success = False

            if workspace_success:
                success += 1
            else:
                failed += 1

    # Summary
    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  Total workspaces: {total}")
    print(f"  Successful: {success}")
    print(f"  Failed: {failed}")
    print(f"{'='*80}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
