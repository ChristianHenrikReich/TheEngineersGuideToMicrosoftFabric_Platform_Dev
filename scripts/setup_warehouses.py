"""Setup warehouses in the lakehouse Fabric workspace.

Warehouse names are read from lakehouse_solution.yml under
``workspaces.lakehouse.warehouses``.

Local usage:
    az login
    python scripts/setup_warehouses.py --environment dev
"""

from __future__ import annotations

import argparse
import sys

from fabric_client import setup_workspace_items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Setup warehouses in Fabric workspace using Fabric REST API."
    )
    parser.add_argument(
        "--environment", "-e",
        required=True,
        choices=["dev", "tst", "prd"],
        help="Target environment",
    )
    args = parser.parse_args(argv)

    try:
        setup_workspace_items(
            item_type="warehouses",
            workspace_type="lakehouse",
            environment=args.environment,
        )
        return 0
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
