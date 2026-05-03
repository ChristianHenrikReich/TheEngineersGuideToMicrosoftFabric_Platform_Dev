// Parameters for TST environment
using '../main.bicep'

param environment = 'tst'
param location = 'norwayeast'
param resourceGroupName = 'rg-lakehouse-tst'
param keyVaultName = 'kv-lakehouse-tst'
param tags = {
  Environment: 'tst'
  Solution: 'Lakehouse'
  ManagedBy: 'Bicep'
  CostCenter: 'DataPlatform'
}
