# Báo Cáo Khảo Sát & Đối Chuẩn GitHub Repositories (GitHub Benchmark Repos)

> **Mục tiêu:** Khảo sát, phân tích kiến trúc và đối chuẩn các kho lưu trữ mã nguồn mở tiêu chuẩn (Gold Standard Repositories) trên GitHub để kế thừa các mẫu thiết kế tối ưu và tránh lỗi thiết kế (Anti-patterns).  
> **Tuân thủ:** Rule 01 & Rule 06 (GitHub Repo Cloning & MCP Reuse) trong `AGENTS.md`.

---

## 1. Danh Sách Các Repository Đối Chuẩn Chính

### ⭐️ Repo 1: `faisalghifari17/customer-churn-prediction`
- **URL:** `https://github.com/faisalghifari17/customer-churn-prediction`
- **Chủ đề:** Phân tích dữ liệu khách hàng rời bỏ và xây dựng mô hình dự đoán.
- **Tập dữ liệu:** Chứa tệp dữ liệu thực tế `customer_churn_dataset-training-master.csv` (23.4 MB, ~440k bản ghi) và `customer_churn_dataset-testing-master.csv` (3.28 MB, ~64k bản ghi).
- **Phân tích Kiến trúc & Kỹ thuật:**
  - Tiền xử lý dữ liệu: Làm sạch giá trị thiếu, mã hóa biến phân loại (Gender, Subscription Type, Contract Length).
  - Thuật toán thử nghiệm: So sánh Logistic Regression, Random Forest, và XGBoost.
  - Phát hiện quan trọng: Biến `Support Calls` và `Payment Delay` có tương quan cao nhất tới quyết định rời bỏ dịch vụ.
- **Kế thừa vào Dự án ChurnGuard:**
  - Tải trực tiếp tập dữ liệu gốc thực tế 440k bản ghi vào `data/raw/` thay vì tạo dữ liệu giả lập.
  - Sử dụng các nhóm biến đặc trưng hành vi và thiết kế bổ sung 3 biến tỉ lệ tương tác (`support_calls_per_tenure`, `spend_per_tenure`, `delay_ratio`).

---

### ⭐️ Repo 2: `ssabrut/customer-churn-mlops`
- **URL:** `https://github.com/ssabrut/customer-churn-mlops`
- **Chủ đề:** End-to-End MLOps Pipeline for Customer Churn Prediction.
- **Stack công nghệ:** DVC, Feast Feature Store, MLflow, Docker, FastAPI.
- **Phân tích Kiến trúc & Luồng Dữ Liệu:**
  ```text
  Raw Data (DVC) -> Feature Store (Feast) -> Training & Tracking (MLflow) -> Serving (FastAPI)
  ```
  - Quản lý dữ liệu: Sử dụng DVC để tách rời việc lưu trữ tệp dữ liệu nặng khỏi Git commit history.
  - Tách biệt môi trường: Tách biệt rõ ràng tầng huấn luyện hàng loạt (Batch Training) và tầng suy luận trực tuyến (Online Inference).
- **Kế thừa vào Dự án ChurnGuard:**
  - Áp dụng cấu trúc thư mục phân tầng sạch: `src/data/`, `src/features/`, `src/models/`, `src/api/`, `src/monitoring/`.
  - Tích hợp `dvc.yaml` và quản lý phiên bản dữ liệu với DVC.

---

### ⭐️ Repo 3: `feast-dev/feast` (Official Feast Feature Store)
- **URL:** `https://github.com/feast-dev/feast`
- **Chủ đề:** The Open Source Feature Store for Machine Learning.
- **Phân tích Cấu trúc & Best Practices (Context7 Verified):**
  - Quản lý metadata qua `feature_store.yaml` với cấu hình linh hoạt: `provider: local`, `offline_store: file`, `online_store: sqlite`.
  - Định nghĩa Entity rõ ràng với `join_keys` (khóa chính nối bảng: `customerid`).
  - Sử dụng `Field(dtype=...)` chuẩn mới thay vì cú pháp cũ đã deprecated.
  - Cơ chế `materialize(start_date, end_date)` để đẩy các đặc trưng mới nhất từ Parquet offline sang SQLite online.
- **Kế thừa vào Dự án ChurnGuard:**
  - Xây dựng `data/feast_repo/feature_store.yaml` và module `src/features/feature_store.py` tuân thủ 100% chuẩn SDK mới nhất.

---

### ⭐️ Repo 4: `mlflow/mlflow` (Official MLflow)
- **URL:** `https://github.com/mlflow/mlflow`
- **Chủ đề:** Open source platform for the machine learning lifecycle.
- **Phân tích Kiến trúc & Best Practices:**
  - Tránh sử dụng filestore cũ (`./mlruns` đang trong trạng thái maintenance mode).
  - Khuyến nghị chuẩn doanh nghiệp: Sử dụng SQLite backend URI (`sqlite:///data/mlflow.db`) đảm bảo tính toàn vẹn dữ liệu ACID và hỗ trợ song song đa luồng/đa tiến trình.
  - Ghi log có cấu trúc: Parameters, Metrics theo từng epoch/validation, Artifacts (mô hình đã serialize `.joblib`).
- **Kế thừa vào Dự án ChurnGuard:**
  - Cấu hình tracking URI `sqlite:///{BASE_DIR}/data/mlflow.db` trong `src/models/train_pipeline.py`.
  - Tự động đăng ký và bình chọn Champion Model dựa trên chỉ số ROC-AUC cao nhất.

---

### ⭐️ Repo 5: `evidentlyai/evidently` (Official Evidently AI)
- **URL:** `https://github.com/evidentlyai/evidently`
- **Chủ đề:** Evaluate and monitor machine learning models in production.
- **Phân tích Cơ chế Giám sát:**
  - So sánh tập tham chiếu (Reference Dataset - thường là tập Validation lúc huấn luyện) với tập hiện tại (Current Production Inference Dataset).
  - Tự động áp dụng kiểm định KS-Test cho biến số thực và PSI (Population Stability Index) cho biến phân loại/phân phối.
- **Kế thừa vào Dự án ChurnGuard:**
  - Xây dựng module `src/monitoring/drift_detector.py` tính toán cả KS-Statistic, P-Value và PSI Score cho 13 đặc trưng của khách hàng, xuất báo cáo trực quan `docs/drift_report.html`.

---

## 2. Bảng Đối Chuẩn Kỹ Thuật (Technical Benchmarking Matrix)

| Tiêu chí So sánh | Repo Faisal Ghifari | Repo Ssabrut MLOps | Repo Feast/MLflow | Dự Án ChurnGuard MLOps (Hiện tại) |
| :--- | :---: | :---: | :---: | :---: |
| **Dữ liệu thực tế (440k rows)** | Có (Kaggle CSV) | Mẫu nhỏ (<10k) | Dữ liệu synthetic | **Có (440,832 bản ghi sạch từ Kaggle)** |
| **Data Versioning (DVC)** | Không | Có | Không | **Có (Đầy đủ dvc init & dvc add)** |
| **Feature Store (Feast)** | Không | Có | Có | **Có (Offline Parquet + Online SQLite)** |
| **Đa Thuật Toán & Tracking** | Không có MLflow | Có MLflow | Có MLflow | **Có (LR, RF, XGB, LGBM + MLflow SQLite)** |
| **Giám Sát Data Drift** | Không | Không | Không | **Có (Kiểm định KS-Test + PSI + HTML Report)** |
| **Giao Diện Web Dashboard** | Không | Không | UI cơ bản | **Có (Bento Grid chuẩn Google Stitch UI)** |
| **Báo Cáo Word KLTN & Slide** | Không | Không | Không | **Có (Word .docx 5 chương + Slide .pptx 16 slide)** |
| **Giới hạn 400 dòng/file** | Nhiều file > 500 | Không áp dụng | Không áp dụng | **Tuyệt đối 100% file <= 400 dòng (Audit 0 lỗi)** |
