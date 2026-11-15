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

echo "[*] Bước 1: Kiểm tra Azure CLI..."
command -v az >/dev/null 2>&1 || { echo "[ERROR] Azure CLI chưa được cài đặt!"; exit 1; }

echo "[*] Bước 2: Kiểm tra xác thực Azure..."
az account show >/dev/null 2>&1 || { echo "[!] Chưa đăng nhập. Vui lòng chạy 'az login'."; exit 1; }

echo "[*] Bước 3: Tạo Resource Group ($RESOURCE_GROUP tại $LOCATION)..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" -o table

echo "[*] Bước 4: Khởi tạo Azure Storage Account ($STORAGE_ACCOUNT)..."
az storage account create --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" --sku Standard_LRS --kind StorageV2 --allow-blob-public-access false --min-tls-version TLS1_2 --public-network-access Disabled -o table
az storage container create --name "churnguard-datasets" --account-name "$STORAGE_ACCOUNT" --auth-mode login -o table

echo "[*] Bước 5: Khởi tạo Azure Managed Redis ($REDIS_NAME - Balanced_B0, SSL Port 10000)..."
az redisenterprise create --cluster-name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" --sku Balanced_B0 --minimum-tls 1.2 --eviction-policy VolatileLRU --client-protocol Encrypted --port 10000 -o table
AZURE_REDIS_HOST=$(az redisenterprise show --cluster-name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query hostName -o tsv)
AZURE_REDIS_PASSWORD=$(az redisenterprise database list-keys --cluster-name "$REDIS_NAME" --resource-group "$RESOURCE_GROUP" --query primaryKey -o tsv)

echo "[*] Bước 6: Khởi tạo Azure Container Registry ($ACR_NAME - Admin Disabled)..."
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic --admin-enabled false -o table

echo "[*] Bước 7: Build & Push Docker image lên ACR..."
az acr build --registry "$ACR_NAME" --image "churnguard-mlops:$IMAGE_TAG" --image "churnguard-mlops:latest" .

echo "[*] Bước 8: Khởi tạo Azure Container Apps Managed Environment..."
az containerapp env create --name "$APP_ENV" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" -o table

echo "[*] Bước 9: Triển khai Container App Serving ($APP_NAME) với Managed Identity..."
az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$APP_ENV" \
  --image "$ACR_NAME.azurecr.io/churnguard-mlops:latest" \
  --system-assigned \
  --target-port 8000 \
  --ingress external \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 0 \
  --max-replicas 5 \
  --secrets api-key-secret="$API_KEY" redis-password="$AZURE_REDIS_PASSWORD" \
  --env-vars APP_ENV=production API_KEY=secretref:api-key-secret MLFLOW_TRACKING_URI=sqlite:////app/data/mlflow.db AZURE_STORAGE_CONTAINER=churnguard-datasets REDIS_HOST="$AZURE_REDIS_HOST" REDIS_PORT=10000 REDIS_SSL=true AZURE_REDIS_PASSWORD=secretref:redis-password \
  -o table

APP_MI_ID=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query identity.principalId -o tsv)
ACR_ID=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)
az role assignment create --assignee-object-id "$APP_MI_ID" --assignee-principal-type ServicePrincipal --role AcrPull --scope "$ACR_ID" -o none

APP_URL=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv)

echo "=============================================================================="
echo "[+] TRIỂN KHAI THÀNH CÔNG LÊN AZURE CLOUD!"
echo "    Public URL : https://$APP_URL"
echo "    Demo UI    : https://$APP_URL/demo"
echo "    API Docs   : https://$APP_URL/docs"
echo "    Health     : https://$APP_URL/health"
echo "=============================================================================="
