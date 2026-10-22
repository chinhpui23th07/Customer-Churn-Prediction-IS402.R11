# Hướng Dẫn Triển Khai ChurnGuard MLOps Lên Microsoft Azure (1-Click Deployment)

> **Hệ thống:** ChurnGuard MLOps Level 2 Enterprise Platform  
> **Kiến trúc:** Cloud-Native Serverless & Low-Latency Feature Store  
> **Khu vực mục tiêu:** Đông Nam Á (Singapore - `southeastasia`, RTT < 50ms)  

---

## 1. Tổng Quan Kiến Trúc Đám Mây Azure (Target Architecture)

Hệ thống ChurnGuard MLOps được thiết kế sẵn sàng để đưa lên nền tảng Microsoft Azure với các dịch vụ chuyên dụng:

| Thành Phần Hệ Thống | Dịch Vụ Azure Tương Ứng | Mô Hình Dịch Vụ | Thông Số & Cấu Hình |
| :--- | :--- | :--- | :--- |
| **Model Serving & UI** | Azure Container Apps | PaaS / Serverless | 1.0 vCPU, 2.0 GiB RAM, Auto-scale 1-5 replicas |
| **Container Registry** | Azure Container Registry (ACR) | PaaS | Basic SKU, lưu trữ image Docker MLOps |
| **Feature Store Online** | Azure Cache for Redis | PaaS | C0 Basic (250 MB) / SQLite fallback |
| **DVC & Model Registry** | Azure Blob Storage | PaaS | Hot Tier, Container `churnguard-datasets` |
| **Giám sát & Logs** | Azure Log Analytics & App Insights | PaaS | Retention 30 days, phân tích latency |

---

## 2. Các Kịch Bản Triển Khai (3 Phương Thức Sẵn Sàng)

### Cách 1: Triển khai 1-Click tự động qua Azure CLI (Khuyên dùng)
Khi có tài khoản Cloud (Azure Subscription), chỉ cần chạy 1 lệnh duy nhất trên máy Windows:
```cmd
cmd /c "deploy\azure\deploy_azure.bat"
```
Hoặc trên môi trường Linux/macOS:
```bash
chmod +x deploy/azure/deploy_azure.sh
./deploy/azure/deploy_azure.sh
```

**Kịch bản tự động thực thi:**
1. Tự động kiểm tra đăng nhập (`az login`).
2. Khởi tạo Resource Group `rg-churnguard-mlops-sea` tại vùng Đông Nam Á (Singapore - `southeastasia`) để đạt độ trễ thấp nhất (< 50ms về Việt Nam).
3. Khởi tạo Azure Storage Account và Blob Container cho DVC.
4. Khởi tạo Azure Container Registry (ACR) và build Docker image trực tiếp trên Cloud.
5. Triển khai Container App Serving với Ingress mở ra Internet, gắn API Key `mlops-churn-secret-2026` và thiết lập Health check probe.
6. Xuất ra URL Public (`https://<app-name>.<region>.azurecontainerapps.io`).

---

### Cách 2: Triển khai qua Azure Resource Manager (ARM Template)
Sử dụng Azure CLI để deploy toàn bộ hạ tầng bằng template khai báo hạ tầng (IaC):
```cmd
cmd /c "az deployment group create --resource-group rg-churnguard-mlops-sea --template-file deploy/azure/arm_template.json"
```

---

### Cách 3: Triển khai chuẩn DevOps bằng Terraform
Nếu nhóm dùng công cụ Terraform:
```cmd
cd deploy/azure
terraform init
terraform plan
terraform apply -auto-approve
```

---

## 3. Kiểm Tra & Thẩm Định Sau Triển Khai (Verification Checklist)

Sau khi triển khai lên Azure, kiểm tra các endpoint:
1. **Health Check:** `curl -f https://<YOUR_APP_URL>/health`
2. **Interactive UI Bento Grid:** Mở trình duyệt truy cập `https://<YOUR_APP_URL>/ui`
3. **Swagger API Docs:** `https://<YOUR_APP_URL>/docs`
4. **Dự đoán thời gian thực:**
   ```bash
   curl -X POST "https://<YOUR_APP_URL>/predict" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: mlops-churn-secret-2026" \
     -d "{\"customer_id\": 1001, \"age\": 35.0, \"gender\": \"Male\", \"tenure\": 24.0, \"usage_frequency\": 18.0, \"support_calls\": 1.0, \"payment_delay\": 2.0, \"subscription_type\": \"Premium\", \"contract_length\": \"Annual\", \"total_spend\": 850.0, \"last_interaction\": 5.0}"
   ```
