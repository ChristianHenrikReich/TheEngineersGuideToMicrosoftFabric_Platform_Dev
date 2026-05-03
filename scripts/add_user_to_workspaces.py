#!/usr/bin/env python3
"""
Add a user as Admin to all workspaces.

This script uses the Fabric Admin API to add users to workspaces.
Requires Fabric Administrator permissions.
"""

from __future__ import annotations

import argparse
import sys

from azure.identity import AzureCliCredential
import requests

from fabric_client import FabricClient, load_solution_config


class WorkspaceUserManager(FabricClient):
    """Manage workspace user access."""

    def add_workspace_user(
        self, workspace_id: str, user_email: str, role: str = "Admin"
    ) -> dict:
        """
        Add a user to a workspace.

        Args:
            workspace_id: The workspace GUID
            user_email: User's email address (UPN)
            role: Workspace role (Admin, Member, Contributor, Viewer)

        Returns:
            API response

        Raises:
            SystemExit: If operation fails
        """
        # First, we need to get the user's object ID
        # Note: This requires the user object ID, not email
        # For now, we'll try the direct approach
        
        payload = {
            "identifier": user_email,
            "groupUserAccessRight": role,
            "principalType": "User"
        }

        print(f"Adding {user_email} as {role} to workspace {workspace_id}...")

        try:
            # Try regular API endpoint
            response = self._api_request(
                "POST", 
                f"/workspaces/{workspace_id}/users",
                json_data=payload
            )
            print(f"  ✓ Successfully added user")
            return response
        except requests.HTTPError as e:
            print(f"  ✗ Failed: HTTP {e.response.status_code}")
            print(f"    {e.response.text}")
            
            # Note: Admin API doesn't support adding users directly
            # User must be added via regular API (requires workspace access)
            # or via Fabric Portal UI
            raise SystemExit(1) from e


def main() -> None:
    """Add user to all workspaces."""
    parser = argparse.ArgumentParser(
        description="Add a user as Admin to all Fabric workspaces"
    )
    parser.add_argument(
        "email",
        help="User email address (UPN) to add as admin",
    )
    parser.add_argument(
        "--role",
        choices=["Admin", "Member", "Contributor", "Viewer"],
        default="Admin",
        help="Workspace role to assign (default: Admin)",
    )
    parser.add_argument(
        "--workspace-type",
        choices=["ingestion", "lakehouse_processing", "lakehouse"],
        help="Only update workspaces of this type",
    )
    parser.add_argument(
        "--environment",
        choices=["dev", "tst", "prd"],
        help="Only update workspaces for this environment",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_solution_config()
    solution_name = config.get("solution_name", "main")

    # Initialize manager
    manager = WorkspaceUserManager()

    print(f"{'='*80}")
    print(f"Fabric Workspace User Management")
    print(f"Solution: {solution_name}")
    print(f"User: {args.email}")
    print(f"Role: {args.role}")
    print(f"{'='*80}\n")

    # Get workspaces configuration
    workspaces_config = config.get("workspaces", {})

    total = 0
    success = 0
    failed = 0

    for workspace_type, environments in workspaces_config.items():
        # Skip non-workspace entries
        if not isinstance(environments, dict):
            continue

        # Filter by workspace type if specified
        if args.workspace_type and workspace_type != args.workspace_type:
            continue

        for env, workspace_config in environments.items():
            # Skip non-environment entries
            if not isinstance(workspace_config, dict) or "id" not in workspace_config:
                continue

            # Filter by environment if specified
            if args.environment and env != args.environment:
                continue

            workspace_id = workspace_config["id"]
            workspace_name = f"{solution_name}-{workspace_type}-{env}"
            total += 1

            print(f"\n[{total}] {workspace_name}")
            print(f"  Workspace ID: {workspace_id}")

            try:
                manager.add_workspace_user(workspace_id, args.email, args.role)
                success += 1
            except SystemExit:
                failed += 1
                if input("\n  Continue with remaining workspaces? [y/N] ").lower() != "y":
                    print("\nAborted by user")
                    sys.exit(1)

    # Summary
    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  Total workspaces: {total}")
    print(f"  Successful: {success}")
    print(f"  Failed: {failed}")
    print(f"{'='*80}")

    if failed > 0:
        print("\n⚠️  Some operations failed.")
        print("Alternative: Use the Fabric Portal to manually add yourself to workspaces:")
        print("  1. Go to https://app.fabric.microsoft.com/")
        print("  2. Find each workspace")
        print("  3. Workspace settings → Manage access → Add people")
        
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
