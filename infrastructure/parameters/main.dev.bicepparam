// Parameters for DEV environment
using '../main.bicep'

param environment = 'dev'
param location = 'norwayeast'
param resourceGroupName = 'rg-lakehouse-dev'
param keyVaultName = 'kv-lakehouse-dev'
param tags = {
  Environment: 'dev'
  Solution: 'Lakehouse'
  ManagedBy: 'Bicep'
  CostCenter: 'DataPlatform'
}
