# Agent Rules and Context for Lakehouse Solution

This document provides rules, conventions, and architectural decisions for AI agents working on this Microsoft Fabric lakehouse solution. Follow these guidelines to maintain consistency and avoid regression.

## Project Overview

Multi-environment Microsoft Fabric deployment solution with automated workspace and lakehouse provisioning. Three workspace types (ingestion, lakehouse_processing, lakehouse) deployed across three environments (dev/tst/prd) using fabric-cicd.

## Environment Naming Convention

**CRITICAL: Use consistent 3-letter environment codes**

- ✅ **dev** - Development environment
- ✅ **tst** - Test environment  
- ✅ **prd** - Production environment

**Do NOT use:**
- ❌ `test` - Inconsistent length
- ❌ `prod` - Inconsistent length
- ❌ Any other variations

**Rationale:** Keeps naming uniform length for alignment in configs and logs.

## Workspace Naming Convention

Format: `{solution_name}-{workspace_type}-{environment}`

Solution name: `main`

Examples:
- `main-ingestion-dev`
- `main-lakehouse_processing-tst`
- `main-lakehouse-prd`

## Architecture Decisions

### 1. Use Fabric REST API (Not CLI)

**Rule:** Always use Fabric REST API for programmatic automation.

- ✅ `requests` library with REST endpoints
- ✅ Direct API calls to `https://api.fabric.microsoft.com/v1`
- ❌ NO `subprocess` calls to Fabric CLI
- ❌ NO `fabric` Python SDK (if it exists)

**Rationale:** REST API is more reliable, provides better error handling, and doesn't require external CLI installations in CI/CD.

### 2. Authentication Pattern

**Rule:** Use `AzureCliCredential` from `azure.identity`

```python
from azure.identity import AzureCliCredential

credential = AzureCliCredential()
token = credential.get_token("https://api.fabric.microsoft.com/.default")
```

**Do NOT use:**
- ❌ `AzureDefaultCredential` (deprecated best practice)
- ❌ Other credential chains

**Rationale:** `AzureCliCredential` works consistently across local (`az login`) and CI/CD (AzureCLI@2 task, azure/login action).

### 3. Shared Code Pattern

**Rule:** Extract duplicate code into shared modules.

- ✅ `fabric_client.py` contains `FabricClient` base class
- ✅ Manager classes inherit from `FabricClient`
- ✅ Shared utilities in common modules

**Example:**
```python
from fabric_client import FabricClient, load_workspace_config

class FabricWorkspaceManager(FabricClient):
    def list_workspaces(self) -> dict[str, str]:
        return self._api_request("GET", "/workspaces")
```

### 4. Configuration Management

**Rule:** `lakehouse_solution.yml` is the single source of truth for workspace IDs.

Structure:
```yaml
solution_name: main

alias:
  dev_capacity: "actual-capacity-id"  # Reusable values

workspaces:
  {workspace_type}:
    dev:
      id: "workspace-id-or-placeholder"
      capacity: dev_capacity  # Can reference alias
    tst:
      id: "workspace-id-or-placeholder"
      capacity: "REPLACE_WITH_YOUR_CAPACITY_ID"
    prd:
      id: "workspace-id-or-placeholder"
      capacity: "REPLACE_WITH_YOUR_CAPACITY_ID"
    lakehouses:  # Optional property for lakehouse workspace
      - bronze
      - silver
    warehouses:  # Optional property for warehouse items
      - gold
```

**Key Points:**
- Each environment entry is an **object** with `id` and `capacity` properties
- **Aliases** allow reusing common values (e.g., capacity IDs across multiple workspaces)
- `setup_workspaces.py` updates this file with actual IDs from Fabric API
- `deploy.py` reads from this file (with optional env var overrides)
- Environment variables are **optional overrides**, not required
- File is committed to git and updated by CI/CD
- All scripts use `_preprocess_config()` from `fabric_client.py` to automatically resolve aliases

### 5. No Circular Dependencies

**CRITICAL RULE:** Never require workspace IDs before `setup_workspaces.py` runs.

**Problem Pattern (AVOID):**
```yaml
# ❌ BAD: Requires WORKSPACE_ID before setup runs
variables:
  - group: fabric-workspace-env  # Contains WORKSPACE_ID
steps:
  - script: python deploy.py --workspace-id $(WORKSPACE_ID)
```

**Correct Pattern:**
```yaml
# ✅ GOOD: Reads from lakehouse_solution.yml updated by setup stage
steps:
  - script: python setup_workspaces.py  # Updates lakehouse_solution.yml
  - script: python deploy.py            # Reads from lakehouse_solution.yml
```

**Rationale:** Workspace IDs are created by `setup_workspaces.py`, so they can't exist before it runs.

### 6. Infrastructure Deployment Pattern

**Rule:** Azure infrastructure is deployed BEFORE Fabric workspace setup using separate service principals.

**Directory Structure:**
```
infrastructure/
  main.bicep                    # Subscription-scoped main template
  modules/
    keyvault.bicep              # Key Vault module
  parameters/
    main.dev.bicepparam         # Environment-specific parameters
    main.tst.bicepparam
    main.prd.bicepparam
```

**Deployment Order:**
1. **Infrastructure Stage** - Deploy Azure resources (Key Vault, etc.)
2. **Setup Workspaces** - Create Fabric workspaces
3. **Setup Lakehouses** - Create lakehouse items
4. **Setup Warehouses** - Create warehouse items
5. **Deploy Fabric Items** - Deploy notebooks, pipelines, etc.

**Separate Service Principals:**

Infrastructure deployment and Fabric deployment use **different** service principals due to RBAC separation:

- **Infrastructure SP**: Contributor on Azure subscription
  - Azure DevOps: `Azure-Service-Connection`
  - GitHub Actions: Uses `AZURE_SUBSCRIPTION_ID` secret
- **Fabric SP**: Contributor on Fabric capacity
  - Azure DevOps: `spn-main-fabric-deploy`
  - GitHub Actions: Same client ID, no subscription ID needed

**Bicep Deployment:**
```bash
az deployment sub create \
  --location norwayeast \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters/main.{environment}.bicepparam
```

**Rationale:** Separation of concerns - Azure resource management permissions are different from Fabric workspace permissions. Infrastructure resources (like Key Vault) must exist before Fabric items can reference them.

**Rationale:** Workspace IDs are created by `setup_workspaces.py`, so they can't exist before it runs.

## File Organization

### Directory Structure

```
.azure_devops/          # Azure DevOps pipeline files
  azure-pipelines.yml
  templates/
    deploy-workspace.yml

.github/workflows/      # GitHub Actions workflows
  deploy-fabric.yml

infrastructure/         # Azure infrastructure (Bicep)
  main.bicep
  modules/
    keyvault.bicep
  parameters/
    main.dev.bicepparam
    main.tst.bicepparam
    main.prd.bicepparam
  README.md

solution/               # Fabric items organized by workspace type
  ingestion/
  lakehouse_processing/
  lakehouse/

fabric_client.py        # Shared Fabric REST API client
setup_workspaces.py     # Create/update workspaces
setup_lakehouses.py     # Create lakehouse items
setup_warehouses.py     # Create warehouse items
deploy.py               # Deploy Fabric items
lakehouse_solution.yml  # Solution config with workspace IDs
requirements-deploy.txt # Python dependencies
```

### Python Script Patterns

All Python scripts should:
1. Use `from __future__ import annotations` for type hints
2. Have comprehensive docstrings
3. Use type hints on function signatures
4. Include `main()` with `argparse` for CLI usage
5. Handle errors gracefully with `SystemExit` for user errors

## CI/CD Pipeline Rules

### Pipeline Flow

**Both Azure DevOps and GitHub Actions must follow:**

1. **Infrastructure Stage/Job** - Deploy Azure resources first
   - Execute Bicep deployment to subscription
   - Use `Azure-Service-Connection` (Azure DevOps) or `AZURE_SUBSCRIPTION_ID` secret (GitHub Actions)
   - Support approval gates for tst/prd environments

2. **Setup Stage/Job** - Create Fabric workspaces and items
   - Depends on infrastructure deployment completing
   - Execute `setup_workspaces.py` to create workspaces
   - Execute `setup_lakehouses.py` to create lakehouse items
   - Execute `setup_warehouses.py` to create warehouse items
   - Commit `lakehouse_solution.yml` changes with `[skip ci]`
   - Use `persistCredentials: true` / `token: ${{ secrets.GITHUB_TOKEN }}`

3. **Deploy Stage/Job** - Runs after setup
   - Read workspace IDs from `lakehouse_solution.yml`
   - NO workspace ID variables required
   - Use approval gates for tst/prd environments

### Azure DevOps Specifics

**Service Connections:**
- `Azure-Service-Connection` - For infrastructure deployment (Contributor on subscription)
- `spn-main-fabric-deploy` - For Fabric deployment (Contributor on Fabric capacity)

**Variable Groups:** NOT required for workspace IDs (removed)

**Environments:** Required for approvals
- `fabric-tst` - Test environment (requires approval)
- `fabric-prd` - Production environment (requires approval)

### GitHub Actions Specifics

**Secrets Required:**
- `AZURE_CLIENT_ID` - Client ID for both infrastructure and Fabric deployment
- `AZURE_TENANT_ID` - Tenant ID
- `AZURE_SUBSCRIPTION_ID` - Subscription ID for infrastructure deployment

**Environment Variables:** NOT required for workspace IDs (removed)

**Environments:** Required for approvals
- `fabric-dev`
- `fabric-tst` (requires approval)
- `fabric-prd` (requires approval)

## Git Commit Practices

**CRITICAL RULE:** Each solved task must be its own commit.

**Never batch multiple completed tasks into one commit.** When you solve a task, commit it immediately before moving to the next task.

**Good Commit Sequence (one task per commit):**
```
feat: add shared Fabric REST API client module
refactor: use shared FabricClient in setup_workspaces.py
refactor: use shared FabricClient in setup_lakehouses.py
docs: document shared fabric_client module
fix: remove WORKSPACE_ID circular dependency from pipelines
```

**Bad Practice (batching tasks):**
```
# ❌ BAD: Multiple unrelated tasks in one commit
feat: add shared module and update both scripts
```

**Commit Message Format:**
```
<type>: <short description>

<optional longer explanation>
<why this change was made>
<what problem it solves>
```

Types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`

**Workflow:**
1. Solve one task completely
2. `git add` only files related to that task
3. `git commit` with descriptive message
4. Move to next task
5. Repeat

## Data-Driven Configuration

**Rule:** Configuration drives automation, not hardcoded values.

**Example - Lakehouse and Warehouse Names:**
```yaml
# lakehouse_solution.yml
lakehouse:
  dev: "workspace-id"
  tst: "workspace-id"
  prd: "workspace-id"
  lakehouses:  # Data-driven list of lakehouse items
    - bronze
    - silver  # Just add here, no code changes needed
  warehouses:  # Data-driven list of warehouse items
    - gold
```

**Script automatically processes:**
```python
def get_lakehouse_names() -> list[str]:
    config = load_workspace_config()
    return config["lakehouse"]["lakehouses"]
```

## API Validation Pattern

**Rule:** Validate against live Fabric API, not placeholder checks.

**Bad Pattern:**
```python
if workspace_id == "placeholder":  # ❌ String comparison
    create_workspace()
```

**Good Pattern:**
```python
existing = manager.list_workspaces()  # ✅ API call
if workspace_name not in existing:
    workspace_id = manager.create_workspace(workspace_name)
```

## Error Handling

**User-facing errors:**
```python
if environment not in valid_envs:
    raise SystemExit(f"Unknown environment '{environment}'. Use: {valid_envs}")
```

**Internal errors:**
```python
if not workspace_id:
    raise RuntimeError(f"Failed to create workspace: no ID returned")
```

## Code Quality Standards

### Type Safety

Use `isinstance()` checks when iterating YAML:

```python
for workspace_type, environments in config.items():
    if not isinstance(environments, dict):
        continue  # Skip non-workspace entries like 'lakehouses'
    
    for env, workspace_id in environments.items():
        if not isinstance(workspace_id, str):
            continue  # Skip nested objects
```

**Rationale:** YAML structure has optional properties like `lakehouses: [...]` that aren't workspace IDs.

### YAML Operations

**Preserve structure when updating:**
```python
def save_workspace_config(config: dict) -> None:
    with config_path.open("w", encoding="utf-8") as fh:
        # Write header comment
        fh.write("# Fabric workspace IDs\n\n")
        
        # Preserve order and structure
        yaml.safe_dump(
            config,
            fh,
            default_flow_style=False,
            sort_keys=False,  # Maintain insertion order
            allow_unicode=True,
        )
```

## Recovery Patterns

### File Corruption During Refactoring

**If multiple `replace_string_in_file` operations fail:**

1. Check errors with `get_errors()`
2. If >10 syntax errors, consider delete + recreate
3. Use `create_file` for clean slate

**Better than:** Multiple overlapping string replacements that leave fragments

### Large Refactors

**For major changes across entire files:**
- Prefer `create_file` over multiple `replace_string_in_file`
- Delete old file first if needed
- Single clean operation is safer than incremental overlapping edits

## Documentation Standards

### README.md Sections

Required sections:
1. Project overview
2. Repository layout (with file tree)
3. Setup instructions (workspaces, lakehouses)
4. Local deployment
5. CI/CD for each platform (GitHub Actions, Azure DevOps)
6. Notes about architecture decisions

### Code Documentation

Every script needs:
- Module docstring with purpose and usage examples
- Function docstrings with Args/Returns
- Inline comments for non-obvious logic

## Testing Before Commit

**Always run before committing:**
```bash
# Check for syntax errors
get_errors()  # If using AI agent tools

# Or manually:
python -m py_compile setup_workspaces.py
python -m py_compile setup_lakehouses.py
python -m py_compile deploy.py
```

## Common Mistakes to Avoid

1. ❌ Using `test`/`prod` instead of `tst`/`prd`
2. ❌ Mixing Fabric CLI and REST API
3. ❌ Requiring WORKSPACE_ID before setup_workspaces runs
4. ❌ Hardcoding workspace/lakehouse names instead of reading from config
5. ❌ Using `AzureDefaultCredential` instead of `AzureCliCredential`
6. ❌ Not checking `isinstance()` when iterating YAML with optional properties
7. ❌ **Batching multiple solved tasks into one commit** - ALWAYS commit each task separately
8. ❌ Forgetting to update README.md after architectural changes

## Key Learnings

### Fabric REST API Endpoints

```python
# Base URL
FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"

# Workspaces
GET    /workspaces                    # List all
POST   /workspaces                    # Create
GET    /workspaces/{id}               # Get details

# Lakehouses
GET    /workspaces/{id}/lakehouses    # List in workspace
POST   /workspaces/{id}/lakehouses    # Create in workspace

# Create payload
{
    "displayName": "workspace-name",
    "description": "optional description"
}
```

### fabric-cicd Integration

```python
from fabric_cicd import (
    FabricWorkspace,
    publish_all_items,
    unpublish_all_orphan_items,
)

# Deploy items from directory to workspace
workspace = FabricWorkspace(
    workspace_id=workspace_id,
    credential=AzureCliCredential()
)

publish_all_items(
    workspace=workspace,
    directory=repository_dir,
    item_type_in_scope=["Notebook", "DataPipeline", "Environment", "Lakehouse"]
)
```

## When to Update This Document

Add to AGENTS.md when you:
- Establish a new pattern or convention
- Make an architectural decision
- Solve a non-obvious problem
- Create a new automation workflow
- Change the project structure
- Learn something that wasn't documented

Keep this document current - it's the knowledge base for maintaining this solution.
