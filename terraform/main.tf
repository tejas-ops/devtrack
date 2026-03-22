# main.tf — the core Terraform configuration
# Provisions: Resource Group, AKS, ACR, KeyVault, PostgreSQL
#
# INTERVIEW MUST-KNOWS:
#   terraform init    = download providers, set up backend
#   terraform plan    = show what WILL change (no changes made yet) — always run this first
#   terraform apply   = apply the changes (creates/updates/destroys resources)
#   terraform destroy = delete everything (careful in prod!)
#   terraform state   = inspect/manipulate the state file
#
# State file: tracks what Terraform has created.
# ALWAYS store state remotely (Azure Storage) — never commit it to git.
# If two people run Terraform simultaneously without remote state → conflicts.

# ── Terraform configuration ──────────────────────────────────────────────────
terraform {
  required_version = ">= 1.7.0"   # minimum Terraform CLI version

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"   # ~> 3.100 = >= 3.100 AND < 4.0 (allows patch updates)
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # ── Remote state backend ──
  # State is stored in Azure Blob Storage — shared across the team
  # Create this storage account BEFORE running terraform init
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstatedevtrack"
    container_name       = "tfstate"
    key                  = "devtrack.terraform.tfstate"
    # Each environment gets its own key:
    #   dev:     devtrack-dev.terraform.tfstate
    #   prod:    devtrack-prod.terraform.tfstate
  }
}

# ── Configure the Azure provider ─────────────────────────────────────────────
provider "azurerm" {
  features {
    key_vault {
      # If a secret exists in KeyVault, purge it before re-creating
      purge_soft_delete_on_destroy = true
      recover_soft_deleted_key_vaults = true
    }
  }
  # Credentials come from environment variables (set by CI/CD):
  #   ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_TENANT_ID, ARM_SUBSCRIPTION_ID
  # OR from 'az login' when running locally
}

# ── Local values (computed from input variables) ─────────────────────────────
locals {
  # Naming convention: {app}-{env}-{resource_type}
  prefix   = "${var.app_name}-${var.environment}"
  # devtrack-dev, devtrack-prod, etc.

  # Merge default tags with environment tag
  tags = merge(var.tags, {
    environment = var.environment
  })
}

# ── Random suffix to ensure globally unique names ─────────────────────────────
resource "random_id" "suffix" {
  byte_length = 3   # generates a 6-character hex string e.g. "a1b2c3"
}

# ── Resource Group ───────────────────────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name   # "devtrack-rg"
  location = var.location              # "uksouth"
  tags     = local.tags
}

# ── Azure Container Registry ─────────────────────────────────────────────────
resource "azurerm_container_registry" "acr" {
  name                = "${replace(local.prefix, "-", "")}acr${random_id.suffix.hex}"
  # ACR names must be alphanumeric only (no hyphens) and globally unique
  # replace() removes hyphens: "devtrack-dev" → "devtrackdev"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  # Standard = pull-through cache, geo-replication available
  # Premium  = adds: private endpoints, content trust, dedicated data endpoints

  admin_enabled       = false   # use Service Principal authentication instead

  tags = local.tags
}

# ── Azure Kubernetes Service ─────────────────────────────────────────────────
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "${local.prefix}-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = local.prefix   # e.g. devtrack-dev — used in FQDN
  kubernetes_version  = "1.28"

  # ── Default node pool ──
  default_node_pool {
    name                = "system"
    node_count          = var.aks_node_count
    vm_size             = var.aks_vm_size
    os_disk_size_gb     = 50
    type                = "VirtualMachineScaleSets"
    # VMSS = node pool can auto-scale (required for Cluster Autoscaler)

    # Enable auto-scaling on the system node pool
    enable_auto_scaling = true
    min_count           = 1
    max_count           = 5

    node_labels = {
      "nodepool-type" = "system"
      "environment"   = var.environment
    }
  }

  # ── Workload node pool (separate from system — best practice) ──
  # (defined as azurerm_kubernetes_cluster_node_pool below)

  # ── Identity — how AKS authenticates to Azure services ──
  identity {
    type = "SystemAssigned"
    # SystemAssigned = Azure creates a managed identity automatically
    # We then grant this identity permission to pull from ACR
  }

  # ── Network ──
  network_profile {
    network_plugin = "azure"    # Azure CNI (pods get VNet IPs — best for AKS)
    network_policy = "calico"   # Calico enforces Kubernetes NetworkPolicies
    # NetworkPolicy = firewall rules BETWEEN pods (microsegmentation)
    load_balancer_sku = "standard"
  }

  # ── Monitoring — send AKS logs to Azure Monitor ──
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  tags = local.tags
}

# ── Grant AKS permission to pull from ACR ────────────────────────────────────
# Without this, pods can't pull images — you'd get ImagePullBackOff errors
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name = "AcrPull"   # built-in Azure role
  scope                = azurerm_container_registry.acr.id
}

# ── Azure Key Vault ──────────────────────────────────────────────────────────
resource "azurerm_key_vault" "main" {
  name                = "${local.prefix}-kv-${random_id.suffix.hex}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  purge_protection_enabled        = true   # prevent accidental deletion in prod
  soft_delete_retention_days      = 7

  tags = local.tags
}

# Grant AKS pods permission to read KeyVault secrets
resource "azurerm_key_vault_access_policy" "aks" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id

  secret_permissions = ["Get", "List"]
  # Pods can GET and LIST secrets, but not create/delete them
}

# Store the DB password in KeyVault
resource "azurerm_key_vault_secret" "db_password" {
  name         = "postgres-admin-password"
  value        = var.postgres_admin_password
  key_vault_id = azurerm_key_vault.main.id
  # In CI/CD: read back with: az keyvault secret show --vault-name ... --name ...
}

# ── Log Analytics Workspace ──────────────────────────────────────────────────
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.prefix}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30   # keep 30 days of logs (adjust for compliance)
  tags                = local.tags
}

# ── Data sources ─────────────────────────────────────────────────────────────
# Data sources READ existing Azure resources (don't create them)
data "azurerm_client_config" "current" {}
# Gets the current Azure authentication context (tenant ID, subscription ID, etc.)
