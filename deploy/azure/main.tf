# Terraform Infrastructure as Code for ChurnGuard MLOps on Azure
# ChurnGuard MLOps Level 2 Enterprise Platform Specification

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.85.0"
    }
  }
}

provider "azurerm" {
  features {}
  storage_use_azuread = true
}

variable "location" {
  type        = string
  default     = "southeastasia"
  description = "Primary Azure region (Singapore) for lowest latency to Vietnam (< 50ms)"
}

variable "resource_group_name" {
  type        = string
  default     = "rg-churnguard-mlops-sea"
  description = "Resource Group name"
}

variable "acr_name" {
  type        = string
  default     = "churnguardacr"
  description = "Azure Container Registry name"
}

variable "acr_sku" {
  type        = string
  default     = "Basic"
  description = "Azure Container Registry SKU (Basic for <= $75 student FinOps; Premium for Private Link & retention)"
  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.acr_sku)
    error_message = "acr_sku must be Basic, Standard, or Premium."
  }
}

variable "allowed_deployer_ips" {
  type        = list(string)
  default     = []
  description = "Optional deployer CIDR/IP allowlist for data-plane storage container creation outside VNet"
}

variable "api_key" {
  type        = string
  sensitive   = true
  description = "Serving API X-API-Key token injected at deploy time via TF_VAR_api_key"
}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags = {
    Project     = "ChurnGuard-MLOps"
    Environment = "Production"
    ManagedBy   = "Terraform"
  }
}

resource "azurerm_container_registry" "acr" {
  name                          = var.acr_name
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  sku                           = var.acr_sku
  admin_enabled                 = false
  public_network_access_enabled = var.acr_sku == "Premium" ? false : true

  dynamic "retention_policy" {
    for_each = var.acr_sku == "Premium" ? [1] : []
    content {
      days    = 7
      enabled = true
    }
  }
}

resource "azurerm_storage_account" "sa" {
  name                              = "stchurnguardsea2026"
  resource_group_name               = azurerm_resource_group.rg.name
  location                          = azurerm_resource_group.rg.location
  account_tier                      = "Standard"
  account_replication_type          = "LRS"
  min_tls_version                   = "TLS1_2"
  public_network_access_enabled     = false
  shared_access_key_enabled         = false
  allow_nested_items_to_be_public   = false
  infrastructure_encryption_enabled = true

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
    ip_rules       = var.allowed_deployer_ips
  }

  blob_properties {
    delete_retention_policy {
      days = 7
    }
  }

  queue_properties {
    logging {
      delete = true
      read   = true
      write  = true
      retention_policy {
        enabled = true
        days    = 7
      }
    }
  }
}

resource "azurerm_storage_container" "sc" {
  name                  = "churnguard-datasets"
  storage_account_id    = azurerm_storage_account.sa.id
  container_access_type = "private"
}

# Azure Managed Redis (AMR) - Replaces legacy Azure Cache for Redis (Basic C0 deprecated April 1, 2026)
resource "azurerm_redis_enterprise_cluster" "redis" {
  name                = "redis-churnguard-sea"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku_name            = "Balanced_B0"
  minimum_tls_version = "1.2"
}

resource "azurerm_redis_enterprise_database" "redis_db" {
  name              = "default"
  cluster_id        = azurerm_redis_enterprise_cluster.redis.id
  client_protocol   = "Encrypted"
  clustering_policy = "EnterpriseCluster"
  eviction_policy   = "VolatileLRU"
  port              = 10000
}

resource "azurerm_log_analytics_workspace" "law" {
  name                = "law-churnguard-mlops"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "cae" {
  name                       = "env-churnguard-mlops"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
}

resource "azurerm_user_assigned_identity" "app_identity" {
  name                = "id-churnguard-mlops-sea"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
}

resource "azurerm_role_assignment" "storage_blob_contributor" {
  scope                = azurerm_storage_account.sa.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
}

resource "azurerm_container_app" "app" {
  name                         = "churnguard-serving-app"
  container_app_environment_id = azurerm_container_app_environment.cae.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app_identity.id]
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.app_identity.id
  }

  secret {
    name  = "redis-access-key"
    value = azurerm_redis_enterprise_database.redis_db.primary_access_key
  }

  secret {
    name  = "api-key-token"
    value = var.api_key
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 0
    max_replicas = 5

    container {
      name   = "churnguard-serving"
      image  = "${azurerm_container_registry.acr.login_server}/churnguard-mlops:latest"
      cpu    = 1.0
      memory = "2.0Gi"

      env {
        name  = "APP_ENV"
        value = "production"
      }
      env {
        name        = "API_KEY"
        secret_name = "api-key-token"
      }
      env {
        name        = "KKBOX_API_KEY"
        secret_name = "api-key-token"
      }
      env {
        name  = "MLFLOW_TRACKING_URI"
        value = "sqlite:////app/data/kkbox_models/mlflow.db"
      }
      env {
        name  = "REDIS_HOST"
        value = azurerm_redis_enterprise_cluster.redis.hostname
      }
      env {
        name  = "REDIS_PORT"
        value = tostring(azurerm_redis_enterprise_database.redis_db.port)
      }
      env {
        name  = "REDIS_SSL"
        value = "true"
      }
      env {
        name        = "AZURE_REDIS_PASSWORD"
        secret_name = "redis-access-key"
      }
      env {
        name  = "AZURE_STORAGE_CONTAINER"
        value = azurerm_storage_container.sc.name
      }
      env {
        name  = "AZURE_STORAGE_ACCOUNT_URL"
        value = azurerm_storage_account.sa.primary_blob_endpoint
      }

      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }

      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/v1/health"
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.storage_blob_contributor
  ]
}

output "container_app_fqdn" {
  value       = azurerm_container_app.app.latest_revision_fqdn
  description = "Public FQDN of the deployed FastAPI serving application"
}

output "redis_ssl_port" {
  value       = azurerm_redis_enterprise_database.redis_db.port
  description = "Azure Managed Redis (AMR Balanced B0) SSL/TLS port (10000)"
}

output "redis_hostname" {
  value       = azurerm_redis_enterprise_cluster.redis.hostname
  description = "Azure Managed Redis (AMR Balanced B0) hostname"
}
