# outputs.tf — values exposed after terraform apply
#
# WHY outputs?
#   1. Share values between Terraform modules
#   2. Print important values to the terminal after apply
#   3. CI/CD pipelines read outputs with: terraform output -raw <name>
#
# Example in GitHub Actions:
#   AKS_NAME=$(terraform output -raw aks_cluster_name)
#   az aks get-credentials --name "$AKS_NAME" --resource-group "$RG_NAME"

output "resource_group_name" {
  value       = azurerm_resource_group.main.name
  description = "Name of the Azure Resource Group"
}

output "aks_cluster_name" {
  value       = azurerm_kubernetes_cluster.aks.name
  description = "Name of the AKS cluster — use with az aks get-credentials"
}

output "aks_host" {
  value       = azurerm_kubernetes_cluster.aks.kube_config[0].host
  description = "AKS API server URL"
  sensitive   = true   # won't print in terminal — access with: terraform output aks_host
}

output "acr_login_server" {
  value       = azurerm_container_registry.acr.login_server
  description = "ACR registry URL — e.g. devtrackdevacr.azurecr.io"
}

output "key_vault_name" {
  value       = azurerm_key_vault.main.name
  description = "Key Vault name for retrieving secrets"
}

output "key_vault_uri" {
  value       = azurerm_key_vault.main.vault_uri
  description = "Key Vault URI — use with Azure SDK DefaultAzureCredential"
}

output "log_analytics_workspace_id" {
  value       = azurerm_log_analytics_workspace.main.id
  description = "Log Analytics Workspace ID for KQL queries"
}
