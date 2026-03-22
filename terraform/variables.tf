# variables.tf — all input variables for this Terraform configuration
#
# WHY use variables?
#   - Avoid hardcoding values (make configs reusable across environments)
#   - Values can come from: terraform.tfvars, environment variables, CLI flags
#   - Sensitive vars (like passwords) should NOT have defaults — Terraform will prompt you
#
# INTERVIEW: "What's the difference between variable, local, and output in Terraform?"
#   variable = input (you provide it)
#   local    = computed/derived value (you calculate it inside Terraform)
#   output   = exported value (you share it with other modules/users)

variable "resource_group_name" {
  type        = string
  description = "Name of the Azure Resource Group"
  default     = "devtrack-rg"
}

variable "location" {
  type        = string
  description = "Azure region for all resources"
  default     = "uksouth"   # closest Azure region to Royal Mail / UK companies
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
  default     = "dev"

  validation {
    # Terraform validates this BEFORE running plan/apply
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod"
  }
}

variable "app_name" {
  type        = string
  description = "Application name — used as prefix for all Azure resource names"
  default     = "devtrack"
}

variable "aks_node_count" {
  type        = number
  description = "Number of AKS nodes in the default node pool"
  default     = 2

  validation {
    condition     = var.aks_node_count >= 1 && var.aks_node_count <= 10
    error_message = "aks_node_count must be between 1 and 10"
  }
}

variable "aks_vm_size" {
  type        = string
  description = "Azure VM size for AKS nodes"
  default     = "Standard_D2s_v3"
  # Standard_D2s_v3 = 2 vCPUs, 8GB RAM — good for dev/staging
  # Standard_D4s_v3 = 4 vCPUs, 16GB RAM — better for prod
}

variable "postgres_sku" {
  type        = string
  description = "Azure Database for PostgreSQL SKU"
  default     = "B_Standard_B1ms"
  # B = Burstable (dev/test), GP = General Purpose (prod), MO = Memory Optimized
}

variable "postgres_admin_password" {
  type        = string
  description = "PostgreSQL admin password"
  sensitive   = true   # Terraform will NEVER print this in logs or state output
  # No default — Terraform will prompt for it, or you set TF_VAR_postgres_admin_password
}

variable "tags" {
  type        = map(string)
  description = "Azure resource tags (key-value pairs for cost tracking, ownership)"
  default = {
    project     = "devtrack"
    managed-by  = "terraform"
    team        = "platform-engineering"
  }
}
