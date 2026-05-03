# Infrastructure

Azure infrastructure deployment for the Lakehouse Solution using Bicep.

## Structure

```
infrastructure/
├── main.bicep                          # Main subscription-scoped template
├── modules/
│   └── keyvault.bicep                  # Key Vault module
├── parameters/
│   ├── main.dev.bicepparam             # DEV environment parameters
│   ├── main.tst.bicepparam             # TST environment parameters
│   └── main.prd.bicepparam             # PRD environment parameters
└── README.md                           # This file
```

## Resources Deployed

- **Resource Group**: Environment-specific resource group for infrastructure
- **Key Vault**: Secure storage for connection strings, keys, and secrets

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
  --parameters infrastructure/parameters/main.dev.bicepparam
```

### Deploy to Test

```bash
az deployment sub create \
  --location norwayeast \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters/main.tst.bicepparam
```

### Deploy to Production

```bash
az deployment sub create \
  --location norwayeast \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters/main.prd.bicepparam
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

Edit the `.bicepparam` files in `parameters/` to customize:

- `location`: Azure region (default: norwayeast)
- `resourceGroupName`: Resource group name pattern
- `keyVaultName`: Key Vault name (must be globally unique)
- `tags`: Resource tags for organization and cost tracking

## Key Vault Configuration

The Key Vault is configured with:
- **RBAC Authorization**: Enabled (no access policies, use Azure RBAC roles)
- **Soft Delete**: Enabled with 90-day retention
- **Purge Protection**: Enabled (prevents permanent deletion during retention period)
- **Network Access**: Allow from all networks (can be restricted to specific VNets/IPs)

### Required RBAC Roles

- **Key Vault Secrets Officer**: For Fabric deployment pipeline to read/write secrets
- **Key Vault Secrets User**: For applications to read secrets

## Notes

- Key Vault names must be globally unique (3-24 characters, alphanumeric and hyphens)
- Soft delete retention is 90 days (cannot be changed after creation if purge protection is enabled)
- Uses subscription-scoped deployment (`targetScope = 'subscription'`) to create resource groups
