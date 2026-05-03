"""Deploy Fabric items to workspaces using fabric-cicd.

Local usage:
    az login
    python deploy.py --workspace ingestion --environment dev
    python deploy.py --workspace lakehouse --environment prod

CI usage: a service principal credential is passed in via env vars; see
.github/workflows/deploy-fabric.yml and .azure_devops/azure-pipelines.yml.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from azure.identity import AzureCliCredential
from fabric_cicd import (
    FabricWorkspace,
    publish_all_items,
    unpublish_all_orphan_items,
)

from fabric_client import get_workspace_id

REPO_ROOT = Path(__file__).resolve().parent
SOLUTION_ROOT = REPO_ROOT / "solution"

# Valid workspace types
WORKSPACE_TYPES = ["ingestion", "lakehouse_processing", "lakehouse"]

# Items in scope for publish. Add types here as the solution grows.
ITEM_TYPE_IN_SCOPE = [
    "Notebook",
    "DataPipeline",
    "Environment",
    "Lakehouse",
]


def get_repository_directory(workspace_type: str) -> Path:
    """Get the repository directory for a workspace type."""
    directory = SOLUTION_ROOT / workspace_type
    if not directory.is_dir():
        raise SystemExit(f"Repository directory not found: {directory}")
    return directory


def deploy(workspace_type: str, environment: str, *, unpublish_orphans: bool) -> None:
    """Deploy artifacts from a workspace folder to a Fabric workspace."""
    workspace_id = get_workspace_id(workspace_type, environment, allow_env_override=True)
    repository_directory = get_repository_directory(workspace_type)
    fabric_env = environment.upper()  # parameter.yml keys are DEV/TST/PRD

    print(f"Deploying {workspace_type} workspace to {fabric_env}")
    print(f"Workspace ID: {workspace_id}")
    print(f"Repository directory: {repository_directory}")

    workspace = FabricWorkspace(
        workspace_id=workspace_id,
        environment=fabric_env,
        repository_directory=str(repository_directory),
        item_type_in_scope=ITEM_TYPE_IN_SCOPE,
        token_credential=AzureCliCredential(),
    )

    publish_all_items(workspace)
    if unpublish_orphans:
        unpublish_all_orphan_items(workspace)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deploy Fabric items to a target workspace.")
    parser.add_argument(
        "--workspace", "-w",
        required=True,
        choices=WORKSPACE_TYPES,
        help="Workspace type to deploy"
    )
    parser.add_argument(
        "--environment", "-e",
        required=True,
        choices=["dev", "tst", "prd"],
        help="Target environment"
    )
    parser.add_argument(
        "--no-unpublish-orphans",
        action="store_true",
        help="Skip unpublishing items that exist in the workspace but not in the repo.",
    )
    args = parser.parse_args(argv)

    deploy(args.workspace, args.environment, unpublish_orphans=not args.no_unpublish_orphans)
    return 0


if __name__ == "__main__":
    sys.exit(main())
