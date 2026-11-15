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
set IDENTITY_NAME=id-churnguard-mlops-sea
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

echo [*] Buoc 4: Khoi tao Azure Storage Account (!STORAGE_ACCOUNT!) va Blob Container qua ARM Control Plane...
az storage account create --name !STORAGE_ACCOUNT! --resource-group !RESOURCE_GROUP! --location !LOCATION! --sku Standard_LRS --kind StorageV2 --allow-blob-public-access false --allow-shared-key-access false --min-tls-version TLS1_2 --public-network-access Disabled -o table
for /f "tokens=*" %%s in ('az account show --query id -o tsv') do set SUB_ID=%%s
az rest --method PUT --uri "https://management.azure.com/subscriptions/!SUB_ID!/resourceGroups/!RESOURCE_GROUP!/providers/Microsoft.Storage/storageAccounts/!STORAGE_ACCOUNT!/blobServices/default/containers/!BLOB_CONTAINER!?api-version=2023-01-01" --body "{\"properties\":{\"publicAccess\":\"None\"}}" -o none

echo [*] Buoc 5: Khoi tao Azure Managed Redis (!REDIS_NAME! - AMR Balanced_B0, SSL Port 10000)...
az redisenterprise create --cluster-name !REDIS_NAME! --resource-group !RESOURCE_GROUP! --location !LOCATION! --sku Balanced_B0 --minimum-tls 1.2 --eviction-policy VolatileLRU --client-protocol Encrypted --port 10000 -o table
for /f "tokens=*" %%h in ('az redisenterprise show --cluster-name !REDIS_NAME! --resource-group !RESOURCE_GROUP! --query hostName -o tsv') do set AZURE_REDIS_HOST=%%h
for /f "tokens=*" %%k in ('az redisenterprise database list-keys --cluster-name !REDIS_NAME! --resource-group !RESOURCE_GROUP! --query primaryKey -o tsv') do set AZURE_REDIS_PASSWORD=%%k

echo [*] Buoc 6: Khoi tao Azure Container Registry (!ACR_NAME! - Admin Disabled)...
az acr create --resource-group !RESOURCE_GROUP! --name !ACR_NAME! --sku Basic --admin-enabled false -o table

echo [*] Buoc 7: Build & Push Docker image truc tiep len ACR (Cloud Native Build)...
az acr build --registry !ACR_NAME! --image churnguard-mlops:!IMAGE_TAG! --image churnguard-mlops:latest .

echo [*] Buoc 8: Khoi tao Azure Container Apps Managed Environment & User-Assigned Identity...
az containerapp env create --name !APP_ENV! --resource-group !RESOURCE_GROUP! --location !LOCATION! -o table
az identity create --name !IDENTITY_NAME! --resource-group !RESOURCE_GROUP! --location !LOCATION! -o table
for /f "tokens=*" %%i in ('az identity show --name !IDENTITY_NAME! --resource-group !RESOURCE_GROUP! --query id -o tsv') do set IDENTITY_ID=%%i
for /f "tokens=*" %%p in ('az identity show --name !IDENTITY_NAME! --resource-group !RESOURCE_GROUP! --query principalId -o tsv') do set IDENTITY_PRINCIPAL=%%p
for /f "tokens=*" %%r in ('az acr show --name !ACR_NAME! --resource-group !RESOURCE_GROUP! --query id -o tsv') do set ACR_ID=%%r
for /f "tokens=*" %%a in ('az storage account show --name !STORAGE_ACCOUNT! --resource-group !RESOURCE_GROUP! --query id -o tsv') do set STORAGE_ID=%%a
for /f "tokens=*" %%b in ('az storage account show --name !STORAGE_ACCOUNT! --resource-group !RESOURCE_GROUP! --query primaryEndpoints.blob -o tsv') do set STORAGE_BLOB_URL=%%b
az role assignment create --assignee-object-id !IDENTITY_PRINCIPAL! --assignee-principal-type ServicePrincipal --role AcrPull --scope !ACR_ID! -o none
az role assignment create --assignee-object-id !IDENTITY_PRINCIPAL! --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" --scope !STORAGE_ID! -o none

echo [*] Buoc 9: Trien khai Container App Serving (!APP_NAME!) voi User-Assigned Managed Identity...
if not defined API_KEY (
    echo [ERROR] Bien moi truong API_KEY chua duoc thiet lap! Hay chay: set API_KEY=<your-strong-secret>
    exit /b 1
)
if not defined KKBOX_API_KEY set KKBOX_API_KEY=!API_KEY!
set CONTAINER_ENV=APP_ENV=production API_KEY=secretref:api-key-token KKBOX_API_KEY=secretref:kkbox-auth-token MLFLOW_TRACKING_URI=sqlite:////app/data/kkbox_models/mlflow.db AZURE_STORAGE_CONTAINER=!BLOB_CONTAINER! AZURE_STORAGE_ACCOUNT_URL=!STORAGE_BLOB_URL! REDIS_HOST=!AZURE_REDIS_HOST! REDIS_PORT=10000 REDIS_SSL=true AZURE_REDIS_PASSWORD=secretref:redis-password

az containerapp create ^
  --name !APP_NAME! ^
  --resource-group !RESOURCE_GROUP! ^
  --environment !APP_ENV! ^
  --image !ACR_NAME!.azurecr.io/churnguard-mlops:latest ^
  --user-assigned !IDENTITY_ID! ^
  --registry-server !ACR_NAME!.azurecr.io ^
  --registry-identity !IDENTITY_ID! ^
  --target-port 8000 ^
  --ingress external ^
  --cpu 1.0 ^
  --memory 2.0Gi ^
  --min-replicas 0 ^
  --max-replicas 5 ^
  --secrets api-key-token="!API_KEY!" kkbox-auth-token="!KKBOX_API_KEY!" redis-password="!AZURE_REDIS_PASSWORD!" ^
  --env-vars !CONTAINER_ENV! ^
  -o table

echo ==============================================================================
echo [+] CHUC MUNG! HE THONG MLOPS DA DUOC TRIEN KHAI THANH CONG TREN AZURE CLOUD!
echo ==============================================================================
for /f "tokens=*" %%u in ('az containerapp show --name !APP_NAME! --resource-group !RESOURCE_GROUP! --query "properties.configuration.ingress.fqdn" -o tsv') do set APP_URL=%%u
echo   - Public Endpoint URL : https://!APP_URL!
echo   - Interactive Demo UI : https://!APP_URL!/demo
echo   - Swagger API Docs    : https://!APP_URL!/docs
echo   - Health Check        : https://!APP_URL!/health
echo ==============================================================================
