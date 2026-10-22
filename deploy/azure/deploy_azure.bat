@echo off
REM ==============================================================================
REM UIT IS402 - 1-CLICK AZURE CLOUD DEPLOYMENT SCRIPT (WINDOWS BATCH)
REM De tai 11: MLOps Customer Churn Prediction
REM Sinh vien: Nguyen Trong Khoi - MSSV: 22520695 | GV: ThS. Ha Le Hoai Trung
REM ==============================================================================

setlocal enabledelayedexpansion

echo ==============================================================================
echo   CHURNGUARD MLOPS - TRIEN KHAI LEN CLOUD MICROSOFT AZURE (1-CLICK DEPLOY)
echo ==============================================================================

set RESOURCE_GROUP=rg-churnguard-mlops-sea
set LOCATION=southeastasia
set ACR_NAME=churnguardacr
set APP_ENV=env-churnguard-mlops
set APP_NAME=churnguard-serving-app
set STORAGE_ACCOUNT=stchurnguardsea2026
set BLOB_CONTAINER=churnguard-datasets
set REDIS_NAME=redis-churnguard-sea
set IMAGE_TAG=v2.0.0

echo [*] Buoc 1: Kiem tra Azure CLI...
where az >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Azure CLI chua duoc cai dat tren he thong!
    echo Vui long cai dat Azure CLI tu: https://aka.ms/installazurecliwindows
    exit /b 1
)

echo [*] Buoc 2: Kiem tra trang thai dang nhap Azure...
az account show >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Chua dang nhap Azure. Dang mo trinh duyet de xac thuc...
    az login
    if %errorlevel% neq 0 (
        echo [ERROR] Dang nhap that bai. Dung tien trinh!
        exit /b 1
    )
)

echo [+] Da dang nhap Azure thanh cong.
for /f "tokens=*" %%i in ('az account show --query name -o tsv') do set SUB_NAME=%%i
echo     Subscription: !SUB_NAME!

echo [*] Buoc 3: Tao Resource Group (!RESOURCE_GROUP! tai !LOCATION!)...
az group create --name !RESOURCE_GROUP! --location !LOCATION! -o table

echo [*] Buoc 4: Khoi tao Azure Storage Account (!STORAGE_ACCOUNT!) va Blob Container (!BLOB_CONTAINER!)...
az storage account create --name !STORAGE_ACCOUNT! --resource-group !RESOURCE_GROUP! --location !LOCATION! --sku Standard_LRS --kind StorageV2 -o table
az storage container create --name !BLOB_CONTAINER! --account-name !STORAGE_ACCOUNT! -o table

echo [*] Buoc 5: Khoi tao Azure Cache for Redis (!REDIS_NAME! - Basic C0, SSL Port 6380)...
az redis create --name !REDIS_NAME! --resource-group !RESOURCE_GROUP! --location !LOCATION! --sku Basic --vm-size c0 -o table

echo [*] Buoc 6: Khoi tao Azure Container Registry (!ACR_NAME!)...
az acr create --resource-group !RESOURCE_GROUP! --name !ACR_NAME! --sku Basic --admin-enabled true -o table

echo [*] Buoc 7: Build & Push Docker image truc tiep len ACR (Cloud Native Build)...
az acr build --registry !ACR_NAME! --image churnguard-mlops:!IMAGE_TAG! --image churnguard-mlops:latest .

echo [*] Buoc 8: Khoi tao Azure Container Apps Managed Environment...
az containerapp env create --name !APP_ENV! --resource-group !RESOURCE_GROUP! --location !LOCATION! -o table

echo [*] Buoc 9: Trien khai Container App Serving (!APP_NAME!)...
for /f "tokens=*" %%p in ('az acr credential show --name !ACR_NAME! --query "passwords[0].value" -o tsv') do set ACR_PASSWORD=%%p

set CONTAINER_ENV=MLFLOW_TRACKING_URI=sqlite:////app/data/mlflow.db AZURE_STORAGE_CONTAINER=!BLOB_CONTAINER! REDIS_PORT=6380 REDIS_SSL=true
if defined AZURE_REDIS_HOST (
    echo [*] Phat hien Azure Redis: !AZURE_REDIS_HOST!
    set CONTAINER_ENV=!CONTAINER_ENV! REDIS_HOST=!AZURE_REDIS_HOST! AZURE_REDIS_PASSWORD=!AZURE_REDIS_PASSWORD!
)

az containerapp create ^
  --name !APP_NAME! ^
  --resource-group !RESOURCE_GROUP! ^
  --environment !APP_ENV! ^
  --image !ACR_NAME!.azurecr.io/churnguard-mlops:latest ^
  --registry-server !ACR_NAME!.azurecr.io ^
  --registry-username !ACR_NAME! ^
  --registry-password "!ACR_PASSWORD!" ^
  --target-port 8000 ^
  --ingress external ^
  --cpu 1.0 ^
  --memory 2.0Gi ^
  --min-replicas 0 ^
  --max-replicas 5 ^
  --env-vars !CONTAINER_ENV! ^
  -o table

echo ==============================================================================
echo [+] CHUC MUNG! HE THONG MLOPS DA DUOC TRIEN KHAI THANH CONG TREN AZURE CLOUD!
echo ==============================================================================
for /f "tokens=*" %%u in ('az containerapp show --name !APP_NAME! --resource-group !RESOURCE_GROUP! --query "properties.configuration.ingress.fqdn" -o tsv') do set APP_URL=%%u
echo   - Public Endpoint URL : https://!APP_URL!
echo   - Interactive Web UI  : https://!APP_URL!/ui
echo   - Swagger API Docs    : https://!APP_URL!/docs
echo   - Health Check        : https://!APP_URL!/health
echo ==============================================================================
