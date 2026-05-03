# Lakehouse Solution — Microsoft Fabric

Fabric items (notebooks, pipelines, lakehouses, environments) live under `solution/`
organized by **workspace type**. Each workspace type has separate dev/tst/prd 
instances in Fabric, managed through [`fabric-cicd`](https://microsoft.github.io/fabric-cicd/).

## Workspace Organization

This solution uses **three workspace types**:

- **ingestion**: Notebooks for ingesting data from customer databases
- **lakehouse_processing**: Notebooks/pipelines for processing and transforming data
- **lakehouse**: Gold and silver lakehouse artifacts

During CI/CD deployment, you specify both the workspace type and the environment 
(dev/tst/prd), and the script deploys to the appropriate Fabric workspace.

## Repository layout

\`\`\`
solution/
  ingestion/                # Ingestion workspace artifacts
    parameter.yml           # Ingestion-specific parameters
    ingest_from_customers_databases/
  lakehouse_processing/     # Processing workspace artifacts
    parameter.yml           # Processing-specific parameters
  lakehouse/                # Lakehouse workspace artifacts
    parameter.yml
    gold.Lakehouse/         # (created by setup_lakehouses.py)
    silver.Lakehouse/       # (created by setup_lakehouses.py)
AGENTS.md                   # Rules and architectural decisions for AI agents/developers
workspaces.yml              # Workspace ID mapping (workspace_type -> environment -> id)
fabric_client.py            # Shared Fabric REST API client
setup_workspaces.py         # Create/update Fabric workspaces and workspaces.yml
setup_lakehouses.py         # Create gold/silver lakehouse artifacts
deploy.py                   # Local + CI deployment entrypoint
requirements-deploy.txt     # Python deps for deploy.py
.azure_devops/
  azure-pipelines.yml       # Azure DevOps pipeline
  templates/
    deploy-workspace.yml    # Azure DevOps deployment template
.github/workflows/
  deploy-fabric.yml         # GitHub Actions pipeline
```

Each workspace type folder contains all artifacts for that logical workspace.
Environment naming (dev/tst/prd) happens during deployment via the 
`--environment` flag.

## Setup Fabric Workspaces

Before deploying, ensure all required Fabric workspaces exist and are configured 
in `workspaces.yml`. The `setup_workspaces.py` script automates this:

```bash
az login
pip install -r requirements-deploy.txt

# Create workspaces if they don't exist and update workspaces.yml
python setup_workspaces.py

# Dry run to see what would be created without making changes
python setup_workspaces.py --dry-run
```

This script:
1. Lists all accessible Fabric workspaces via REST API
2. Creates missing workspaces (named `{workspace_type}-{environment}`)
3. Updates `workspaces.yml` with actual workspace IDs

**Note:** Uses the shared `fabric_client.py` module for Fabric REST API operations.

## Deploy locally

Prereqs: Python 3.12, the Azure CLI, and access to the target Fabric workspace.

```bash
az login
pip install -r requirements-deploy.txt

# Deploy ingestion workspace to dev
python deploy.py --workspace ingestion --environment dev

# Deploy lakehouse workspace to production
python deploy.py --workspace lakehouse --environment prd

# Deploy all workspaces to test
python deploy.py --workspace ingestion --environment tst
python deploy.py --workspace lakehouse_processing --environment tst
python deploy.py --workspace lakehouse --environment tst
```

Workspace IDs are configured in `workspaces.yml`. Override them via environment 
variables: `{WORKSPACE_TYPE}_{ENVIRONMENT}_WORKSPACE_ID`, e.g., 
`INGESTION_DEV_WORKSPACE_ID`.

By default `deploy.py` also unpublishes items that exist in the workspace but
not in the repo. Pass `--no-unpublish-orphans` to skip that step.

## Setup lakehouses

The `setup_lakehouses.py` script creates lakehouse items directly in your Fabric 
workspace using the Fabric REST API. Lakehouse names are defined in 
`workspaces.yml` (data-driven configuration).

Prerequisites:
```bash
# Install Azure CLI Fabric extension
az extension add --name fabric
az login
```

Usage:
```bash
# Create lakehouses in the dev environment
python setup_lakehouses.py --environment dev

# Create lakehouses in production
python setup_lakehouses.py --environment prd
```

This will:
1. Read lakehouse names from `workspaces.yml` (`lakehouses` list)
2. Get the target workspace ID for the specified environment
3. Create each lakehouse using `fabric lakehouse create` CLI commands
4. Skip lakehouses that already exist

To add more lakehouses, simply update the `lakehouses` list in `workspaces.yml`:
```yaml
lakehouses:
  - gold
  - silver
  - bronze  # Add new lakehouses here
```

## Per-environment parameters

Each workspace folder has its own `parameter.yml` for fabric-cicd find/replace 
substitutions. The keys `DEV`, `TST`, `PRD` must match the `--environment` 
argument (uppercased).

Use parameter.yml for runtime substitutions like:
- Key Vault URLs
- Secret names
- Connection strings
- Lakehouse/warehouse ID references (using \`$items.Lakehouse.name.$id\` syntax)

Example: In \`solution/ingestion/parameter.yml\`, you can parameterize different 
Key Vault URLs per environment while keeping the same notebook code.

## CI: GitHub Actions

Workflow: `.github/workflows/deploy-fabric.yml`. 

**Workflow jobs:**

1. **setup_workspaces** - Runs `setup_workspaces.py` to ensure all Fabric workspaces exist
   - If `workspaces.yml` is updated with new workspace IDs, changes are committed back to the repository
   - Commit message includes `[skip ci]` to prevent triggering another workflow run

2. **setup** - Creates deployment matrix based on trigger type

3. **deploy** - Deploys Fabric items to selected environments

**Automatic deployment on push to main:**
- Runs setup_workspaces job first
- Deploys **all workspaces** to **dev** environment automatically

**Manual deployment via workflow_dispatch:**
- Select which workspace to deploy: `all`, `ingestion`, `lakehouse_processing`, or `lakehouse`
- Select target environment: `dev`, `tst`, or `prd`
- Requires approval for tst/prd environments (configure in GitHub Environment settings)

**Example usage:**
1. Push to `main` → Setup workspaces + deploy all workspaces to dev automatically
2. Manual trigger → Select "ingestion" + "prd" → Deploys only ingestion workspace to production
3. Manual trigger → Select "all" + "tst" → Deploys all workspaces to test

**One-time setup:**

1. Create a service principal and grant it Contributor access to your Fabric capacity.
2. Add **federated credentials** on the SP for this repo (subject
   `repo:<owner>/<repo>:environment:fabric-dev`, etc.).
3. Repo secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`.
4. GitHub Environments: `fabric-dev`, `fabric-tst`, `fabric-prd` with required reviewers 
   on tst and prd.

**Note:** Workspace IDs are read from `workspaces.yml`, which is automatically updated by the 
`setup_workspaces` job. No environment variables needed for workspace configuration.

## CI: Azure DevOps

Pipeline: `.azure_devops/azure-pipelines.yml`.

**Pipeline stages:**

1. **Setup Workspaces** - Runs `setup_workspaces.py` to ensure all Fabric workspaces exist
   - If `workspaces.yml` is updated with new workspace IDs, changes are committed back to the repository
   - Commit message includes `[skip ci]` to prevent triggering another pipeline run
   
2. **Deploy to Environments** - Deploys Fabric items to selected environments (dev/tst/prd)
   - Runs sequentially: dev → tst → prd
   - TST and PRD stages require approval via Azure DevOps environments

**Pipeline parameters:**

The pipeline uses object-based configuration defined in the YAML:
- `workspaces` array: Controls which workspaces to deploy (ingestion, lakehouse_processing, lakehouse)
- `environments` array: Controls target environments (dev, tst, prd) with deployment flags and approval requirements

Modify the parameter defaults in the YAML file to customize which workspaces and environments deploy by default.

**Behavior:**
- On push to `main` → Runs setup stage + deploys **all workspaces** to **dev**
- Manual run → Modify YAML parameters to control workspace/environment selection
- Stages run sequentially: setup_workspaces → dev → tst → prd
- TST and PRD require approval through Azure DevOps environments

**One-time setup:**

1. Create a service principal with Contributor access to your Fabric capacity.
2. Create service connection `fabric-deploy-sc` (Azure Resource Manager) in Azure DevOps linked to that SP.
3. Create environments `fabric-tst` and `fabric-prd` with approval checks.

**Note:** Workspace IDs are read from `workspaces.yml`, which is automatically updated by the 
`setup_workspaces` stage. No variable groups needed for workspace configuration.

## Notes

- **Shared Fabric API Client**: Both `setup_workspaces.py` and `setup_lakehouses.py` 
  use the shared `fabric_client.py` module, which provides a `FabricClient` base class 
  with common authentication and REST API request methods. This eliminates code 
  duplication and ensures consistent API interaction patterns.
- `deploy.py` uses `AzureCliCredential` in all contexts. Locally you run
  `az login` yourself; the GitHub Actions workflow uses `azure/login@v2` and
  the Azure DevOps pipeline uses the `AzureCLI@2` task, both of which
  establish an `az` CLI session that `AzureCliCredential` then reads.
- Workspace IDs in `workspaces.yml` are placeholders until `setup_workspaces.py` is run.
  The pipeline automatically runs this script and commits any changes back to the repository.
