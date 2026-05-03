// Main Bicep template for Lakehouse Solution infrastructure
// Deploy Azure resources required for Fabric lakehouse solution
//
// Usage:
//   az deployment sub create \
//     --location <region> \
//     --template-file infrastructure/main.bicep \
//     --parameters infrastructure/parameters/main.dev.bicepparam

targetScope = 'subscription'

@description('Environment name (dev, tst, prd)')
@allowed(['dev', 'tst', 'prd'])
param environment string

@description('Azure region for resources')
param location string = deployment().location

@description('Resource group name for infrastructure')
param resourceGroupName string = 'rg-lakehouse-${environment}'

@description('Key Vault name')
param keyVaultName string

@description('Tags to apply to all resources')
param tags object = {
  Environment: environment
  Solution: 'Lakehouse'
  ManagedBy: 'Bicep'
}

// Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// Key Vault Module
module keyVault 'modules/keyvault.bicep' = {
  scope: rg
  name: 'keyVault-deployment'
  params: {
    keyVaultName: keyVaultName
    location: location
    environment: environment
    tags: tags
  }
}

// Outputs
output resourceGroupName string = rg.name
output keyVaultName string = keyVault.outputs.keyVaultName
output keyVaultId string = keyVault.outputs.keyVaultId
