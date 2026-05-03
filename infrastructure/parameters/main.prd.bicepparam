// Parameters for PRD environment
using '../main.bicep'

param environment = 'prd'
param location = 'norwayeast'
param resourceGroupName = 'rg-lakehouse-prd'
param keyVaultName = 'kv-lakehouse-prd'
param tags = {
  Environment: 'prd'
  Solution: 'Lakehouse'
  ManagedBy: 'Bicep'
  CostCenter: 'DataPlatform'
}
