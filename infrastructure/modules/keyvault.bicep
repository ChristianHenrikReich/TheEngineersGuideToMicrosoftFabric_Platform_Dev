// Key Vault module for secure storage of connection strings and keys
// Configured with soft delete and RBAC
// Note: Purge protection intentionally excluded (irreversible once enabled)

@description('Name of the Key Vault')
param keyVaultName string

@description('Location for the Key Vault')
param location string = resourceGroup().location

@description('Environment name (dev, tst, prd)')
param environment string

@description('Tags to apply to the Key Vault')
param tags object = {}

@description('SKU name for the Key Vault')
@allowed([
  'standard'
  'premium'
])
param skuName string = 'standard'

@description('Enable soft delete for the Key Vault')
param enableSoftDelete bool = true

@description('Soft delete retention in days')
@minValue(7)
@maxValue(90)
param softDeleteRetentionInDays int = 90

@description('Enable RBAC authorization')
param enableRbacAuthorization bool = true

@description('Tenant ID for the Key Vault')
param tenantId string = subscription().tenantId

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: union(tags, {
    environment: environment
  })
  properties: {
    sku: {
      family: 'A'
      name: skuName
    }
    tenantId: tenantId
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enableRbacAuthorization: enableRbacAuthorization
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

@description('Key Vault resource ID')
output keyVaultId string = keyVault.id

@description('Key Vault name')
output keyVaultName string = keyVault.name

@description('Key Vault URI')
output keyVaultUri string = keyVault.properties.vaultUri
