# Báo Cáo Phân Tích Kiến Trúc Điện Toán Đám Mây & Dự Toán Chi Phí (Cloud Architecture & FinOps TCO)

> **Dự án:** ChurnGuard MLOps Level 2 Platform  
> **Kiến trúc:** Hybrid Cloud Native (Serverless Container Apps + In-Memory Feature Store)  
> **Mục tiêu:** Tối ưu hóa hiệu năng, độ trễ mạng đa vùng và chi phí vận hành TCO trên Microsoft Azure và đối chuẩn Đa Đám Mây (Multi-Cloud FinOps Benchmark)  

---

## 1. Phân Loại Các Thành Phần Hệ Thống Theo Mô Hình Dịch Vụ Cloud (IaaS, PaaS, FaaS, SaaS)

Hệ thống ChurnGuard MLOps được thiết kế theo kiến trúc Hybrid Cloud Native, phân tách rành mạch theo các mô hình dịch vụ đám mây từ hạ tầng đến phần mềm:

| Mô hình Cloud | Thành phần trong Hệ Thống | Công nghệ Cụ thể (Azure / Multi-Cloud) | Vai trò & Trách nhiệm Kỹ thuật |
| :--- | :--- | :--- | :--- |
| **IaaS** *(Infrastructure as a Service)* | - VM Compute Nodes<br>- Docker Hosts | - Azure Virtual Machines (Standard_D4s_v5)<br>- AWS EC2 (m6i.xlarge, t4g.xlarge)<br>- OCI VM.Standard3.Flex | Cung cấp tài nguyên tính toán thô (CPU, RAM) cho quá trình huấn luyện phân tán, trích xuất đặc trưng Out-of-Core quy mô lớn. |
| **PaaS** *(Platform as a Service)* | - Serving Containers<br>- Feature Store Cache<br>- Registry & Storage | - Azure Container Apps (ACA Serverless)<br>- Azure Managed Redis (AMR Balanced B0) / Valkey 8.0<br>- Azure Container Registry (ACR) & Azure Blob Storage (LRS) | Môi trường thực thi container Serverless Scale-to-Zero, quản lý Feast Online Hot Cache tốc độ cao và lưu trữ Artifacts. |
| **FaaS** *(Function as a Service)* | - Event-Driven Triggers<br>- Automated Retraining | - Azure Functions (Python runtime)<br>- AWS Lambda | Tự động kích hoạt luồng tái huấn luyện (Retraining Trigger) khi nhận webhook cảnh báo Data Drift vượt ngưỡng từ Evidently AI. |
| **SaaS** *(Software as a Service)* | - Experiment Tracking<br>- CI/CD Automation<br>- Observability Platform | - MLflow Tracking Server<br>- GitHub Actions Cloud Runners<br>- Azure Monitor / Application Insights / Grafana | Quản trị vòng đời mô hình, điều phối quy trình tích hợp liên tục và giám sát bảng biểu số liệu thời gian thực. |

---

## 2. So Sánh Hiệu Năng & Chi Phí: Máy Chủ Truyền Thống (On-Premise) vs Cloud

Dựa trên thực nghiệm xử lý tập dữ liệu lớn KKBox Customer Churn 7.52 GB (442,211,685 dòng trên 32 tệp Parquet Zstandard):

| Tiêu chí Đánh giá | Máy chủ Truyền thống (On-Premise Server) | Hệ thống Cloud Scalable (Azure / AWS) | Đánh giá Chênh lệch & Ưu thế |
| :--- | :--- | :--- | :--- |
| **Chi phí đầu tư ban đầu (CapEx)** | Rất cao (~$4,500 - $8,000 mua máy chủ vật lý, UPS, thiết bị mạng) | $0 (Chuyển đổi hoàn toàn sang chi phí vận hành OpEx theo nhu cầu) | **Cloud tiết kiệm 100% CapEx ban đầu**, tối ưu hóa dòng tiền doanh nghiệp. |
| **Tốc độ Xử lý I/O (>4GB Scale)** | 84.50 giây (quét tuần tự text/CSV thô >30 GB, ~355 MB/s, nguy cơ cạn bộ nhớ) | 5.61 giây (lát cắt 37,629,251 dòng Parquet Zstandard Out-of-Core qua DuckDB; toàn tập manifest 7.52 GB / 32 tệp / 442,211,685 dòng) | **Parquet / Cloud nhanh hơn 15.06x** (tiết kiệm 77.3% dung lượng đĩa và nén 3.7x). |
| **Thời gian Huấn luyện & ETL** | 52.4 phút (chạy đơn luồng trên máy trạm 4 cores, thắt nút cổ chai I/O) | 4.8 phút (chạy song song đa luồng trên Azure Standard_D4s_v5 Compute) | **Cloud tối ưu hơn 10.9x** về chu kỳ phát triển và thời gian phản hồi (Time-to-Market). |
| **Khả năng Co giãn (Scalability)** | Mất từ 2 đến 4 tuần để đặt hàng và nâng cấp phần cứng | Chỉ mất 1-2 phút tự động scale từ 0 lên 5 replicas bằng ACA KEDA | **Cloud linh hoạt tuyệt đối**, tự co về 0 (Scale-to-Zero) khi không có tải. |

---

## 3. Dự Toán Chi Phí Chi Tiết & FinOps TCO Trên Nền Tảng Microsoft Azure

Nhằm khắc phục thời điểm Microsoft ngừng hỗ trợ khởi tạo Azure Cache for Redis Basic C0 (Deprecation ngày 01/04/2026), kiến trúc đã chuyển đổi toàn diện sang **Azure Managed Redis (AMR Balanced B0)** kết hợp containerized **Valkey 8.0** trên Azure Container Apps và lưu trữ **Standard_LRS**. Hệ thống đồng bộ SQLite WAL cục bộ và Azure Blob Storage (`churnguard-datasets`), tối ưu hóa tổng chi phí sở hữu TCO xuống mức **$70.61/month** (baseline trong IaC theo `finops_infracost_scan.py`) và **$11.22/month** (kịch bản Pilot Serverless Scale-to-Zero thực tế).

### 3.1. Bảng Dự Toán Chi Phí Định Mức Vận Hành Hàng Tháng (Azure Production Baseline)

| Tên Dịch Vụ Cloud Thực Tế | Cấu Hình / SKU Định Mức | Khối Lượng / Công Thức Tính Toán | Đơn Giá Azure Retail | Chi Phí Tháng (USD) |
| :--- | :--- | :--- | :--- | :--- |
| **1. Azure Container Apps (ACA)** | `1.0 vCPU, 2.0 GiB RAM`, Serverless Scale-to-Zero (`minReplicas: 0, maxReplicas: 5`) | Baseline tải chuẩn (~100k req/tháng, ~480 giờ active/tháng trừ Free Grant `180k vCPU-s` & `360k GiB-s`) | $0.000024 / vCPU-s & $0.000003 / GiB-s | **$46.80/month** |
| **2. Azure Managed Redis (AMR)** | Balanced B0 Non-HA (TLS Port `10000`) / Valkey 8.0 trên ACA | 730 giờ/tháng - Feast Online In-Memory Cache | $0.0164 / giờ | **$12.00/month** |
| **3. Azure Container Registry (ACR)** | Basic Tier (`churnguardacr.azurecr.io/churnguard-mlops:latest`) | 1 Registry (10 GB lưu trữ Docker Image) | $0.167 / ngày | **$5.00/month** |
| **4. Azure Blob Storage (ADLS Gen2)** | Hot Tier Standard_LRS (`churnguard-datasets` + DVC Remote) | ~100 GB Parquet + Model Artifacts & Checkpoints + I/O | $0.0184 / GB + giao dịch I/O | **$2.40/month** |
| **5. Azure Monitor & Log Analytics** | Application Insights & Log Analytics (`law-churnguard-mlops`, `PerGB2018`) | 6.5 GB ingestion/tháng = 5.0 GB Free Grant + 1.5 GB tính phí | $2.94 / GB (Southeast Asia) | **$4.41/month** |
| **6. Internet Egress Bandwidth** | Outbound Data Transfer | <= 100 GB/tháng (nằm 100% trong hạn mức miễn phí 100 GB/tháng) | $0.00 (Free Grant <= 100 GB) | **$0.00/month** |
| **TỔNG CHI PHÍ TCO HÀNG THÁNG** | **Total Monthly Cloud TCO (Azure Production Baseline)** | **6 dịch vụ cốt lõi khớp 100% IaC (`reports/infracost_breakdown.json`)** | **Khung ngân sách kế hoạch: < $75.00/month** | **$70.61/month (~1.79 triệu VNĐ)** |

### 3.2. Quy Đổi Đơn Giá Chi Tiết & Hạn Mức Miễn Phí (Azure Monthly Free Grants)
- **Đơn giá tính toán ACA vCPU:** $\$0.000024 / \text{vCPU-s} \times 3,600\text{ s/h} = \mathbf{\$0.0864 / \text{vCPU-hour}}$.
- **Đơn giá tính toán ACA RAM:** $\$0.000003 / \text{GiB-s} \times 3,600\text{ s/h} = \mathbf{\$0.0108 / \text{GiB-hour}}$.
- **Hạn mức miễn phí hàng tháng (Free Tier Grants):**
  * **Azure Container Apps:** Miễn phí **180,000 vCPU-seconds** và **360,000 GiB-seconds** mỗi tháng (tương đương 50 vCPU-giờ và 100 GiB-giờ miễn phí).
  * **Azure Monitor / Log Analytics:** Miễn phí **5.0 GB dữ liệu ingestion/tháng** đầu tiên trên mỗi workspace.
  * **Internet Egress:** Miễn phí **100 GB dữ liệu truyền ra ngoài Internet/tháng** đầu tiên cho toàn subscription.

### 3.3. So Sánh Kịch Bản: Tải Đỉnh 24/7 vs Serverless Scale-to-Zero Thực Tế

| Dịch Vụ Cloud | Kịch Bản 1: Tải Đỉnh 24/7 (Worst Case) | Kịch Bản 2: Production Scale-to-Zero (Realistic) | Cơ Chế FinOps Tối Ưu Hóa |
| :--- | :---: | :---: | :--- |
| **Azure Container Apps (ACA)** | **$150.12** (2 replicas 720h liên tục, ~1,440h sau Free Grant) | **$1.08** (60 giờ active/tháng = 216k vCPU-s, trừ 180k Free Grant) | KEDA co về 0 replica khi không có request, hấp thụ 180k vCPU-s free |
| **Azure Managed Redis (AMR) / Valkey** | **$12.00** (AMR Balanced B0 730h) | **$5.00** (Valkey 8.0 trên ACA / AMR dev) | Hot cache cho Feast Online, SQLite WAL fallback |
| **Azure Monitor & Log Analytics**| **$6.90** (8 GB ingestion, tính phí 3 GB @ $2.30/GB) | **$0.00** (3.2 GB ingestion) | 100% nằm trong hạn mức 5 GB/tháng miễn phí của Azure |
| **Azure Container Registry (ACR)**| **$5.00** (Basic Tier 10 GB) | **$5.00** (Basic Tier 10 GB) | Lưu trữ Docker Serving Image chuẩn CI/CD |
| **Azure Blob Storage (ADLS Gen2)**| **$1.20** (50 GB Hot LRS + I/O) | **$0.14** (7.52 GB Parquet Zstandard @ $0.0184/GB) | Parquet Zstandard nén 3.7x, tiết kiệm 77% phí đĩa và I/O |
| **Internet Egress Bandwidth** | **$1.74** (120 GB outbound, tính phí 20 GB @ $0.087/GB) | **$0.00** (18 GB outbound) | 100% nằm trong hạn mức 100 GB/tháng miễn phí của Azure |
| **TỔNG CHI PHÍ THỰC TẾ** | **$176.96 / month** | **$11.22 / month** | **Tiết kiệm 93.7% so với tải đỉnh (84.1% so với baseline $70.61)** |

---

## 4. Đối Chuẩn Định Giá Đa Đám Mây Toàn Diện (Multi-Cloud Pricing & Benchmark Evidence)

Bảng đối chuẩn tổng hợp bảng giá chính thức, công thức tính toán và đường dẫn xác thực (canonical URLs) cho cả 6 nhà cung cấp điện toán đám mây toàn cầu và nội địa:

### 4.1. Bảng Tổng Hợp Đơn Giá & Chi Phí Vận Hành Hàng Tháng (6 Cloud Providers)

| # | Nhà Cung Cấp Đám Mây | Dịch Vụ & Cấu Hình Định Mức | Đơn Giá Chi Tiết & Công Thức Tính Toán | Chi Phí Vận Hành Tháng (TCO) | Nguồn Trích Dẫn & URL Công Khai Chính Thức |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Microsoft Azure** | - ACA Serverless (1 vCPU, 2 GiB)<br>- Azure Blob LRS Hot (~100 GB)<br>- AMR Balanced B0 (TLS 10000)<br>- ACR Basic (10 GB) | - ACA: $0.000024/vCPU-s & $0.000003/GiB-s (Free grant: 180k vCPU-s, 360k GiB-s)<br>- Blob LRS: $0.0184/GB<br>- AMR B0: $0.0164/h ($12.00/mo)<br>- ACR Basic: $0.167/ngày ($5.00/mo) | **$70.61/month** (Baseline IaC)<br>hoặc **$11.22/month** (Scale-to-Zero) | [Azure Retail Prices API](https://prices.azure.com/api/retail/prices) |
| **2** | **Amazon Web Services (AWS)** | - EC2 m6i.xlarge (4 vCPU, 16 GiB RAM)<br>- EC2 t4g.xlarge (ARM 4 vCPU, 16 GiB)<br>- AWS Fargate (Serverless Container)<br>- Amazon S3 Standard (50 GB) | - m6i.xlarge: $0.192/h * 730h = $140.16/mo<br>- t4g.xlarge: $0.1344/h * 730h = $98.11/mo<br>- Fargate: $0.04048/vCPU-h + $0.004445/GB-h<br>- S3 Standard: $0.025/GB = $1.25/mo | **$141.41/mo** (EC2 m6i)<br>hoặc **$99.36/mo** (t4g.xlarge) | [AWS EC2 On-Demand Pricing](https://aws.amazon.com/ec2/pricing/on-demand/) |
| **3** | **Google Cloud Platform (GCP)** | - Compute Engine e2-standard-4 (4 vCPU, 16 GiB)<br>- Cloud Run (1 vCPU, 2 GiB, ~320h active/mo)<br>- Google Cloud Storage (50 GB Standard) | - e2-standard-4: $0.134/h * 730h = $97.82/mo<br>- Cloud Run (~320h = 1.152M vCPU-s & 2.304M GiB-s, trừ Free 180k vCPU-s & 360k GiB-s) = $28.19 + GCS $1.00 (~$35.56 gồm logging/egress)<br>- GCS Standard: $0.020/GB = $1.00/mo | **$98.82/mo** (VM e2)<br>hoặc **$35.56/mo** (Cloud Run Serverless) | [Google Cloud Compute All Pricing](https://cloud.google.com/compute/all-pricing) |
| **4** | **Oracle Cloud Infrastructure (OCI)** | - VM.Standard3.Flex (4 OCPU = 8 vCPU, 16 GiB)<br>- OCI Container Instances (Serverless)<br>- OCI Object Storage Standard (50 GB) | - VM.Standard3.Flex: ($0.025 * 4 + $0.0015 * 16) = $0.124/h * 730h = $90.52/mo<br>- Container Instances: $0.0000105/OCPU-s & $0.0000015/GB-s<br>- Object Storage: (50 - 10 miễn phí) * $0.0255 = $1.02/mo | **$91.54/mo** (VM Flex)<br>hoặc **$28.40/mo** (Container Instances) | [Oracle Cloud Cost Estimator](https://www.oracle.com/cloud/costestimator/) |
| **5** | **OVHcloud (Global Bare-Metal)** | - Bare-metal Server Rise-1 (AMD Epyc 8c/16t, 64 GB DDR4 ECC RAM, 2x 960 GB NVMe SSD) | - Trọn gói Dedicated Server: $120.00/tháng<br>- Băng thông Unmetered 1 Gbps, 0 phí Egress | **$120.00/mo** (Cố định toàn diện, không rủi ro I/O spike) | [OVHcloud Bare-Metal Rise](https://www.ovhcloud.com/en/bare-metal/rise/) |
| **6** | **Viettel IDC (Vietnam Enterprise Server)** | - Dedicated Server Entry (Intel Xeon 12c/24t, 32 GB ECC RAM, 2x 480 GB SSD Enterprise) | - Đơn giá niêm yết: 4,500,000 VND/tháng (~$177.16/mo theo tỷ giá 25,400 VND/USD)<br>- Băng thông trong nước 100 Mbps, Data Center Tier 3 | **$177.16/mo** (4,500,000 VNĐ/tháng) | [Viettel IDC Thuê Máy Chủ](https://viettelidc.com.vn/thue-may-chu) |

### 4.2. Chi Tiết Phương Pháp Định Giá Từng Nhà Cung Cấp

1. **Microsoft Azure:**
   - Mô hình Serverless Micro-Billing tính cước theo giây thực thi (vCPU-s và GiB-s).
   - Hạn mức miễn phí hàng tháng (180,000 vCPU-s và 360,000 GiB-s) giúp các tác vụ suy luận phân tán, kiểm thử định kỳ và batch inference đạt ngưỡng tiệm cận $0 chi phí compute khi kích hoạt chế độ co giãn tự động KEDA.
   - Trích dẫn API chính thức: `https://prices.azure.com/api/retail/prices`

2. **Amazon Web Services (AWS):**
   - Phiên bản x86 tiêu chuẩn `m6i.xlarge` (4 vCPU, 16 GiB) có giá $0.192/giờ ($140.16/tháng).
   - Phiên bản kiến trúc ARM Graviton2 `t4g.xlarge` (4 vCPU, 16 GiB) mang lại lợi thế kinh tế rõ rệt: $0.1344/giờ ($98.11/tháng), tiết kiệm 30% so với x86.
   - Tùy chọn Serverless AWS Fargate ($0.04048/vCPU-h + $0.004445/GB-h) phù hợp với microservices container.
   - Trích dẫn chính thức: `https://aws.amazon.com/ec2/pricing/on-demand/`

3. **Google Cloud Platform (GCP):**
   - Dòng VM tối ưu chi phí `e2-standard-4` (4 vCPU, 16 GiB) có đơn giá $0.134/giờ ($97.82/tháng).
   - Dịch vụ Cloud Run (1 vCPU, 2 GiB, ~320 giờ active/tháng = 1,152,000 vCPU-s & 2,304,000 GiB-s) tính cước Serverless ($0.000024/vCPU-s, $0.0000025/GiB-s) trừ Free Tier 180k vCPU-s & 360k GiB-s (compute $28.19 + GCS $1.00 + Cloud Logging/egress ~$6.37), tổng ước tính $35.56/tháng.
   - Trích dẫn chính thức: `https://cloud.google.com/compute/all-pricing`

4. **Oracle Cloud Infrastructure (OCI):**
   - Kiến trúc điện toán linh hoạt `VM.Standard3.Flex` cho phép tùy biến số lượng OCPU ($0.025/OCPU-h) và RAM ($0.0015/GB-h). Với cấu hình 4 OCPU (tương đương 8 vCPU Intel) và 16 GB RAM, đơn giá giờ là `$0.025*4 + $0.0015*16 = $0.124/giờ`, tương đương `$90.52/tháng` (730 giờ), cộng `$1.02` Object Storage (40 GB sau 10 GB Free) thành **$91.54/tháng**.
   - OCI Container Instances tính cước theo $0.0000105/OCPU-s và $0.0000015/GB-s, tổng chi phí serverless ước tính $28.40/tháng.
   - Trích dẫn chính thức: `https://www.oracle.com/cloud/costestimator/`

5. **OVHcloud (Global Bare-Metal):**
   - Cung cấp máy chủ vật lý riêng biệt (Dedicated Bare-Metal Server Rise-1) trang bị vi xử lý AMD Epyc (8 lõi / 16 luồng), 64 GB RAM ECC và 2 ổ SSD NVMe 960 GB.
   - Lợi thế vượt trội: Cố định hoàn toàn chi phí ở mức $120.00/tháng, băng thông 1 Gbps không giới hạn dung lượng (unmetered), không tính phí truyền dữ liệu ra ngoài (0 Egress fee).
   - Trích dẫn chính thức: `https://www.ovhcloud.com/en/bare-metal/rise/`

6. **Viettel IDC (Vietnam Enterprise Server):**
   - Máy chủ dùng riêng vật lý nội địa (Dedicated Server Entry) với Intel Xeon 12 lõi / 24 luồng, 32 GB RAM ECC và 2 ổ cứng chuyên dụng Enterprise SSD 480 GB.
   - Đơn giá niêm yết: 4,500,000 VNĐ/tháng (~$177.16 USD/tháng).
   - Lợi thế chiến lược: Đạt độ trễ mạng nội địa siêu thấp (< 5ms tại TP.HCM/Hà Nội), bảo đảm 100% tuân thủ Luật An ninh mạng Việt Nam (Luật số 24/2018/QH14) và Nghị định 53/2022/NĐ-CP về lưu trữ dữ liệu tại Việt Nam.
   - Trích dẫn chính thức: `https://viettelidc.com.vn/thue-may-chu`

---

## 5. Ma Trận Đối Sánh Đa Chiều (Multi-Cloud Decision Matrix)

Ma trận đánh giá tổng hợp đa tiêu chí để lựa chọn kiến trúc đám mây tối ưu cho hệ thống MLOps:

| Tiêu Chí Đánh Giá | Microsoft Azure | Amazon Web Services | Google Cloud Platform | Oracle Cloud (OCI) | OVHcloud | Viettel IDC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Code & IaC Parity** *(Mức độ tương thích mã nguồn)* | **10/10** (Khớp 100% Terraform/Bicep/ACA) | **9/10** (ECS/Fargate/S3 tương thích cao) | **8/10** (Cloud Run/GCS chuẩn OCI) | **7/10** (OCI Container Instances) | **6/10** (Cần setup Docker swarm/K8s) | **5/10** (Cài đặt hạ tầng thủ công/Ansible) |
| **Chi Phí 1 Tuần (Sprint / Pilot Run)** | **$2.80 - $17.65** | **$24.00 - $35.00** | **$8.00 - $24.00** | **$7.10 - $22.89** | **$30.00** (Tính theo tháng) | **$44.29** (Tính theo tháng) |
| **Rủi Ro Bẫy Chi Phí (Financial Safety / Credit Trap)** | **Rất Thấp** (Scale-to-Zero, Hard Quotas) | **Trung Bình** (Egress & NAT Gateway ẩn) | **Thấp** (Ngưỡng Free Tier rõ ràng) | **Trung Bình** (Cách tính OCPU phức tạp) | **Tuyệt Đối An Toàn** (Cố định flat $120/tháng) | **Tuyệt Đối An Toàn** (Hợp đồng cố định VNĐ) |
| **Độ Trễ Mạng Về Việt Nam (Latency to VN)** | **26.19 - 49.17 ms** (Singapore/HongKong) | **30 - 55 ms** (Singapore) | **28 - 52 ms** (Singapore) | **45 - 75 ms** (Singapore) | **180 - 230 ms** (Châu Âu / Bắc Mỹ) | **< 5 ms** (Nội địa TP.HCM / Hà Nội) |
| **Tuân Thủ Pháp Lý & Dữ Liệu Nội Địa** | ISO 27001, SOC 2, HIPAA | ISO 27001, SOC 2 | ISO 27001, SOC 2 | ISO 27001, FedRAMP | GDPR, ISO 27001 | **Luật An ninh mạng VN, Nghị định 53/2022/NĐ-CP** |
| **Khuyến Nghị Triển Khai (Recommendation)** | **Lựa chọn Số 1 cho MLOps Serving & Cloud Native** | **Lựa chọn cho Hệ sinh thái AWS hiện hữu** | **Tốt cho BigQuery / Phân tích dữ liệu lớn** | **Tối ưu chi phí cho workload tính toán thô** | **Tối ưu cho Cụm Huấn luyện Deep Learning 24/7** | **Bắt buộc cho Dữ liệu nhạy cảm / Tài chính VN** |

---

## 6. Định Mức Hạn Ngạch Đám Mây (Cloud Quotas) & Cảnh Báo Ngân Sách

Để kiểm soát rủi ro chi phí vượt ngưỡng (Cost Spikes) và bảo đảm tính sẵn sàng, hệ thống thiết lập bảng định mức hạn ngạch (Quotas) trên Microsoft Azure:

| Tài nguyên / Dịch vụ Azure | Định mức Quota Đăng ký | Mức Tiêu Thụ Thiết Kế | Ngưỡng Cảnh Báo (Alert Threshold) | Hành Động Tự Động Hóa |
| :--- | :--- | :--- | :--- | :--- |
| **Compute vCPUs (Container Apps)** | 10 vCPUs / Region | 1.0 vCPU / replica (0 - 5 replicas) | 5.0 vCPUs (50%) | Khóa khởi tạo worker mới, gửi email thông báo MLOps Lead |
| **Container Apps Replicas** | Max 5 replicas | 0 - 3 replicas (Scale-to-Zero) | 4 replicas (80%) | Kích hoạt tính năng HTTP concurrency throttling (50 reqs) |
| **Azure Managed Redis (AMR Balanced B0)** | 250 MB - 1 GB Memory | ~85 MB (Feast Online Features) | 200 MB (80%) | Kích hoạt chính sách trục xuất khóa bộ nhớ `volatile-lru` |
| **Azure Blob Storage (`churnguard-datasets`)** | 5 TB / Subscription | ~50 GB (DVC Parquet & Artifacts) | 100 GB | Tự động chuyển tệp cũ >90 ngày sang Cool Tier |
| **Azure Budget Cost Alert** | **$75.00/month (FinOps Baseline Target)** | **$70.61/month (Tối đa)** | $56.49 (80% TCO) & $70.61 (100% TCO) | Tự động hạ scale các cụm non-production về 0 replica |

---

## 7. Kết Quả Đo Độ Trễ Thực Tế Đa Vùng Microsoft Azure (Multi-Region Latency)

Thực nghiệm đo đạc độ trễ TCP Handshake và HTTPS Round-Trip Time (RTT) tới các cổng kết nối API Azure toàn cầu (ghi nhận thực tế từ `data/processed/region_latency_results.json`):

| Khu Vực Đám Mây (Region) | Azure Data Center | Khoảng Cách | Min RTT | Avg RTT | Đánh Giá Khả Năng SLA Phục Vụ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Đông Nam Á (Khuyến nghị)** | Singapore (`southeastasia`) | ~1,400 km | **26.19 ms** | **49.17 ms** | **Tối ưu (< 50ms)** - Đặt API Serving & Feature Store chính |
| **Đông Á** | Hong Kong (`eastasia`) | ~1,500 km | **38.34 ms** | **47.98 ms** | **Tối ưu (< 50ms)** - Vùng dự phòng nóng (Hot Standby) |
| **Nhật Bản** | Tokyo (`japaneast`) | ~4,300 km | 89.18 ms | 106.29 ms | Chấp nhận được (50-150ms) - Phục vụ người dùng Đông Bắc Á |
| **Tây Âu** | Netherlands (`westeurope`) | ~9,400 km | 197.43 ms | 216.59 ms | Cần Azure Front Door / CDN Edge Acceleration (> 150ms) |
| **Bắc Mỹ** | N. Virginia (`eastus`) | ~14,200 km | 238.57 ms | 255.60 ms | Cần Azure Front Door / CDN Edge Acceleration (> 150ms) |

---

## 8. Phân Chia Vai Trò Vận Hành & Ma Trận Phân Quyền IAM RBAC (Teamwork Governance)

Hệ thống phân định rành mạch trách nhiệm vận hành theo mô hình phân quyền dựa trên vai trò (Role-Based Access Control):

| Thành viên / Vai trò | Trách nhiệm Kỹ thuật Chính | Phạm vi Mã nguồn | Quyền Hạn Azure IAM RBAC |
| :--- | :--- | :--- | :--- |
| **MLOps Platform Architect / Tech Lead** | Thiết kế kiến trúc, điều phối CI/CD, tối ưu hóa TCO & nghiệm thu toàn diện | `src/api/`, `configs/`, `.github/`, `deploy/` | **Subscription Contributor / Cost Management Budget Admin** |
| **Data Engineer** | Quản trị DVC, Feast Feature Store Offline/Online, Out-of-Core ETL | `src/data/`, `src/features/` | **Storage Blob Data Contributor, Redis Cache Contributor** |
| **ML Engineer** | Huấn luyện mô hình, Optuna Tuning, Model Registry & XAI (SHAP) | `src/models/` | **Azure ML Data Scientist / AcrPush & Registry Contributor** |
| **DevOps / MLOps SRE** | Giám sát Data Drift (Evidently AI), Docker orchestration, Web UI | `src/monitoring/`, `src/web/` | **Container Apps Operator, Monitoring Metrics Publisher** |

---

## 9. Chiến Lược Tối Ưu Hóa Chi Phí FinOps Doanh Nghiệp (Enterprise FinOps Recommendations)

1. **Thiết lập Serverless Scale-to-Zero (`minReplicas: 0`)**: Azure Container Apps tự động co giãn về 0 khi không có tải, kết hợp tận dụng hạn mức miễn phí hàng tháng (180,000 vCPU-s, 360,000 GiB-s, 5 GB Logs, 100 GB Egress) đưa chi phí thực tế kịch bản kiểm thử/on-demand xuống chỉ còn **$11.22/month** (tiết kiệm 93.7% so với duy trì tải đỉnh 24/7 ở mức $176.96/month).
2. **Chuẩn Hóa Lưu Trữ Apache Parquet Zstandard**: Cắt giảm **77.3% dung lượng lưu trữ** và chi phí truyền tải mạng I/O so với định dạng CSV/text thô (từ 32 GB xuống còn 7.52 GB).
3. **Hiện Đại Hóa Bộ Nhớ Đệm Cache**: Thay thế Azure Cache for Redis Basic C0 (ngừng hỗ trợ từ 01/04/2026) bằng **Azure Managed Redis (AMR Balanced B0 - $12.00/tháng)** hoặc **Valkey 8.0 containerized ($5.00/tháng)**, kết hợp SQLite WAL cục bộ, bảo đảm tính sẵn sàng cao với chi phí tối thiểu.
4. **Chiến Lược Đa Đám Mây Đột Phá (Multi-Cloud Hybrid Strategy)**:
   - Sử dụng **Microsoft Azure Southeast Asia** cho API Serving thời gian thực và Feature Store độ trễ thấp (< 50ms).
   - Cân nhắc máy chủ vật lý **OVHcloud Rise-1 ($120.00/tháng)** cho các đợt huấn luyện lại mô hình lớn định kỳ không giới hạn băng thông.
   - Sẵn sàng phương án chuyển giao sang **Viettel IDC Dedicated Server (4,500,000 VNĐ/tháng)** khi hệ thống phục vụ các nghiệp vụ tài chính - ngân hàng bắt buộc tuân thủ 100% dữ liệu cư trú tại Việt Nam.
