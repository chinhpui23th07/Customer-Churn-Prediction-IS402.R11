# Báo Cáo Phân Tích Kiến Trúc Điện Toán Đám Mây & Dự Toán Chi Phí (Cloud Architecture & Quotas)

> **Dự án:** ChurnGuard MLOps - Hệ Thống Dự Đoán Khách Hàng Rời Bỏ Dịch Vụ  
> **Học phần:** Điện toán đám mây (Cloud Computing - IS402) - Đề tài Bài tập 11  
> **Mục tiêu:** Đáp ứng trọn vẹn Mục 1.4 và Mục 5.4 trong Rubric Đánh giá Bài tập Lớn.

---

## 1. Phân Loại Các Thành Phần Hệ Thống Theo Mô Hình Dịch Vụ Cloud (Mục 1.4 Rubric)

Hệ thống ChurnGuard MLOps được thiết kế theo kiến trúc Hybrid Cloud Native, tận dụng tối đa các mô hình dịch vụ từ hạ tầng đến phần mềm:

| Mô hình Cloud | Thành phần trong Hệ Thống | Công nghệ Cụ thể (Azure / AWS) | Vai trò & Trách nhiệm Kỹ thuật |
| :--- | :--- | :--- | :--- |
| **IaaS** *(Infrastructure as a Service)* | - VM Compute Nodes<br>- Docker Containers | - Azure Virtual Machines (Standard_D4s_v5)<br>- AWS EC2 (t3.xlarge / c5.xlarge) | Cung cấp tài nguyên tính toán thô (CPU, RAM, GPU) cho quá trình huấn luyện phân tán và worker nodes của Kubernetes/Docker. |
| **PaaS** *(Platform as a Service)* | - Feature Store<br>- Serving Containers<br>- Container Registry & Object Storage | - Azure Container Apps (ACA Serverless)<br>- Azure Cache for Redis (Basic C0 SSL 6380)<br>- Azure Container Registry (ACR Basic) & Azure Blob Storage | Quản lý môi trường thực thi container Serverless Scale-to-Zero, lưu trữ Docker Image và Feast Online Hot Cache tốc độ cao. |
| **FaaS** *(Function as a Service)* | - Event-Driven Triggers<br>- Retraining Alarms | - Azure Functions (Python runtime)<br>- AWS Lambda | Tự động kích hoạt luồng tái huấn luyện (Retraining Trigger) khi nhận webhook cảnh báo Data Drift vượt ngưỡng từ Evidently AI. |
| **SaaS** *(Software as a Service)* | - Experiment Tracking<br>- Version Control & CI/CD<br>- Monitoring Dashboards | - Databricks / MLflow Managed SaaS<br>- GitHub Actions (Self-hosted & Cloud Runners)<br>- Azure Monitor / Application Insights / Grafana Cloud | Quản trị vòng đời mô hình, theo dõi bảng biểu phân tích thời gian thực và quản lý quy trình cộng tác mã nguồn nhóm. |

---

## 2. So Sánh Hiệu Năng & Chi Phí: Máy Chủ Truyền Thống (On-Premise) vs Cloud (Mục 1.3 Rubric)

Dựa trên thực nghiệm xử lý tập dữ liệu 442,211 bản ghi (Track 1) và 42,448,764 bản ghi 5.28 GB (Track 2):

| Tiêu chí Đánh giá | Máy chủ Truyền thống (On-Premise Server) | Hệ thống Cloud Scalable (Azure / AWS) | Đánh giá Chênh lệch & Ưu thế |
| :--- | :--- | :--- | :--- |
| **Chi phí đầu tư ban đầu (CapEx)** | Rất cao (~$4,500 - $8,000 mua phần cứng máy chủ, UPS, router chuyên dụng) | $0 (Chuyển hoàn toàn sang chi phí vận hành OpEx theo giây/tháng) | **Cloud tiết kiệm 100% CapEx ban đầu**, phù hợp chu kỳ dự án ngắn hạn. |
| **Tốc độ Xử lý I/O (>4GB Scale)** | 14.82 giây (quét tuần tự định dạng CSV thô 5.28 GB, 364.8 MB/s) | 0.88 giây (truy vấn phân tích Parquet Snappy Out-of-Core, 6,144.0 MB/s) | **Parquet / Cloud nhanh hơn gấp 16.84x** (tiết kiệm 77.3% dung lượng đĩa trên tập 5.28 GB). |
| **Thời gian Train 4 Mô hình** | 4.8 phút (chạy tuần tự trên CPU máy cá nhân 4 cores) | 28.5 giây (chạy song song đa luồng trên Cloud Compute) | **Cloud tối ưu hơn 10x** về thời gian hoàn thành (Time-to-Market). |
| **Khả năng Mở rộng (Scalability)** | Mất 2-4 tuần để đặt mua thêm RAM/CPU phần cứng | Chỉ mất 1-2 phút tự động scale từ 0 lên 5 replicas bằng ACA KEDA | **Cloud linh hoạt tuyệt đối**, tự co về 0 (Scale-to-Zero) khi không có lượt truy cập. |

---

## 3. Dự Toán Chi Phí & Định Mức Quotas Cho Hệ Thống MLOps (Mục 5.4 Rubric)

### Bảng Dự Toán Chi Phí Vận Hành Hàng Tháng (Cloud FinOps TCO trên Microsoft Azure)

Kiến trúc thực tế sử dụng SQLite cục bộ (chế độ WAL) kết hợp đồng bộ Azure Blob Storage (`churnguard-datasets`) và Azure Cache for Redis (Basic C0) cho Feast Online Store, hoàn toàn không dùng dịch vụ RDBMS dư thừa, giúp tối ưu tổng chi phí TCO xuống còn **$74.67/month** (tiết kiệm đáng kể so với mức $90.75/month của mô hình RDBMS luôn bật):

| Tên Dịch Vụ Cloud Thực Tế | Cấu Hình / SKU Định Mức | Khối Lượng / Công Thức Tính Toán | Đơn Giá Azure | Chi Phí Tháng (USD) |
| :--- | :--- | :--- | :--- | :--- |
| **1. Azure Container Apps (ACA)** | `1.0 vCPU, 2.0 GiB RAM`, Serverless Scale-to-Zero (`minReplicas: 0, maxReplicas: 5`) | ~320 giờ hoạt động/tháng = `1,152,000 vCPU-s` ($27.65) + `2,304,000 GiB-s` ($6.91) | $0.000024 / vCPU-s & $0.000003 / GiB-s | **$34.56/month** |
| **2. Azure Cache for Redis** | Basic C0 (250 MB RAM, SSL Port `6380`, `enableNonSslPort: false`) | 730 giờ/tháng - Feast Online Hot Cache | $0.022 / giờ | **$16.06/month** |
| **3. Azure Container Registry (ACR)** | Basic Tier (`churnguardacr.azurecr.io/churnguard-mlops:latest`) | 1 Registry (10 GB lưu trữ Docker Image) | $0.167 / ngày | **$5.00/month** |
| **4. Azure Blob Storage (ADLS Gen2)** | Hot Tier LRS (Container `churnguard-datasets` + DVC Remote) | 50 GB Parquet Snappy + Model Artifacts & Operations | $0.0184 / GB + I/O | **$3.55/month** |
| **5. Azure Monitor & Log Analytics** | Application Insights & Log Analytics (`law-churnguard-mlops`) | 5 GB telemetry & drift metrics ingestion/tháng | $2.30 / GB | **$11.50/month** |
| **6. Azure Virtual Network & Egress** | VNet Ingress/Egress & Outbound Data Transfer | ~200 GB dữ liệu phản hồi REST API ra Internet | $0.02 / GB (trên mức miễn phí) | **$4.00/month** |
| **TỔNG CHI PHÍ TCO HÀNG THÁNG** | **Total Monthly Cloud TCO** | **6 dịch vụ cốt lõi khớp 100% IaC** | **Ngân sách cảnh báo: $100.00/month** | **$74.67/month (~1.87 triệu VNĐ)** |

---

## 4. Định Mức Hạn Ngạch Đám Mây (Cloud Quotas) & Cảnh Báo Ngân Sách (Mục 5.4 Rubric)

Để kiểm soát rủi ro chi phí vượt ngưỡng (Cost Spikes) và bảo đảm tính sẵn sàng, hệ thống thiết lập bảng định mức hạn ngạch (Quotas) trên Microsoft Azure:

| Tài nguyên / Dịch vụ Azure | Định mức Quota Đăng ký | Mức Tiêu Thụ Thiết Kế | Ngưỡng Cảnh Báo (Alert Threshold) | Hành Động Tự Động Hóa |
| :--- | :--- | :--- | :--- | :--- |
| **Compute vCPUs (Container Apps)** | 10 vCPUs / Region | 1.0 vCPU / replica (0 - 5 replicas) | 5.0 vCPUs (50%) | Khóa khởi tạo worker mới, gửi email MLOps Lead |
| **Container Apps Replicas** | Max 5 replicas | 0 - 3 replicas (Scale-to-Zero) | 4 replicas (80%) | Bật tính năng HTTP concurrency throttling (50 reqs) |
| **Azure Cache for Redis (Basic C0)** | 250 MB Memory | ~85 MB (Feast Online Features) | 200 MB (80%) | Kích hoạt chính sách trục xuất khóa `volatile-lru` |
| **Azure Blob Storage (`churnguard-datasets`)** | 5 TB / Subscription | ~50 GB (DVC Parquet & Artifacts) | 100 GB | Tự động chuyển tệp cũ >90 ngày sang Cool Tier |
| **Azure Budget Cost Alert** | **$100.00/month** | **$74.67/month** | $59.74 (80% TCO) & $74.67 (100% TCO) | Tự động hạ scale các cụm non-prod về 0 |

---

## 5. Kết Quả Đo Độ Trễ Thực Tế Đa Vùng Microsoft Azure (Mục 3.3 Rubric)

Thực nghiệm đo đạc độ trễ TCP Handshake và HTTPS Round-Trip Time (RTT) tới các cổng kết nối API Azure toàn cầu (ghi nhận từ `data/processed/region_latency_results.json`):

| Khu Vực Đám Mây (Region) | Azure Data Center | Khoảng Cách | Min RTT | Avg RTT | Đánh Giá Khả Năng SLA Phục Vụ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Đông Nam Á (Khuyến nghị)** | Singapore (`southeastasia`) | ~1,400 km | **26.19 ms** | **49.17 ms** | **Tối ưu (<50ms)** - Đặt API Serving & Feature Store chính |
| **Đông Á** | Hong Kong (`eastasia`) | ~1,500 km | **38.34 ms** | **47.98 ms** | **Tối ưu (<50ms)** - Vùng dự phòng nóng (Hot Standby) |
| **Nhật Bản** | Tokyo (`japaneast`) | ~4,300 km | 89.18 ms | 106.29 ms | Chấp nhận được (50-150ms) - Phục vụ khách hàng Đông Bắc Á |
| **Tây Âu** | Netherlands (`westeurope`) | ~9,400 km | 197.43 ms | 216.59 ms | Cần Azure Front Door / CDN Edge Acceleration (>150ms) |
| **Bắc Mỹ** | N. Virginia (`eastus`) | ~14,200 km | 238.57 ms | 255.60 ms | Cần Azure Front Door / CDN Edge Acceleration (>150ms) |

---

## 6. Phân Chia Vai Trò Nhóm & Ma Trận Phân Quyền IAM RBAC (Teamwork Governance)

Hệ thống phân định rành mạch trách nhiệm vận hành theo mô hình phân quyền dựa trên vai trò (Role-Based Access Control):

| Thành viên / Vai trò | Trách nhiệm Kỹ thuật Chính | Phạm vi Mã nguồn | Quyền Hạn Azure IAM RBAC |
| :--- | :--- | :--- | :--- |
| **MLOps Lead (Nguyễn Trọng Khôi - 23520783)** | Thiết kế kiến trúc, điều phối CI/CD, tối ưu hóa TCO & nghiệm thu toàn diện | `src/api/`, `configs/`, `.github/`, `deploy/` | **Subscription Contributor / Cost Management Budget Admin** |
| **Data Engineer** | Quản trị DVC, Feast Feature Store Offline/Online, Out-of-Core ETL | `src/data/`, `src/features/` | **Storage Blob Data Contributor, Redis Cache Contributor** |
| **ML Engineer** | Huấn luyện mô hình, Optuna Tuning, Model Registry & XAI (SHAP) | `src/models/` | **Azure ML Data Scientist / AcrPush & Registry Contributor** |
| **DevOps / MLOps SRE** | Giám sát Data Drift (Evidently AI), Docker orchestration, Web UI | `src/monitoring/`, `src/web/` | **Container Apps Operator, Monitoring Metrics Publisher** |

---

> [!TIP]
> **Chiến lược Tối ưu Hóa Chi Phí (Cloud FinOps):**
> 1. Thiết lập **Serverless Scale-to-Zero (`minReplicas: 0`)** cho Azure Container Apps giúp chi phí compute chỉ phát sinh khi có lưu lượng thực tế (~320 giờ/tháng = **$34.56/month**).
> 2. Sử dụng định dạng **Apache Parquet (Snappy)** giúp cắt giảm **73.0% - 77.3% dung lượng lưu trữ** và chi phí truyền tải dữ liệu so với CSV thuần.
> 3. Sử dụng **Azure Cache for Redis Basic C0 ($16.06/month)** kết hợp SQLite WAL cục bộ thay vì dịch vụ cơ sở dữ liệu quan hệ đắt đỏ, đưa tổng TCO toàn hệ thống về mức **$74.67/month** (nằm gọn dưới ngưỡng cảnh báo ngân sách **$100.00/month**).
