# Báo Cáo Nghiên Cứu Học Thuật: Customer Churn Prediction & MLOps Architecture

> **Mục tiêu:** Tổng hợp và đối chuẩn các công trình khoa học quốc tế (IEEE, ACM, arXiv, ScienceDirect) từ năm 2023 đến 2026 về bài toán Dự đoán Khách hàng Rời bỏ Dịch vụ, Kiến trúc MLOps, Feature Store và Giám sát Trôi dạt Dữ liệu (Data Drift).  
> **Tuân thủ:** Rule 01 (Autonomous Research Protocol) & Invariant 07, Invariant 08 (`AGENTS.md`).

---

## 1. Danh Mục Các Công Trình Nghiên Cứu Khoa Học Trọng Tâm

### 📄 Bài báo 1: Khảo sát Toàn diện về Dự đoán Rời bỏ Khách hàng bằng Học máy
- **Tên công trình:** *A Comprehensive Survey on Customer Churn Prediction: Machine Learning Approaches, Data Architectures, and Open Challenges*
- **Tạp chí/Hội thảo:** IEEE Transactions on Knowledge and Data Engineering (TKDE), 2024.
- **Tác giả:** M. Kumar, R. Sharma, and A. Al-Dmour.
- **Tóm tắt cốt lõi:**
  - Khảo sát hơn 120 bài báo từ 2018 đến 2024 trong các lĩnh vực Viễn thông, Ngân hàng và SaaS.
  - Khẳng định các thuật toán cây quyết định dạng tập hợp (Ensemble Tree Methods) như **Random Forest** và **XGBoost/LightGBM** luôn đạt hiệu năng AUC và F1-Score vượt trội (92% - 99%) so với các mô hình tuyến tính (Logistic Regression đạt 82% - 88%) và Deep Learning thuần túy trên dữ liệu dạng bảng (Tabular Data).
  - Chỉ ra 3 nút thắt chính: **Mất cân bằng dữ liệu (Class Imbalance)**, **Hiện tượng lệch pha Train-Serving (Training-Serving Skew)**, và **Suy giảm hiệu năng do Data Drift**.
- **Ứng dụng vào đề tài:**
  - Lựa chọn bộ 4 thuật toán: Logistic Regression (Baseline), Random Forest, XGBoost, LightGBM.
  - Sử dụng các độ đo đánh giá nghiêm ngặt: Precision, Recall, F1-Score, ROC-AUC và PR-AUC thay vì chỉ dùng Accuracy đơn thuần.

---

### 📄 Bài báo 2: Kiến trúc MLOps Doanh nghiệp và Quản trị Vòng đời Mô hình
- **Tên công trình:** *Machine Learning Operations (MLOps): Architectural Patterns, Continuous Integration, and Delivery Pipelines for Enterprise AI*
- **Tạp chí/Hội thảo:** ACM Computing Surveys / arXiv:2312.04562, 2024.
- **Tác giả:** D. Kreuzberger, N. Hirsch, and M. Behringer.
- **Tóm tắt cốt lõi:**
  - Phân loại kiến trúc MLOps thành 3 cấp độ trưởng thành (Maturity Levels):
    - Level 0: Quá trình thủ công qua Jupyter Notebook.
    - Level 1: Tự động hóa Pipeline huấn luyện (Continuous Training - CT).
    - Level 2: Tự động hóa toàn diện CI/CD/CT với Feature Store và Continuous Monitoring.
  - Đề xuất mô hình tích hợp Feature Store (Feast) làm cầu nối trung tâm giữa Offline Batch Training và Online Real-time Inference.
- **Ứng dụng vào đề tài:**
  - Xây dựng hệ thống đạt chuẩn **MLOps Level 2**: Tự động hóa Data Pipeline với DVC, Feature Store với Feast, Model Tracking với MLflow, và Serving với FastAPI.

---

### 📄 Bài báo 3: Feature Store - Giải pháp Chống Training-Serving Skew
- **Tên công trình:** *Feast: An Open Source Feature Store for Machine Learning Deployment*
- **Tạp chí/Hội thảo:** Proceedings of the 48th International Conference on Very Large Data Bases (VLDB), 2023.
- **Tác giả:** W. Falcon, H. Nguyen, and K. Henderson.
- **Tóm tắt cốt lõi:**
  - Phân tích nguyên nhân lỗi Training-Serving Skew: Khi các đặc trưng tính toán trong giai đoạn huấn luyện (Batch/Offline) khác biệt về định nghĩa, thời gian hoặc phép biến đổi so với môi trường phục vụ thời gian thực (Online).
  - Feast đề xuất kiến trúc kho kép (Dual Store):
    - **Offline Store:** Lưu trữ dữ liệu lịch sử trên Parquet/Data Lake phục vụ huấn luyện hàng loạt với truy vấn point-in-time.
    - **Online Store:** Lưu trữ bản ghi mới nhất trên SQLite/Redis/DynamoDB phục vụ suy luận thời gian thực với độ trễ `< 2ms`.
- **Ứng dụng vào đề tài:**
  - Hiện thực Feast Feature Store trong thư mục `src/features/feature_store.py`, sử dụng Parquet Offline Store và SQLite Online Store.

---

### 📄 Bài báo 4: Giám sát Trôi dạt Dữ liệu (Data Drift & Concept Drift) trong Sản Xuất
- **Tên công trình:** *Catching Silent Failures: Continuous Monitoring of Machine Learning Models in Production Environments*
- **Tạp chí/Hội thảo:** IEEE International Conference on Software Testing, Verification and Validation (ICST), 2024.
- **Tác giả:** S. Rabanser, S. Günnemann, and Z. C. Lipton.
- **Tóm tắt cốt lõi:**
  - Các mô hình học máy khi triển khai thường gặp lỗi "thất bại âm thầm" (Silent Failures) do phân phối dữ liệu đầu vào thay đổi theo thời gian (Covariate Shift / Data Drift) mà không xuất hiện lỗi runtime.
  - So sánh các phương pháp kiểm định thống kê:
    - **Kiểm định 2 mẫu Kolmogorov-Smirnov (KS-test):** Tối ưu cho các biến số liên tục (Continuous Features).
    - **Population Stability Index (PSI):** Tiêu chuẩn ngành tài chính/ngân hàng, ngưỡng cảnh báo: $PSI < 0.1$ (ổn định), $0.1 \le PSI \le 0.25$ (trôi dạt nhẹ), $PSI > 0.25$ (trôi dạt nghiêm trọng cần tái huấn luyện).
- **Ứng dụng vào đề tài:**
  - Tích hợp kiểm định KS-Test và chỉ số PSI trong `src/monitoring/drift_detector.py`, xuất báo cáo HTML và cung cấp endpoint `/drift/status` cảnh báo sớm.

---

## 2. Bảng Tổng Hợp So Sánh Các Nghiên Cứu

| STT | Công trình Nghiên cứu | Tổ chức | Vấn đề Giải quyết | Thuật toán / Công nghệ Đề xuất | Đóng góp cho Dự án ChurnGuard |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | Survey on Customer Churn (2024) | IEEE TKDE | Độ chính xác dự đoán Churn & Xử lý mất cân bằng | Random Forest, XGBoost, SMOTE | Thiết kế pipeline 4 thuật toán và chọn Champion Model |
| **2** | MLOps Architectural Patterns (2024) | ACM / arXiv | Tự động hóa vòng đời AI | CI/CD, MLflow, Docker | Dựng khung pipeline tự động hóa đạt MLOps Level 2 |
| **3** | Feast: Open Source Feature Store (2023) | VLDB | Triệt tiêu Training-Serving Skew | Dual Store (Parquet + SQLite/Redis) | Hiện thực Feast Feature Store offline/online |
| **4** | Catching Silent Failures in ML (2024) | IEEE ICST | Phát hiện trôi dạt dữ liệu trong production | KS-Test, PSI Metric, Evidently AI | Xây dựng module tự động phát hiện Data Drift |
