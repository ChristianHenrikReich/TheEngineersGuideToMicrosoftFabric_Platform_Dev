# Infrastructure

Azure infrastructure deployment for the Lakehouse Solution using Bicep.

## Structure

```
infrastructure/
├── main.bicep                           # Main subscription-scoped template
├── modules/
│   └── keyvault.bicep                   # Key Vault module
├── parameters/
│   ├── main.dev.parameters.json         # DEV environment parameters
│   ├── main.tst.parameters.json         # TST environment parameters
│   └── main.prd.parameters.json         # PRD environment parameters
└── README.md                            # This file
```

## Resources Deployed

- **Resource Group**: `rg-{projectName}-{environment}` (automatically created)
- **Key Vault**: `{projectAbbr}kv{env}{uniqueString}` (max 24 chars, RBAC-enabled)

## Local Deployment

### Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Bicep CLI installed (bundled with Azure CLI)
- Contributor access to the Azure subscription

### Deploy to Development

```bash
az deployment sub create \
  --location norwayeast \
  --template-file infrastructure/main.bicep \
  --parameters @infrastructure/parameters/main.dev.parameters.json
```

### Deploy to Test

```bash
az deployment sub create \
  --location norwayeast \
  --template-file infrastructure/main.bicep \
  --parameters @infrastructure/parameters/main.tst.parameters.json
```

### Deploy to Production

```bash
az deployment sub create \
  --location norwayeast \
  --template-file infrastructure/main.bicep \
  --parameters @infrastructure/parameters/main.prd.parameters.json
```

## CI/CD Deployment

Infrastructure is deployed automatically via Azure DevOps and GitHub Actions pipelines before Fabric workspace deployment.

### Azure DevOps

- **Service Connection**: `Azure-Service-Connection` (Contributor on subscription)
- **Stage**: `deploy_infrastructure_{environment}`
- **Task**: `AzureCLI@2` with Bicep deployment command

### GitHub Actions

- **Secrets Required**: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- **Job**: `deploy_infrastructure`
- **Authentication**: Azure login with OIDC (federated credentials)

## Parameters

Edit the `.parameters.json` files in `parameters/` to customize:

- `environment`: Environment name (dev, tst, prd)
- `location`: Azure region (default: norwayeast)
- `projectName`: Project prefix for resource names (default: lakehouse)
- `keyVaultSku`: Key Vault SKU (standard or premium, default: standard)
- `tags`: Resource tags for organization and cost tracking

## Naming Convention

Resources follow Azure best practices with uniqueString for global uniqueness:

- **Resource Group**: `rg-{projectName}-{environment}` (e.g., `rg-lakehouse-dev`)
- **Key Vault**: `{projectAbbr}kv{env}{uniqueString}` (e.g., `lakehokv dev1234567890abc`)
  - Max 24 characters
  - Globally unique using subscription ID and resource group hash

## Key Vault Configuration

The Key Vault is configured with:
- **RBAC Authorization**: Enabled (no access policies, use Azure RBAC roles)
- **Soft Delete**: Enabled with 90-day retention
- **Purge Protection**: **NOT enabled** (intentional - irreversible once set)
- **Public Network Access**: Enabled
- **Network ACLs**: Allow Azure Services, default action Allow

### Required RBAC Roles

- **Key Vault Secrets Officer**: For Fabric deployment pipeline to read/write secrets
- **Key Vault Secrets User**: For applications to read secrets

## Notes

- Key Vault names are automatically generated using uniqueString for global uniqueness
- Soft delete retention is 90 days
- Purge protection intentionally excluded (irreversible once enabled, per data_platform best practices)
- Uses subscription-scoped deployment (`targetScope = 'subscription'`) to create resource groups
- Production-ready configuration based on battle-tested data_platform repository
