#!/usr/bin/env python3
"""
Assign all workspaces to the correct Fabric capacity.

This script updates workspace capacity assignments using the Fabric REST API.
Requires Fabric Administrator or Workspace Admin permissions.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from azure.identity import AzureCliCredential
import requests

from fabric_client import FabricClient, load_solution_config


class WorkspaceCapacityManager(FabricClient):
    """Manage workspace capacity assignments."""

    def assign_workspace_to_capacity(
        self, workspace_id: str, capacity_id: str
    ) -> dict[str, Any]:
        """
        Assign a workspace to a capacity.

        Args:
            workspace_id: The workspace GUID
            capacity_id: The capacity GUID to assign

        Returns:
            API response data

        Raises:
            SystemExit: If assignment fails
        """
        payload = {"capacityId": capacity_id}

        print(f"Assigning workspace {workspace_id} to capacity {capacity_id}...")

        try:
            response = self._api_request(
                "PATCH", f"/workspaces/{workspace_id}", json_data=payload
            )
            print(f"  ✓ Successfully assigned workspace to capacity")
            return response
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                print(f"  ✗ Failed: Insufficient permissions")
                print(
                    f"    You need Admin access to workspace {workspace_id} or Fabric Administrator role"
                )
            elif e.response.status_code == 400:
                print(f"  ✗ Failed: Invalid capacity ID or workspace state")
                print(f"    Response: {e.response.text}")
            else:
                print(f"  ✗ Failed: HTTP {e.response.status_code}")
                print(f"    {e.response.text}")
            raise SystemExit(1) from e

    def get_workspace_info(self, workspace_id: str) -> dict[str, Any]:
        """
        Get workspace information using admin API.

        Args:
            workspace_id: The workspace GUID

        Returns:
            Workspace details
        """
        try:
            return self._api_request("GET", f"/admin/workspaces/{workspace_id}")
        except requests.HTTPError as e:
            print(f"  ⚠ Could not get workspace info: {e.response.status_code}")
            return {}


def main() -> None:
    """Assign all workspaces to the correct capacity."""
    parser = argparse.ArgumentParser(
        description="Assign all workspaces to the correct Fabric capacity"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
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
    manager = WorkspaceCapacityManager()

    print(f"{'='*80}")
    print(f"Fabric Workspace Capacity Assignment")
    print(f"Solution: {solution_name}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
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
            # Skip non-environment entries (like 'lakehouses', 'warehouses')
            if not isinstance(workspace_config, dict) or "id" not in workspace_config:
                continue

            # Filter by environment if specified
            if args.environment and env != args.environment:
                continue

            workspace_id = workspace_config["id"]
            capacity_id = workspace_config.get("capacity")

            if not capacity_id:
                print(f"⚠ Skipping {workspace_type}-{env}: No capacity configured")
                continue

            workspace_name = f"{solution_name}-{workspace_type}-{env}"
            total += 1

            print(f"\n[{total}] {workspace_name}")
            print(f"  Workspace ID: {workspace_id}")
            print(f"  Target Capacity: {capacity_id}")

            # Get current workspace info
            current_info = manager.get_workspace_info(workspace_id)
            if current_info:
                current_capacity = current_info.get("capacityId", "None")
                print(f"  Current Capacity: {current_capacity}")

                if current_capacity == capacity_id:
                    print(f"  → Already assigned to correct capacity, skipping")
                    success += 1
                    continue

            if args.dry_run:
                print(f"  → [DRY RUN] Would assign to capacity {capacity_id}")
                success += 1
            else:
                try:
                    manager.assign_workspace_to_capacity(workspace_id, capacity_id)
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

    if args.dry_run:
        print("\nDRY RUN completed. Run without --dry-run to apply changes.")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
