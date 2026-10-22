#!/usr/bin/env bash
# ==============================================================================
# UIT IS402 - 1-CLICK AZURE CLOUD DEPLOYMENT SCRIPT (BASH/LINUX/CI)
# De tai 11: MLOps Customer Churn Prediction
# Sinh vien: Nguyen Trong Khoi - MSSV: 22520695 | GV: ThS. Ha Le Hoai Trung
# ==============================================================================

set -euo pipefail

echo "=============================================================================="
echo "  CHURNGUARD MLOPS - TRIỂN KHAI LÊN CLOUD MICROSOFT AZURE (1-CLICK DEPLOY)"
echo "=============================================================================="

RESOURCE_GROUP="rg-churnguard-mlops-sea"
LOCATION="southeastasia"
ACR_NAME="acrchurnguard22520695"
APP_ENV="env-churnguard-mlops"
APP_NAME="churnguard-serving-app"
STORAGE_ACCOUNT="stchurnguardsea2026"
IMAGE_TAG="v2.0.0"

echo "[*] Bước 1: Kiểm tra Azure CLI..."
command -v az >/dev/null 2>&1 || { echo "[ERROR] Azure CLI chưa được cài đặt!"; exit 1; }

echo "[*] Bước 2: Kiểm tra xác thực Azure..."
az account show >/dev/null 2>&1 || { echo "[!] Chưa đăng nhập. Vui lòng chạy 'az login'."; exit 1; }

echo "[*] Bước 3: Tạo Resource Group ($RESOURCE_GROUP tại $LOCATION)..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" -o table

echo "[*] Bước 4: Khởi tạo Azure Storage Account ($STORAGE_ACCOUNT)..."
az storage account create --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" --sku Standard_LRS --kind StorageV2 -o table
az storage container create --name "churnguard-datasets" --account-name "$STORAGE_ACCOUNT" -o table

echo "[*] Bước 5: Khởi tạo Azure Container Registry ($ACR_NAME)..."
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic --admin-enabled true -o table

echo "[*] Bước 6: Build & Push Docker image lên ACR..."
az acr build --registry "$ACR_NAME" --image "churnguard-serving:$IMAGE_TAG" --image "churnguard-serving:latest" .

echo "[*] Bước 7: Khởi tạo Azure Container Apps Managed Environment..."
az containerapp env create --name "$APP_ENV" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" -o table

echo "[*] Bước 8: Triển khai Container App Serving ($APP_NAME)..."
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

CONTAINER_ENV="API_KEY=mlops-churn-secret-2026 MLFLOW_TRACKING_URI=sqlite:////app/data/mlflow.db"
if [ -n "${AZURE_REDIS_HOST:-}" ]; then
  echo "[*] Phát hiện Azure Redis: $AZURE_REDIS_HOST"
  CONTAINER_ENV="$CONTAINER_ENV REDIS_HOST=$AZURE_REDIS_HOST REDIS_PORT=6380 REDIS_SSL=true AZURE_REDIS_PASSWORD=${AZURE_REDIS_PASSWORD:-}"
fi

az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$APP_ENV" \
  --image "$ACR_NAME.azurecr.io/churnguard-serving:latest" \
  --registry-server "$ACR_NAME.azurecr.io" \
  --registry-username "$ACR_NAME" \
  --registry-password "$ACR_PASSWORD" \
  --target-port 8000 \
  --ingress external \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --env-vars $CONTAINER_ENV \
  -o table

APP_URL=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv)

echo "=============================================================================="
echo "[+] TRIỂN KHAI THÀNH CÔNG LÊN AZURE CLOUD!"
echo "    Public URL : https://$APP_URL"
echo "    Web UI     : https://$APP_URL/ui"
echo "    API Docs   : https://$APP_URL/docs"
echo "    Health     : https://$APP_URL/health"
echo "=============================================================================="
