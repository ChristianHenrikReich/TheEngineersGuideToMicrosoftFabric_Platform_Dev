// Main Bicep template for Lakehouse Solution infrastructure
// Deploy Azure resources required for Fabric lakehouse solution
//
// Usage:
//   az deployment sub create \
//     --location <region> \
//     --template-file infrastructure/main.bicep \
//     --parameters @infrastructure/parameters/main.{environment}.parameters.json

targetScope = 'subscription'

@description('Environment name (dev, tst, prd)')
@allowed([
  'dev'
  'tst'
  'prd'
])
param environment string

@description('Azure region for resources')
param location string = 'swedencentral'

@description('Project name prefix')
param projectName string

@description('Key Vault SKU')
@allowed([
  'standard'
  'premium'
])
param keyVaultSku string = 'standard'

@description('Tags to apply to all resources')
param tags object = {}

// Variables
var resourceGroupName = 'rg-${projectName}-${environment}'
// Key Vault name must be max 24 chars: shortened to fit Azure limits
// Pattern: {projectAbbr}{resourceType}{env}{uniqueString}
var keyVaultName = '${take(replace(projectName, '-', ''), 6)}kv${environment}${take(uniqueString(subscription().id, resourceGroupName), 13)}'
var commonTags = union(tags, {
  environment: environment
  managedBy: 'bicep'
})

// Create resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
  tags: commonTags
}

// Deploy Key Vault module
module keyVault './modules/keyvault.bicep' = {
  name: 'keyVaultDeployment'
  scope: resourceGroup
  params: {
    keyVaultName: keyVaultName
    location: location
    environment: environment
    tags: commonTags
    skuName: keyVaultSku
    enableRbacAuthorization: true
  }
}

// Outputs
@description('Resource group name')
output resourceGroupName string = resourceGroup.name

@description('Key Vault resource ID')
output keyVaultId string = keyVault.outputs.keyVaultId

@description('Key Vault name')
output keyVaultName string = keyVault.outputs.keyVaultName

@description('Key Vault URI')
output keyVaultUri string = keyVault.outputs.keyVaultUri
