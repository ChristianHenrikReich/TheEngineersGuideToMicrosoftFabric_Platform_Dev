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
import os
import sys
from pathlib import Path

import yaml
from azure.identity import AzureCliCredential
from fabric_cicd import (
    FabricWorkspace,
    publish_all_items,
    unpublish_all_orphan_items,
)

REPO_ROOT = Path(__file__).resolve().parent
SOLUTION_ROOT = REPO_ROOT / "solution"
WORKSPACES_CONFIG = REPO_ROOT / "workspaces.yml"

# Valid workspace types
WORKSPACE_TYPES = ["ingestion", "lakehouse_processing", "lakehouse"]

# Items in scope for publish. Add types here as the solution grows.
ITEM_TYPE_IN_SCOPE = [
    "Notebook",
    "DataPipeline",
    "Environment",
    "Lakehouse",
]


def load_workspace_config(config_path: Path = WORKSPACES_CONFIG) -> dict:
    """Load workspace configuration from lakehouse_solution.yml.
    
    Returns a nested dict: {workspace_type: {environment: workspace_id}}
    """
    if not config_path.is_file():
        raise SystemExit(f"Workspace config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if "workspaces" not in data:
        raise SystemExit(f"'workspaces' section not found in {config_path}")

    return data["workspaces"]


def get_workspace_id(workspace_type: str, environment: str) -> str:
    """Get the workspace ID for a given workspace type and environment.
    
    Checks for environment variable override first:
        {WORKSPACE_TYPE}_{ENVIRONMENT}_WORKSPACE_ID
    """
    config = load_workspace_config()
    
    # Check for environment variable override
    env_var_name = f"{workspace_type.upper()}_{environment.upper()}_WORKSPACE_ID"
    if env_var_name in os.environ:
        return os.environ[env_var_name]
    
    # Get from config file
    if workspace_type not in config:
        raise SystemExit(f"Workspace type '{workspace_type}' not found in {WORKSPACES_CONFIG}")
    
    if environment not in config[workspace_type]:
        raise SystemExit(
            f"Environment '{environment}' not found for workspace '{workspace_type}' in {WORKSPACES_CONFIG}"
        )
    
    return config[workspace_type][environment]


def get_repository_directory(workspace_type: str) -> Path:
    """Get the repository directory for a workspace type."""
    directory = SOLUTION_ROOT / workspace_type
    if not directory.is_dir():
        raise SystemExit(f"Repository directory not found: {directory}")
    return directory


def deploy(workspace_type: str, environment: str, *, unpublish_orphans: bool) -> None:
    """Deploy artifacts from a workspace folder to a Fabric workspace."""
    workspace_id = get_workspace_id(workspace_type, environment)
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
