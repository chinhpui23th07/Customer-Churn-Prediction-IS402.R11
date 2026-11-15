@echo off
REM ==============================================================================
REM CHURNGUARD MLOPS - 1-CLICK AZURE CLOUD DEPLOYMENT SCRIPT (WINDOWS BATCH)
REM Production-Grade Automated Cloud Infrastructure Provisioning
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
az storage account create --name !STORAGE_ACCOUNT! --resource-group !RESOURCE_GROUP! --location !LOCATION! --sku Standard_LRS --kind StorageV2 --allow-blob-public-access false --min-tls-version TLS1_2 --public-network-access Disabled -o table
az storage container create --name !BLOB_CONTAINER! --account-name !STORAGE_ACCOUNT! --auth-mode login -o table

echo [*] Buoc 5: Khoi tao Azure Managed Redis (!REDIS_NAME! - AMR Balanced_B0, SSL Port 10000)...
az redisenterprise create --cluster-name !REDIS_NAME! --resource-group !RESOURCE_GROUP! --location !LOCATION! --sku Balanced_B0 --minimum-tls 1.2 --eviction-policy VolatileLRU --client-protocol Encrypted --port 10000 -o table
for /f "tokens=*" %%h in ('az redisenterprise show --cluster-name !REDIS_NAME! --resource-group !RESOURCE_GROUP! --query hostName -o tsv') do set AZURE_REDIS_HOST=%%h
for /f "tokens=*" %%k in ('az redisenterprise database list-keys --cluster-name !REDIS_NAME! --resource-group !RESOURCE_GROUP! --query primaryKey -o tsv') do set AZURE_REDIS_PASSWORD=%%k

echo [*] Buoc 6: Khoi tao Azure Container Registry (!ACR_NAME! - Admin Disabled)...
az acr create --resource-group !RESOURCE_GROUP! --name !ACR_NAME! --sku Basic --admin-enabled false -o table

echo [*] Buoc 7: Build & Push Docker image truc tiep len ACR (Cloud Native Build)...
az acr build --registry !ACR_NAME! --image churnguard-mlops:!IMAGE_TAG! --image churnguard-mlops:latest .

echo [*] Buoc 8: Khoi tao Azure Container Apps Managed Environment...
az containerapp env create --name !APP_ENV! --resource-group !RESOURCE_GROUP! --location !LOCATION! -o table

echo [*] Buoc 9: Trien khai Container App Serving (!APP_NAME!) voi Managed Identity (Zero Plaintext Secrets)...
if not defined API_KEY (
    echo [ERROR] Bien moi truong API_KEY chua duoc thiet lap! Hay chay: set API_KEY=<your-strong-secret>
    exit /b 1
)
set CONTAINER_ENV=APP_ENV=production API_KEY=secretref:api-key-secret MLFLOW_TRACKING_URI=sqlite:////app/data/mlflow.db AZURE_STORAGE_CONTAINER=!BLOB_CONTAINER! REDIS_HOST=!AZURE_REDIS_HOST! REDIS_PORT=10000 REDIS_SSL=true AZURE_REDIS_PASSWORD=secretref:redis-password

az containerapp create ^
  --name !APP_NAME! ^
  --resource-group !RESOURCE_GROUP! ^
  --environment !APP_ENV! ^
  --image !ACR_NAME!.azurecr.io/churnguard-mlops:latest ^
  --system-assigned ^
  --target-port 8000 ^
  --ingress external ^
  --cpu 1.0 ^
  --memory 2.0Gi ^
  --min-replicas 0 ^
  --max-replicas 5 ^
  --secrets api-key-secret="!API_KEY!" redis-password="!AZURE_REDIS_PASSWORD!" ^
  --env-vars !CONTAINER_ENV! ^
  -o table

for /f "tokens=*" %%i in ('az containerapp show --name !APP_NAME! --resource-group !RESOURCE_GROUP! --query identity.principalId -o tsv') do set APP_MI_ID=%%i
for /f "tokens=*" %%r in ('az acr show --name !ACR_NAME! --resource-group !RESOURCE_GROUP! --query id -o tsv') do set ACR_ID=%%r
az role assignment create --assignee-object-id !APP_MI_ID! --assignee-principal-type ServicePrincipal --role AcrPull --scope !ACR_ID! -o none

echo ==============================================================================
echo [+] CHUC MUNG! HE THONG MLOPS DA DUOC TRIEN KHAI THANH CONG TREN AZURE CLOUD!
echo ==============================================================================
for /f "tokens=*" %%u in ('az containerapp show --name !APP_NAME! --resource-group !RESOURCE_GROUP! --query "properties.configuration.ingress.fqdn" -o tsv') do set APP_URL=%%u
echo   - Public Endpoint URL : https://!APP_URL!
echo   - Interactive Demo UI : https://!APP_URL!/demo
echo   - Swagger API Docs    : https://!APP_URL!/docs
echo   - Health Check        : https://!APP_URL!/health
echo ==============================================================================
