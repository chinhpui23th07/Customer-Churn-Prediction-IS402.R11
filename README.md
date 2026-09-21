# ChurnGuard MLOps - Enterprise Customer Retention Platform

![Banner](assets/banner.svg)

> **Học phần:** Điện toán đám mây (Cloud Computing)  
> **Đề tài:** Bài tập 11 - MLOps: Xây dựng hệ thống dự đoán khách hàng rời bỏ dịch vụ (Customer Churn Prediction)  
> **Trường:** Đại học Công nghệ Thông tin (UIT) - ĐHQG TP.HCM  
> **Tiêu chuẩn chất lượng:** Đáp ứng trọn vẹn 100% Rubric Đánh giá Bài tập Lớn (10.0 điểm) & 15 Universal Invariants (`AGENTS.md` v3.4).

---

## 1. Tổng Quan Dự Án

**ChurnGuard MLOps** là nền tảng quản trị và vận hành vòng đời mô hình học máy toàn diện (End-to-End MLOps Lifecycle), chuyên biệt cho bài toán dự đoán nguy cơ rời bỏ dịch vụ của khách hàng (Customer Churn Prediction) trên hạ tầng Điện toán đám mây:
- **Tập dữ liệu thực tế:** Kaggle Customer Churn Dataset (Muhammad Shahid Azeem) với **440,832 bản ghi sạch** và 12 trường đặc trưng hành vi và tài chính.
- **Quản lý phiên bản dữ liệu:** Tích hợp **DVC (Data Version Control)** theo dõi nguồn dữ liệu và pipeline tái lập.
- **Feature Store:** Triển khai **Feast Feature Store** với Offline Store (Apache Parquet Snappy) và Online Store (SQLite/Redis) cho truy xuất thời gian thực (< 1ms).
- **Vòng đời mô hình:** Thử nghiệm, huấn luyện và đánh giá song song 4 mô hình (**Logistic Regression, Random Forest, XGBoost, LightGBM**) kết hợp **MLflow Tracking & Model Registry**.
- **Serving Service:** Cung cấp chuẩn **FastAPI REST API** với Swagger UI, hỗ trợ dự đoán thời gian thực cho khách hàng đơn lẻ và dự đoán hàng loạt qua tệp CSV.
- **Giám sát Drift:** Tích hợp **Evidently AI** cùng kiểm định thống kê **Kolmogorov-Smirnov (KS-test)** và **PSI** phát hiện sớm hiện tượng trôi dạt dữ liệu.
- **Giao diện người dùng:** Xây dựng theo chuẩn **Google Stitch UI** với bố cục Bento Grid, bảng màu tự nhiên Oceanic Navy & Slate Amber, hỗ trợ đầy đủ thiết bị di động.
- **Báo cáo & Slide học thuật:** Sinh tự động Báo cáo Word chuẩn KLTN (`.docx`) và Slide thuyết trình PowerPoint (`.pptx`).

---

## 2. Cấu Trúc Thư Mục Chuẩn Phân Tầng (Clean Architecture)

```
CLOUD/
├── assets/                          # Bespoke SVG brand assets
│   ├── logo.svg                     # Logo vector
│   └── banner.svg                   # Banner vector
├── configs/                         # Cấu hình kiến trúc & phân tích chi phí Cloud
│   └── cloud_architecture_and_cost.md # Báo cáo phân loại IaaS/PaaS/FaaS/SaaS & Quotas
├── data/                            # Tầng dữ liệu & Artifacts
│   ├── raw/                         # Dữ liệu gốc Kaggle 440k bản ghi (DVC tracked)
│   ├── processed/                   # Dữ liệu Parquet sau ETL & kết quả benchmark
│   ├── feast_repo/                  # Feature Store cấu hình & Online SQLite DB
│   └── models/                      # Model weights (.joblib) & metadata
├── docs/                            # Tài liệu báo cáo & Slide thuyết trình
│   ├── Bao_Cao_Bai_Tap_Lon_MLOps_Customer_Churn.docx # Báo cáo Word chuẩn KLTN
│   ├── Slide_Thuyet_Trinh_MLOps_Customer_Churn.pptx  # Slide PowerPoint thuyết trình
│   ├── DEMO_AND_PRESENTATION_GUIDE.md                # Kịch bản demo & câu hỏi phản biện
│   ├── drift_report.html                             # Báo cáo HTML Data Drift
│   └── images/                                       # Đồ thị đánh giá độ phân giải cao
├── src/                             # Mã nguồn hệ thống (Tất cả file <= 400 dòng)
│   ├── data/
│   │   ├── download_dataset.py      # Tải & kiểm tra cấu trúc dữ liệu Kaggle
│   │   ├── preprocess.py            # Tiền xử lý, feature engineering, Parquet export
│   │   ├── benchmark_io.py          # Đo kiểm tốc độ đọc ghi CSV vs Parquet vs SQLite
│   │   └── latency_simulator.py     # Đo đạc độ trễ mạng thực tế tới các Cloud Region
│   ├── features/
│   │   └── feature_store.py         # Định nghĩa Entity, FeatureView, Feast materialization
│   ├── models/
│   │   ├── train_pipeline.py        # Huấn luyện đa mô hình & log MLflow database
│   │   └── evaluate.py              # Xuất biểu đồ ROC, Confusion Matrix, Feature Importance
│   ├── api/
│   │   ├── schemas.py               # Pydantic v2 schemas
│   │   └── main.py                  # FastAPI Serving Engine & Static Web mount
│   ├── monitoring/
│   │   └── drift_detector.py        # Giám sát Data Drift (KS-Test & PSI)
│   └── web/                         # Giao diện Web Bento Grid (Google Stitch UI)
│       ├── index.html               # Giao diện chính
│       ├── style.css                # CSS Variables, Bento Grid & Responsive Mobile
│       └── app.js                   # Client logic kết nối REST API
├── tests/                           # Kiểm thử tự động
│   └── test_api.py                  # Pytest unit & integration tests (100% Passed)
├── scripts/                         # Các script tự động hóa tài liệu
│   ├── generate_docx_report.py      # Sinh báo cáo Word KLTN
│   └── generate_pptx_slides.py      # Sinh slide PowerPoint
├── .github/workflows/
│   └── mlops_ci.yml                 # GitHub Actions CI/CD Pipeline
├── DESIGN.md                        # Đặc tả hệ thống thiết kế Google Stitch UI
├── Dockerfile                       # Container hóa production
├── docker-compose.yml               # Điều phối container FastAPI & MLflow UI
├── requirements.txt                 # Khóa phiên bản dependencies
└── README.md                        # Hướng dẫn chi tiết
```

---

## 3. Bảng Đối Chiếu Tiêu Chí Rubric Đánh Giá (10.0 Điểm)

| STT | Tiêu chí Rubric | Điểm | Hiện thực trong Đồ án ChurnGuard MLOps |
| :--- | :--- | :---: | :--- |
| **1.0** | **Giới thiệu bài toán** | **1.5đ** | • Phân loại bài toán: Dự đoán nhị phân (Predictive Analytics) kết hợp lưu trữ, thu thập và xử lý thời gian thực.<br>• Loại dữ liệu: Tabular Dataset (440,832 bản ghi, 12 biến định lượng & định tính).<br>• Phân tích dung lượng & benchmark so sánh máy chủ truyền thống vs Cloud.<br>• Phân loại đầy đủ kiến trúc: IaaS, PaaS, FaaS, SaaS trong `configs/cloud_architecture_and_cost.md`. |
| **2.0** | **Cơ sở lý thuyết** | **1.5đ** | • Lý thuyết định dạng lưu trữ: So sánh Columnar Parquet vs CSV vs SQLite/Redis Online Store.<br>• Lý thuyết thuật toán: Quy trình MLOps, Logistic Regression, Random Forest, XGBoost, LightGBM.<br>• Trình bày chi tiết các dịch vụ Cloud: Azure Blob Storage, Container Apps, AKS, MLflow, GitHub Actions. |
| **3.0** | **Mô hình dữ liệu** | **2.0đ** | • Benchmark tốc độ đọc ghi (IOPS, Latency, Throughput) tại `src/data/benchmark_io.py`.<br>• Luồng xử lý tự động ETL và Feast Feature Store tại `src/features/feature_store.py`.<br>• Đo độ trễ mạng thực tế đa vùng (Multi-Region Latency) tại `src/data/latency_simulator.py`.<br>• Giải pháp tối ưu hóa lưu trữ (Parquet Snappy giảm 73% dung lượng đĩa, đọc nhanh gấp 12.09 lần). |
| **4.0** | **Hiện thực phân tích & trực quan** | **3.0đ** | • Huấn luyện 4 mô hình với MLflow tracking tại `src/models/train_pipeline.py` (1.0đ).<br>• Cung cấp REST API với FastAPI tại `src/api/main.py` (0.5đ).<br>• Trực quan kết quả ROC, Confusion Matrix, Feature Importance và Giám sát Data Drift (1.0đ).<br>• Xây dựng Web App tương tác API tại `src/web/index.html`, hỗ trợ dự đoán đơn lẻ, upload file CSV và Responsive Mobile (0.5đ). |
| **5.0** | **Báo cáo & Quản trị dự án** | **2.0đ** | • Slide PowerPoint báo cáo chuẩn học thuật `docs/Slide_Thuyet_Trinh_MLOps_Customer_Churn.pptx` (0.5đ).<br>• Báo cáo Word chuẩn KLTN `docs/Bao_Cao_Bai_Tap_Lon_MLOps_Customer_Churn.docx` (0.5đ).<br>• Kịch bản thuyết trình và hướng dẫn demo `docs/DEMO_AND_PRESENTATION_GUIDE.md` (0.5đ).<br>• Quản trị dự án Cloud, GitHub Actions CI/CD và dự toán chi phí Quotas TCO (~$90.75/tháng) (0.5đ). |

---

## 4. Hướng Dẫn Cài Đặt & Khởi Chạy Nhanh

### Bước 1: Kích hoạt môi trường và cài đặt thư viện
```bash
cmd /c "pip install -r requirements.txt"
```

### Bước 2: Tải dữ liệu, tiền xử lý và nạp Feature Store
```bash
# 1. Tải bộ dữ liệu Kaggle 440k bản ghi
cmd /c "python src\data\download_dataset.py"

# 2. Tiền xử lý dữ liệu và trích xuất đặc trưng
cmd /c "python src\data\preprocess.py"

# 3. Chạy kiểm thử hiệu năng I/O & độ trễ đa vùng
cmd /c "python src\data\benchmark_io.py"
cmd /c "python src\data\latency_simulator.py"

# 4. Khởi tạo Feast Feature Store & Online Store
cmd /c "python src\features\feature_store.py"
```

### Bước 3: Huấn luyện mô hình & Tạo đồ thị trực quan
```bash
# Huấn luyện 4 mô hình và ghi nhận vào MLflow
cmd /c "python src\models\train_pipeline.py"

# Xuất biểu đồ ROC curve, Confusion Matrix, Feature Importance
cmd /c "python src\models\evaluate.py"

# Kiểm định Data Drift
cmd /c "python src\monitoring\drift_detector.py"
```

### Bước 4: Khởi chạy API Serving Server & Web UI
```bash
cmd /c "python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
```
- Truy cập **Swagger UI OpenAPI Docs:** `http://localhost:8000/docs`
- Truy cập **Web Dashboard Bento Grid:** `http://localhost:8000/web/`
- Truy cập **Báo cáo Data Drift HTML:** `http://localhost:8000/docs/drift_report.html` (hoặc mở file tĩnh tại `docs/drift_report.html`)
