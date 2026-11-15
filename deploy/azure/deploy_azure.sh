#!/usr/bin/env bash
# ==============================================================================
# CHURNGUARD MLOPS - 1-CLICK AZURE CLOUD DEPLOYMENT SCRIPT (BASH/LINUX/CI)
# Production-Grade Automated Cloud Infrastructure Provisioning
# ==============================================================================

set -euo pipefail

echo "=============================================================================="
echo "  CHURNGUARD MLOPS - TRIỂN KHAI LÊN CLOUD MICROSOFT AZURE (1-CLICK DEPLOY)"
echo "=============================================================================="

RESOURCE_GROUP="rg-churnguard-mlops-sea"
LOCATION="southeastasia"
ACR_NAME="churnguardacr"
APP_ENV="env-churnguard-mlops"
APP_NAME="churnguard-serving-app"
STORAGE_ACCOUNT="stchurnguardsea2026"
REDIS_NAME="redis-churnguard-sea"
IMAGE_TAG="v2.0.0"

: "${API_KEY:?ERROR: Bien moi truong API_KEY la bat buoc (khong dung secret mac dinh)!}"
KKBOX_API_KEY="${KKBOX_API_KEY:-$API_KEY}"
IDENTITY_NAME="id-churnguard-mlops-sea"

echo "[*] Bước 1: Kiểm tra Azure CLI..."
command -v az >/dev/null 2>&1 || { echo "[ERROR] Azure CLI chưa được cài đặt!"; exit 1; }

echo "[*] Bước 2: Kiểm tra xác thực Azure..."
az account show >/dev/null 2>&1 || { echo "[!] Chưa đăng nhập. Vui lòng chạy 'az login'."; exit 1; }

echo "[*] Bước 3: Tạo Resource Group ($RESOURCE_GROUP tại $LOCATION)..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" -o table

echo "[*] Bước 4: Khởi tạo Azure Storage Account ($STORAGE_ACCOUNT) via ARM Control Plane..."
az storage account create --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" --sku Standard_LRS --kind StorageV2 --allow-blob-public-access false --allow-shared-key-access false --min-tls-version TLS1_2 --public-network-access Disabled -o table
az rest --method PUT --uri "https://management.azure.com/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT/blobServices/default/containers/churnguard-datasets?api-version=2023-01-01" --body '{"properties":{"publicAccess":"None"}}' -o none

echo "[*] Bước 5: Khởi tạo Azure Managed Redis ($REDIS_NAME - Balanced_B0, SSL Port 10000)..."
az redisenterprise create --cluster-name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" --sku Balanced_B0 --minimum-tls 1.2 --eviction-policy VolatileLRU --client-protocol Encrypted --port 10000 -o table
AZURE_REDIS_HOST=$(az redisenterprise show --cluster-name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query hostName -o tsv)
AZURE_REDIS_PASSWORD=$(az redisenterprise database list-keys --cluster-name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query primaryKey -o tsv)

echo "[*] Bước 6: Khởi tạo Azure Container Registry ($ACR_NAME - Admin Disabled)..."
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic --admin-enabled false -o table

echo "[*] Bước 7: Build & Push Docker image lên ACR..."
az acr build --registry "$ACR_NAME" --image "churnguard-mlops:$IMAGE_TAG" --image "churnguard-mlops:latest" .

echo "[*] Bước 8: Khởi tạo Azure Container Apps Managed Environment & User-Assigned Identity..."
az containerapp env create --name "$APP_ENV" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" -o table
az identity create --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" -o table
IDENTITY_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)
IDENTITY_PRINCIPAL=$(az identity show --name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query principalId -o tsv)
ACR_ID=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)
STORAGE_ID=$(az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --query id -o tsv)
az role assignment create --assignee-object-id "$IDENTITY_PRINCIPAL" --assignee-principal-type ServicePrincipal --role AcrPull --scope "$ACR_ID" -o none
az role assignment create --assignee-object-id "$IDENTITY_PRINCIPAL" --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" --scope "$STORAGE_ID" -o none

echo "[*] Bước 9: Triển khai Container App Serving ($APP_NAME) với User-Assigned Managed Identity..."
STORAGE_BLOB_URL=$(az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --query primaryEndpoints.blob -o tsv)
az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$APP_ENV" \
  --image "$ACR_NAME.azurecr.io/churnguard-mlops:latest" \
  --user-assigned "$IDENTITY_ID" \
  --registry-server "$ACR_NAME.azurecr.io" \
  --registry-identity "$IDENTITY_ID" \
  --target-port 8000 \
  --ingress external \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 0 \
  --max-replicas 5 \
  --secrets api-key-token="$API_KEY" kkbox-auth-token="$KKBOX_API_KEY" redis-password="$AZURE_REDIS_PASSWORD" \
  --env-vars APP_ENV=production API_KEY=secretref:api-key-token KKBOX_API_KEY=secretref:kkbox-auth-token MLFLOW_TRACKING_URI=sqlite:////app/data/kkbox_models/mlflow.db AZURE_STORAGE_CONTAINER=churnguard-datasets AZURE_STORAGE_ACCOUNT_URL="$STORAGE_BLOB_URL" REDIS_HOST="$AZURE_REDIS_HOST" REDIS_PORT=10000 REDIS_SSL=true AZURE_REDIS_PASSWORD=secretref:redis-password \
  -o table

APP_URL=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv)

echo "=============================================================================="
echo "[+] TRIỂN KHAI THÀNH CÔNG LÊN AZURE CLOUD!"
echo "    Public URL : https://$APP_URL"
echo "    Demo UI    : https://$APP_URL/demo"
echo "    API Docs   : https://$APP_URL/docs"
echo "    Health     : https://$APP_URL/health"
echo "=============================================================================="
