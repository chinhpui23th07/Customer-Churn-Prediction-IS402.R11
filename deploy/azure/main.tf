# Terraform Infrastructure as Code for ChurnGuard MLOps on Azure
# UIT IS402 Cloud Computing - Student: Nguyen Trong Khoi (22520695)

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80.0"
    }
  }
}

provider "azurerm" {
  features {}
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

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags = {
    Project     = "UIT-IS402-MLOps"
    Course      = "Cloud Computing"
    StudentId   = "22520695"
    Environment = "Production"
  }
}

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
}

resource "azurerm_storage_account" "sa" {
  name                     = "stchurnguardsea2026"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_storage_container" "sc" {
  name                  = "churnguard-datasets"
  storage_account_name  = azurerm_storage_account.sa.name
  container_access_type = "private"
}

resource "azurerm_redis_cache" "redis" {
  name                = "redis-churnguard-sea"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  capacity            = 0
  family              = "C"
  sku_name            = "Basic"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
    maxmemory_policy = "volatile-lru"
  }
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

resource "azurerm_container_app" "app" {
  name                         = "churnguard-serving-app"
  container_app_environment_id = azurerm_container_app_environment.cae.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

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
        name  = "MLFLOW_TRACKING_URI"
        value = "sqlite:////app/data/mlflow.db"
      }
      env {
        name  = "REDIS_HOST"
        value = azurerm_redis_cache.redis.hostname
      }
      env {
        name  = "REDIS_PORT"
        value = tostring(azurerm_redis_cache.redis.ssl_port)
      }
      env {
        name  = "REDIS_SSL"
        value = "true"
      }
      env {
        name  = "AZURE_STORAGE_CONTAINER"
        value = azurerm_storage_container.sc.name
      }
    }
  }
}

output "container_app_fqdn" {
  value       = azurerm_container_app.app.latest_revision_fqdn
  description = "Public FQDN of the deployed FastAPI serving application"
}

output "redis_ssl_port" {
  value       = azurerm_redis_cache.redis.ssl_port
  description = "Azure Cache for Redis SSL port (6380)"
}
