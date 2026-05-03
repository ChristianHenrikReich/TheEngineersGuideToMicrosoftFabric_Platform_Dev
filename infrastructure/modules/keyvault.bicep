// Key Vault module for secure storage of connection strings and keys
// Configured with soft delete, purge protection, and RBAC

@description('Key Vault name')
param keyVaultName string

@description('Azure region')
param location string

@description('Environment name')
param environment string

@description('Resource tags')
param tags object

@description('Enable soft delete')
param enableSoftDelete bool = true

@description('Soft delete retention days')
@minValue(7)
@maxValue(90)
param softDeleteRetentionInDays int = 90

@description('Enable purge protection')
param enablePurgeProtection bool = true

@description('Enable RBAC authorization')
param enableRbacAuthorization bool = true

// Key Vault resource
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enablePurgeProtection: enablePurgeProtection ? true : null
    enableRbacAuthorization: enableRbacAuthorization
    networkAcls: {
      defaultAction: 'Allow' // Can be restricted to 'Deny' with specific rules
      bypass: 'AzureServices'
    }
  }
}

// Outputs
output keyVaultName string = keyVault.name
output keyVaultId string = keyVault.id
output keyVaultUri string = keyVault.properties.vaultUri
