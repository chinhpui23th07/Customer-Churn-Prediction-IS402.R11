# Báo Cáo Kiểm Toán Độc Lập Toàn Diện Dự Án (Zero-Trust Audit Report)

- **Phạm vi kiểm toán:** Toàn bộ mã nguồn, hạ tầng IaC, pipeline dữ liệu/CI-CD, bảo mật, giao diện và tài liệu trong `c:\Users\Nguyen Trong Khoi\Downloads\CLOUD` (`122` tệp được theo dõi bởi Git trong `src/`, `scripts/`, `tests/`, `deploy/`, `.github/`).
- **Nhánh Git tại thời điểm kiểm toán:** `feat/kkbox-mlops-deploy-ready`
- **Phương pháp kiểm toán (Zero-Trust 3-Tier):**
  1. **Không tin tưởng bộ test có sẵn (`tests/`, `scripts/verification/`):** Đối chiếu chéo trực tiếp bằng chứng mã nguồn và thanh tra cấu trúc bộ test để tìm các điểm mù ("False Green").
  2. **Thanh tra trực tiếp từng dòng mã nguồn và cấu hình:** Đọc tuần tự các tệp trong `src/`, `scripts/`, `deploy/`, `.github/`, `dvc.lock`, `.dockerignore`, `Dockerfile`, `docker-compose.yml`, và các báo cáo JSON/Markdown.
  3. **Chạy công cụ độc lập & kiểm thử runtime trực tiếp:**
     - `python scripts/check_file_lines.py src` và `scripts` (`41` tệp trong `src/`, `36` tệp trong `scripts/` đều `<= 400` dòng).
     - `dvc status` (phát hiện lỗi schema `dvc.lock`).
     - `tools/checkov_env` (Checkov quét `deploy/azure`) và `tools/trivy/trivy.exe config --severity CRITICAL,HIGH,MEDIUM deploy` (Trivy quét Terraform, ARM, Dockerfile).
     - FastAPI `TestClient(app)` trên `src.api.main:app` để kiểm tra phản hồi thực tế của `/health`, `/v1/health`, `/v1/predictions`, `/v1/predictions/manual`, `/features/1`, `/predict`, `/docs/drift_report.html` cùng phiên bản thư viện cài đặt (`mlflow 3.16.1`, `feast 0.66.0`, `streamlit 1.51.0`).
     - *Lưu ý giới hạn môi trường:* Lệnh kiểm tra Docker Desktop daemon (`npipe:////./pipe/dockerDesktopLinuxEngine`) báo lỗi không kết nối được tại thời điểm kiểm tra, do đó hành vi runtime trong container được đánh giá từ `TestClient(app)` kết hợp phân tích tĩnh `Dockerfile`, `docker-compose.yml` và `.dockerignore`. Bộ `pytest` có chủ đích không được chạy trong phiên audit này để tránh làm biến đổi tệp `data/processed/drift_metrics.json`.

---

## 1. Tóm Tắt Điều Hành & Bảng Tổng Hợp Mức Độ Nghiêm Trọng

Cuộc kiểm toán độc lập phát hiện **16 lỗi thực tế** (`BUG-01` đến `BUG-16`), trong đó hệ thống hiện tại mang nghiêm trọng tình trạng **"Dual-Stack Schizophrenia"** (hai kiến trúc song song: Kaggle 13 cột cũ và KKBox mới chưa hoàn thiện), cơ chế fallback giải thích SHAP giả mạo, rò rỉ thời gian nghiêm trọng trong đường ống KKBox ETL/Train, hạ tầng deploy Azure không thể chạy thành công nếu triển khai thật, lỗ hổng bảo mật không xác thực trên các API quản trị, và báo cáo sự thật nội bộ tự xưng "KHỚP 100%" nhưng sai lệch cả số học lẫn kết quả quét bảo mật.

| Mức độ | Số lượng | Mã lỗi | Tác động chính |
| :--- | :---: | :--- | :--- |
| **P0 - Critical** | **9** | `BUG-01`, `BUG-02`, `BUG-03`, `BUG-05`, `BUG-06`, `BUG-07`, `BUG-10`, `BUG-11`, `BUG-12` | Sai lệch domain/model nghiêm trọng, rò rỉ dữ liệu tương lai, XAI bịa số, lộ dữ liệu/auth mặc định, endpoint & Docker vỡ runtime, IaC Azure fail khi deploy, sai lệch số liệu trong báo cáo sự thật, hỏng `dvc.lock`, UI `/ui` & Dashboard hỏng |
| **P1 - High** | **5** | `BUG-04`, `BUG-08`, `BUG-09`, `BUG-13`, `BUG-14` | A/B Testing sai thuật toán đặc tả, CI/CD đọc JSON cũ & hardcode branch/domain, module Causal Uplift/Resilience/Dapr bị cô lập hoặc cấu hình sai, Feature Store chỉ chạy SQLite cục bộ, UI vi phạm `DESIGN.md` & giới hạn dòng |
| **P2 - Medium** | **2** | `BUG-15`, `BUG-16` | Script đóng gói bỏ sót tệp cấu hình/báo cáo cốt lõi; bộ test và công cụ kiểm định có 5 điểm mù tạo kết quả "Xanh giả" |
| **Tổng cộng** | **16** | `BUG-01` .. `BUG-16` | **Chưa đủ điều kiện nghiệm thu production hay nộp báo cáo chính thức trước khi khắc phục P0 & P1** |

### Ma Trận Tóm Tắt 16 Lỗi Đã Xác Minh

| Mã | Mức độ | Nhóm | Tiêu đề ngắn | Tệp bằng chứng chính |
| :--- | :---: | :--- | :--- | :--- |
| `BUG-01` | P0 | Kiến trúc / ML | Dual-Stack Schizophrenia (Kaggle Legacy vs KKBox Pilot/Leak) | [main.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/main.py#L1-L120) |
| `BUG-02` | P0 | Data / ML Integrity | Rò rỉ thời gian (Temporal Target Leakage) & chia tập ngẫu nhiên KKBox | [kkbox_etl.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/data/kkbox_etl.py#L163-L196) |
| `BUG-03` | P0 | XAI / Liêm chính | Fallback SHAP giả mạo (`default_weights`) & LinearExplainer nền `np.zeros` | [explain.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/models/explain.py#L33-L104) |
| `BUG-04` | P1 | Thống kê / A/B | A/B Testing sai đặc tả (thiếu latency, không có Chi-Square/Thompson) | [ab_testing.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/ab_testing.py#L54-L137) |
| `BUG-05` | P0 | Bảo mật / Auth | Endpoint quản trị bỏ xác thực & key mặc định vẫn hoạt động khi thiếu `APP_ENV` | [routes_management.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/routes_management.py#L37-L180) |
| `BUG-06` | P0 | Runtime / Docker | `/v1/*` degraded/503 & `.dockerignore` cắt tệp khiến Retrain/Dashboard hỏng | [.dockerignore](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/.dockerignore#L16-L34) |
| `BUG-07` | P0 | Azure IaC / Deploy | Terraform, ARM Template & Script deploy Azure chứa lỗi xung đột không thể chạy | [main.tf](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/deploy/azure/main.tf#L56-L214) |
| `BUG-08` | P1 | CI/CD / DevSecOps | CI quét JSON tĩnh không `--live`, FinOps giả Infracost, hardcode branch/URL | [devsecops_resilience.yml](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/.github/workflows/devsecops_resilience.yml#L106-L113) |
| `BUG-09` | P1 | Kiến trúc / Dead Code | `SLearner`/`TLearner`/`XLearner`, `AzuriteStorageAdapter`, Dapr bị cô lập/lỗi SSL | [retention_optimizer.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/economics/retention_optimizer.py#L126-L276) |
| `BUG-10` | P0 | Báo cáo sự thật | `factual_metrics_audit.md` sai cộng số học KKBox, mâu thuẫn Checkov & Security | [factual_metrics_audit.md](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/requirements/factual_metrics_audit.md#L50-L403) |
| `BUG-11` | P0 | MLOps / DVC | `dvc.lock` sai schema `'2.0'` (`metrics` key) và thiếu `md5` hash | [dvc.lock](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/dvc.lock#L14-L19) |
| `BUG-12` | P0 | Frontend / UI | `/ui` thiếu ô nhập API key (401), Streamlit Dashboard trộn Kaggle/KKBox & mất ảnh | [dashboard.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/web/dashboard.py#L63-L169) |
| `BUG-13` | P1 | Hạ tầng dữ liệu | Feature Store & API DB chỉ dùng SQLite cục bộ, không có Redis/Managed DB cloud | [feature_store.yaml](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/data/kkbox_feast/feature_store.yaml#L1-L10) |
| `BUG-14` | P1 | UI Design System | `/demo` dùng màu tím `#546afa`, `app.js` 222 dòng (`> 200`), CSS nén 15 dòng | [index.html](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/kkbox/web/index.html#L35) |
| `BUG-15` | P2 | Packaging | Script đóng gói bỏ sót `.checkov.yml`, `dvc.lock`, `reports/`, `docs/requirements/` | [audit_vision_and_package.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/scripts/audit_vision_and_package.py#L148-L153) |
| `BUG-16` | P2 | Chất lượng Test | 5 điểm mù trong `tests/` và `verification/` tạo "False Green" | [test_azure_iac_waf.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/tests/test_azure_iac_waf.py#L38-L121) |

---

## 2. Chi Tiết Các Lỗi Phát Hiện

### BUG-01 [P0 - Critical]: Dual-Stack Schizophrenia (Hệ thống vận hành đồng thời Kaggle Legacy và KKBox chưa hoàn thiện)

- **Vị trí & Bằng chứng:**
  - [src/data/download_dataset.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/data/download_dataset.py#L2-L4): Tự đánh dấu `DEPRECATED: Module tải tập dữ liệu Kaggle cũ (Legacy). Dự án hiện tại sử dụng tập dữ liệu lớn KKBox Parquet (7.52 GB).`
  - [docs/requirements/project_spec.md](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/requirements/project_spec.md#L28): Khẳng định `pipeline KKBox dùng subscriber_key và is_churn; khóa một snapshot là (subscriber_key, as_of_date). Code Kaggle cũ chưa tuân thủ và chỉ còn là legacy cho đến khi chuyển xong.`
  - [src/api/main.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/main.py#L1-L120), [src/api/routes_management.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/routes_management.py#L1-L224), [src/models/train_pipeline.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/models/train_pipeline.py#L40-L90), [src/models/evaluate.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/models/evaluate.py#L1-L151), [src/models/model_diagnostics.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/models/model_diagnostics.py#L1-L244), [src/models/tune_optuna.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/models/tune_optuna.py#L1-L157), [src/data/data_quality.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/data/data_quality.py#L1-L187), [src/data/benchmark_io.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/data/benchmark_io.py#L1-L119), [src/data/latency_simulator.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/data/latency_simulator.py#L1-L136), [src/monitoring/drift_detector.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/monitoring/drift_detector.py#L100-L160): Toàn bộ cụm code chính vẫn vận hành trên dữ liệu Kaggle 13 cột cũ (`total_spend`, `support_calls_per_tenure`, `gender_encoded`, `champion_model.joblib`).
  - [docs/experiments/kkbox_pilot_model_report.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/experiments/kkbox_pilot_model_report.json#L2-L78): Kết quả KKBox hiện có ghi nhận `"mode": "pilot"`, `"model_version": "pilot-05ff8789"`, chỉ train/test trên `"train_rows": 776, "validation_rows": 224, "test_rows": 967`, `"roc_auc": 0.768043`, kèm cảnh báo `"Pilot metrics are a plumbing smoke test on incomplete source history; do not report as final accuracy."`
  - **Kết quả probe thực tế qua `TestClient`:**
    - `GET /health` -> `200 {'status': 'HEALTHY', 'champion_model': 'XGBoost', 'model_version': 'v2.0.0-champion', 'feast_online_store': 'CONNECTED (SQLite Only - Redis Offline)', 'mlflow_tracking_db': 'CONNECTED (MLflow Tracking & Registry)', 'uptime_seconds': 0.21}` (phục vụ model Kaggle cũ).
    - `GET /v1/health` -> `200 {'status': 'degraded', 'reason': 'Model unavailable'}` (nhánh KKBox thiếu model).
    - `GET /features/1` -> `200` trả về schema Kaggle (`customerid`, `total_spend`, `support_calls_per_tenure`, `gender_encoded`).
- **Nguyên nhân gốc & Tác động:**
  - Quá trình chuyển đổi sang KKBox (`442,211,685` dòng) mới chỉ xây dựng một nhánh phụ (`/v1/*`, `/demo`, `src/kkbox/*`), trong khi API gốc (`/predict`, `/features/{id}`, `/models/*`, `/api/v1/trigger_retrain`) và bộ script huấn luyện/drift chính vẫn chạy dataset Kaggle cũ.
  - Không có mô hình KKBox production hoàn chỉnh nào sẵn sàng phục vụ thay thế cho bản pilot hoặc pipeline bị rò rỉ.
- **Hướng khắc phục:** Tách biệt hoặc loại bỏ hoàn toàn pipeline Kaggle legacy ra khỏi đường ống chính; huấn luyện lại model KKBox chính thức trên dữ liệu cutoff-safe đầy đủ và gắn vào router chính lẫn Feast KKBox.

---

### BUG-02 [P0 - Critical]: Rò rỉ thời gian (Temporal Target Leakage) và chia tập ngẫu nhiên trong DuckDB ETL & Train KKBox

- **Vị trí & Bằng chứng:**
  - [src/data/kkbox_etl.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/data/kkbox_etl.py#L163):
    ```python
    ch_cte = f"SELECT CAST(subscriber_key AS VARCHAR) AS msno, is_churn FROM read_parquet('{ch_path}')"
    ```
    Không lọc theo `label_window`.
  - [src/data/kkbox_etl.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/data/kkbox_etl.py#L178-L179) và [L195-L196](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/data/kkbox_etl.py#L195-L196): `tx_cte` và `ld_cte` truy vấn trực tiếp `FROM read_parquet('{tx_path}')` / `FROM read_parquet('{ld_path}')` và `GROUP BY` không hề có mệnh đề `WHERE transaction_date <= cutoff` hay `WHERE activity_date <= cutoff`.
  - [data/processed/kkbox_execution_metrics.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/data/processed/kkbox_execution_metrics.json#L39): Ghi rõ `"partitions_executed": "churn_label (window=2017-03) + member + subscription_transaction (part=0) + listening_day (v2/activity_month=201703)"` - sử dụng hành vi nghe nhạc của chính tháng `201703` để dự đoán nhãn `churn_label` tháng `2017-03` mà không có mốc cutoff tách cửa sổ đặc trưng và cửa sổ nhãn.
  - [src/models/train_kkbox.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/models/train_kkbox.py#L95-L97):
    ```python
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    ```
    Dùng `train_test_split` ngẫu nhiên trên tập `real_hf_kkbox_full_window.parquet` thay vì chia theo trục thời gian (Out-of-Time Split).
  - *Đối chiếu nội bộ:* [src/kkbox/features.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/kkbox/features.py#L54-L77) (PySpark) đã áp dụng `.where(F.col("transaction_date") <= cutoff)` và `.where(F.col("activity_date") <= cutoff)`, chứng tỏ chính dự án đã nhận thức yêu cầu cutoff nhưng pipeline DuckDB 15-feature lại bỏ qua.
- **Nguyên nhân gốc & Tác động:** Mô hình huấn luyện từ `kkbox_etl.py` + `train_kkbox.py` bị rò rỉ dữ liệu tương lai vào feature, dẫn đến chỉ số đánh giá bị thổi phồng phi thực tế và vi phạm liêm chính khoa học ML.
- **Hướng khắc phục:** Bổ sung bộ lọc `label_window` và `<= cutoff` cho cả `tx_cte` và `ld_cte` trong `kkbox_etl.py`; thay `train_test_split` ngẫu nhiên bằng Time-Based Split theo `(subscriber_key, as_of_date)`.

---

### BUG-03 [P0 - Critical]: Fallback giải thích SHAP giả mạo (`default_weights`) và lỗi `LinearExplainer` với nền `np.zeros`

- **Vị trí & Bằng chứng:**
  - [src/models/explain.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/models/explain.py#L33):
    ```python
    return shap.LinearExplainer(clf, np.zeros((1, len(cols))))
    ```
    Dùng ma trận 1 dòng toàn số `0` làm background dataset cho `LinearExplainer`, không phản ánh phân phối kỳ vọng thực tế của dữ liệu huấn luyện.
  - [src/models/explain.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/models/explain.py#L92-L104) (và bị sao chép trùng lặp tại [src/api/utils.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/utils.py#L205-L217)):
    ```python
    else:
        default_weights = np.array([
            0.04, -0.02, -0.08, -0.05, 0.25, 0.20, -0.04,
            -0.12, -0.10, 0.08, 0.18, -0.06, 0.14
        ])
        w = default_weights[: x_arr.shape[1]]
        vals = x_arr[0] * w
    ```
- **Nguyên nhân gốc & Tác động:** Khi SHAP thất bại hoặc model không khớp, hệ thống không báo lỗi mà âm thầm nhân input với 13 trọng số bịa đặt cố định (`default_weights`) để trả về "SHAP explanation" cho người dùng. Logic này cũng bị trùng lặp ở 2 tệp và gắn cứng độ dài 13 chiều. Vi phạm nghiêm trọng `INVARIANT-13` (Zero Mockup & Real Execution) và `INVARIANT-14` (Explicit Error Surfacing).
- **Hướng khắc phục:** Xóa bỏ hoàn toàn `default_weights`; truyền background distribution thực từ tập train cho `LinearExplainer`/`TreeExplainer`; hợp nhất về 1 module giải thích duy nhất và báo lỗi tường minh nếu tính SHAP thất bại.

---

### BUG-04 [P1 - High]: Thuật toán A/B Testing không khớp đặc tả và sai phương pháp kiểm định

- **Vị trí & Bằng chứng:**
  - [src/api/ab_testing.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/ab_testing.py#L54-L137):
    - Docstring mô tả: `"T-test cho độ trễ và Chi-Square cho phân phối churn"`.
    - Thực tế SQL (dòng 66) chỉ truy vấn `churn_prediction, churn_probability, model_version` (không có cột độ trễ `latency`).
    - Hàm thống kê (dòng 100, 137) không chạy Chi-Square trên tỷ lệ churn mà chạy `stats.ttest_ind(champ_probs, chal_probs, equal_var=False)` và gán nhãn `"Welch's Two-Sample T-test on Probability Distributions"`.
    - Định tuyến traffic chỉ là hàm băm MD5 tĩnh 80/20, không có cơ chế Multi-Armed Bandit / Thompson Sampling thích ứng.
- **Nguyên nhân gốc & Tác động:** Code thực thi khác hẳn docstring và mục tiêu kiểm định A/B (xác suất model không tuân theo phân phối chuẩn và Welch T-test trên xác suất không thay thế được Chi-Square cho tỷ lệ phân loại churn hay kiểm định độ trễ).
- **Hướng khắc phục:** Lưu thêm độ trễ (`latency_ms`) vào bảng log; bổ sung kiểm định Chi-Square cho phân phối `churn_prediction` và Welch T-test đúng nghĩa cho `latency_ms`; đồng bộ tài liệu và code.

---

### BUG-05 [P0 - Critical]: Lỗ hổng bảo mật xác thực trên các API quản trị & Mật khẩu mặc định được kích hoạt âm thầm

- **Vị trí & Bằng chứng:**
  - [src/api/routes_management.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/routes_management.py#L37-L180): Các endpoint `/models/summary` (L37), `/models/tuning` (L47), `/ab_test/analytics` (L57), `/features/{customer_id}` (L63), `/drift/status` (L73), `/metrics` (L180) đều thiếu `Depends(verify_api_key)`.
  - **Kết quả probe thực tế qua `TestClient`:** `GET /features/1` không gửi header `X-API-Key` vẫn trả về `HTTP 200` với toàn bộ feature của khách hàng (`{'customer_id': 1, 'features': {'customerid': [1], 'total_spend': [598.0], ...}}`).
  - [src/api/utils.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/utils.py#L19-L122):
    - Dòng 19 đánh giá `API_KEY_SECRET` ngay tại thời điểm import module (nếu biến môi trường `APP_ENV=production` được gán sau khi import hoặc không được set trong `Dockerfile`/`docker-compose.yml`, giá trị mặc định `"mlops-churn-secret-2026"` vẫn có hiệu lực).
    - Dòng 122: `configured_secret = os.getenv("API_KEY") or API_KEY_SECRET` cho phép fallback về secret mặc định khi `API_KEY` chưa được cấu hình.
- **Nguyên nhân gốc & Tác động:** Bất kỳ tác nhân bên ngoài nào cũng có thể đọc dữ liệu khách hàng qua `/features/{id}`, lấy chỉ số hệ thống/model qua `/models/*`, `/ab_test/analytics`, `/drift/status`, hoặc khai thác key mặc định `"mlops-churn-secret-2026"` nếu container thiếu cấu hình `APP_ENV`/`API_KEY`.
- **Hướng khắc phục:** Gắn `Depends(verify_api_key)` cho toàn bộ route nhạy cảm; đọc `APP_ENV` và `API_KEY` động trong hàm xác thực theo cơ chế fail-closed, cấm fallback key hardcode trong production.

---

### BUG-06 [P0 - Critical]: Endpoint KKBox `/v1/*` bị `degraded`/`503` và `.dockerignore` loại bỏ tệp khiến Retrain & Dashboard hỏng trong Container

- **Vị trí & Bằng chứng:**
  - **Kết quả probe thực tế qua `TestClient`:**
    - `GET /v1/health` -> `200 {'status': 'degraded', 'reason': 'Model unavailable'}` (do không có artifact model KKBox hợp lệ tại `data/kkbox_models`).
    - `POST /v1/predictions` -> `503 {'detail': 'API secret is not configured'}` vì [src/kkbox/api.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/kkbox/api.py#L124-L128) kiểm tra `os.getenv("KKBOX_API_KEY")` và trả 503 nếu rỗng, nhưng `KKBOX_API_KEY` KHÔNG hề được truyền trong [Dockerfile](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/Dockerfile#L36), [docker-compose.yml](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docker-compose.yml#L1-L68), [main.tf](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/deploy/azure/main.tf), [arm_template.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/deploy/azure/arm_template.json), [containerapp.yaml](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/deploy/azure/containerapp.yaml), hay `deploy_azure.*`.
    - `POST /v1/predictions/manual` -> `422` khi schema không đủ 12 cột KKBox chính xác.
  - [.dockerignore](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/.dockerignore#L16-L34): Loại bỏ toàn bộ `docs/`, `data/processed/*.parquet`, `data/processed/*.csv`, `*.db`, `*.sqlite` (chỉ mở ngoại lệ cho `data/feast_repo/data/*.db` và `data/kkbox_feast/*.db`).
  - Hệ quả khi đóng gói Docker:
    1. `POST /api/v1/trigger_retrain` trong [routes_management.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/routes_management.py#L102) gọi `run_drift_analysis()` -> [src/monitoring/drift_detector.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/monitoring/drift_detector.py#L126-L144) đọc `pd.read_parquet(REF_PARQUET)` và `test_features.parquet` không có kiểm tra `exists()` -> sẽ ném `FileNotFoundError` (HTTP 500) trong Docker vì `*.parquet` bị `.dockerignore` loại bỏ.
    2. `MLFLOW_TRACKING_URI = "sqlite:////app/data/mlflow.db"` trong [main.tf](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/deploy/azure/main.tf) tham chiếu tệp `.db` bị loại bỏ bởi `*.db` trong `.dockerignore`.
    3. Giao diện Streamlit đọc `docs/images/*.png` (bị chặn bởi `docs/` trong `.dockerignore`). *(Ghi chú chính xác: Trên `TestClient`, `GET /docs/drift_report.html` trả về `200` nhờ nhánh fallback trong [src/api/main.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/main.py) tự render HTML động từ `data/processed/drift_metrics.json`; trong container, dù `docs/` bị `.dockerignore` loại bỏ, fallback đó vẫn phụ thuộc vào việc `drift_metrics.json` có mặt trong image).*
- **Nguyên nhân gốc & Tác động:** Thiếu đồng bộ biến môi trường giữa `src/kkbox/api.py`, IaC và Docker; `.dockerignore` cắt bỏ các artifact runtime bắt buộc nhưng code không xử lý tồn tại tệp hoặc tải từ Azure Blob Storage.
- **Hướng khắc phục:** Bổ sung `KKBOX_API_KEY` (hoặc hợp nhất xác thực) vào IaC/Compose; nạp reference data/model từ Azure Blob Storage hoặc whitelist artifact cần thiết; thêm kiểm tra tồn tại tệp trong `drift_detector.py`.

---

### BUG-07 [P0 - Critical]: Terraform, ARM Template và Script Deploy Azure chứa lỗi xung đột không thể triển khai

- **Vị trí & Bằng chứng:**
  1. **Terraform ([deploy/azure/main.tf](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/deploy/azure/main.tf#L9-L214)):**
     - Dòng 9: Pin provider `azurerm ~> 3.80.0` (phiên bản cũ hơn thời điểm ra mắt SKU `Balanced_B0` trong catalog FinOps).
     - Dòng 56-63: Tạo `azurerm_container_registry` với `sku = "Basic"` nhưng bật `public_network_access_enabled = false` và `retention_policy { enabled = true }` - hai tính năng chỉ được Azure hỗ trợ trên SKU `Premium`.
     - Dòng 73-74: Storage Account bật `public_network_access_enabled = false` + `shared_access_key_enabled = false`, nhưng vẫn tạo `azurerm_storage_container` qua data-plane từ máy client mà không cấu hình `storage_use_azuread = true` cùng private endpoint/network exception -> Terraform apply lỗi `403 AuthorizationFailure` / chặn firewall.
     - Dòng 102-106, 113, 213-214: Container App đặt `MLFLOW_TRACKING_URI = "sqlite:////app/data/mlflow.db"` (không bền vững/bị `.dockerignore` chặn) và bỏ sót `KKBOX_API_KEY` lẫn biến kết nối Storage.
  2. **ARM Template ([deploy/azure/arm_template.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/deploy/azure/arm_template.json#L54-L252)):**
     - Dòng 92-101 và 122-134: Trùng lặp tài nguyên `blobServices` tên `default` (vừa khai báo nested trong `storageAccounts`, vừa khai báo top-level ở mảng `resources` bên ngoài) -> gây lỗi ARM deployment conflict/duplicate resource.
     - Dòng 54-59: ACR `Basic` nhưng đặt `publicNetworkAccess: "Disabled"`.
     - Dòng 190-211, 227-252: Container App dùng `identity: SystemAssigned` và cấu hình `registries` với `identity: "system"`, nhưng trong toàn bộ template **KHÔNG có tài nguyên `Microsoft.Authorization/roleAssignments` nào** cấp quyền `AcrPull` cho Managed Identity -> Container App thất bại khi pull image lúc khởi tạo. Biến môi trường cũng thiếu `AZURE_REDIS_PASSWORD` và `KKBOX_API_KEY`.
  3. **Script Deploy ([deploy_azure.bat](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/deploy/azure/deploy_azure.bat#L50-L92) & [deploy_azure.sh](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/deploy/azure/deploy_azure.sh#L34-L70)):**
     - Bước 4 tắt `--public-network-access Disabled` trên Storage Account rồi ngay sau đó chạy lệnh client-side `az storage container create` (bị chặn truy cập mạng công khai).
     - Bước 9 gọi `az containerapp create` kéo image từ ACR **trước khi** gán role `AcrPull` (và thiếu tham số `--registry-server` / `--registry-identity`).
- **Nguyên nhân gốc & Tác động:** IaC và script deploy được viết để vượt qua kiểm tra tĩnh đơn giản mà chưa triển khai thực nghiệm trên Azure; chạy `terraform apply`, `az deployment group create` hay `deploy_azure.*` sẽ dừng lỗi.
- **Hướng khắc phục:** Đồng bộ SKU (ACR Basic bỏ `publicNetworkAccess: Disabled`/`retention_policy`, hoặc dùng Premium + Private Endpoint nếu bắt buộc private), xóa `blobServices` trùng lặp trong ARM, cấp role `AcrPull` trước/tách step bằng Managed Identity, bổ sung đầy đủ env (`KKBOX_API_KEY`, Redis/Storage config).

---

### BUG-08 [P1 - High]: Pipeline CI/CD đọc báo cáo tĩnh, FinOps giả Infracost và hardcode branch/domain

- **Vị trí & Bằng chứng:**
  - [.github/workflows/devsecops_resilience.yml](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/.github/workflows/devsecops_resilience.yml#L106-L113):
    - Gọi `python scripts/security_audit_suite.py` **không có cờ `--live`**. Theo [scripts/security_audit_suite.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/scripts/security_audit_suite.py#L170-L189), khi thiếu `--live`, script chỉ đọc lại tệp JSON tĩnh `reports/*.json` có sẵn thay vì chạy scanner thực tế.
    - Tại [scripts/security_audit_suite.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/scripts/security_audit_suite.py#L118-L128), hàm `parse_microburst_report` luôn gán `status="PASS"` chỉ dựa vào `count = len(lines)` mà không phân tích nội dung cảnh báo.
    - Job đặt tên `4. FinOps Shift-Left Cost Gate (Infracost Standard)`, nhưng [scripts/finops_infracost_scan.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/scripts/finops_infracost_scan.py#L46-L75) không gọi CLI Infracost thật mà dùng bảng giá tĩnh `PRICE_CATALOG` (ví dụ `"Premium": (150.00, ...)`, `"Balanced_B0": (12.00, ...)`) và regex `parse_terraform_resources`.
  - [.github/workflows/kkbox_smoke_deploy_runner.yml](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/.github/workflows/kkbox_smoke_deploy_runner.yml#L25-L48): Khóa cứng runner vào `refs/heads/feat/kkbox-churn-pipeline-pilot` và hardcode endpoint `https://kkboxchurnuit26.eastasia.cloudapp.azure.com`.
- **Nguyên nhân gốc & Tác động:** Công cụ CI báo cáo "Xanh" giả tạo dựa trên báo cáo cũ hoặc bảng giá tự ước lượng, không bắt được lỗi mới phát sinh trên nhánh `feat/kkbox-mlops-deploy-ready` hay `main`.
- **Hướng khắc phục:** Thêm `--live` (hoặc chạy trực tiếp Trivy/Checkov/Infracost CLI thực tế trong workflow), sửa logic parse kết quả bảo mật, và tham số hóa branch/URL trong `kkbox_smoke_deploy_runner.yml`.

---

### BUG-09 [P1 - High]: Module Causal Uplift, Azurite Adapter, Retry/Bulkhead và Dapr bị cô lập hoặc cấu hình sai

- **Vị trí & Bằng chứng:**
  - Kiểm tra `git grep` toàn repo: Các lớp `SLearner`, `TLearner`, `XLearner` và hàm `estimate_kaplan_meier_residual_clv` tại [src/economics/retention_optimizer.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/economics/retention_optimizer.py#L126-L276) chỉ xuất hiện trong `tests/test_causal_uplift.py` - **0 điểm gọi** trong `src/api/`, `src/kkbox/`, hoặc `scripts/`.
  - Kiểm tra `src.resilience`: `AzuriteStorageAdapter`, `Bulkhead`, `RetryPolicy` ([azurite_adapter.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/resilience/azurite_adapter.py#L1-L248), [resilience_pipeline.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/resilience/resilience_pipeline.py#L1-L138)) không được import trong `src/api/` hay `src/kkbox/` (chỉ có `CircuitBreaker` được dùng tại `main.py:88` và `kkbox/api.py:31-46`, còn `AzuriteStorageAdapter` chỉ được test độc lập trong `tests/test_retraining_concurrency.py`).
  - [src/resilience/azurite_adapter.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/resilience/azurite_adapter.py#L105-L106): Gọi `BlobServiceClient.from_connection_string(target_conn, connection_verify=False)` tắt xác minh chứng chỉ SSL và thiếu hỗ trợ `DefaultAzureCredential` cho production Azure Blob.
  - [src/api/routes_management.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/routes_management.py#L26): Khởi tạo `JOB_MANAGER = RetrainingJobManager()` với `DistributedRetrainLock` có `redis_client=None` mặc định trong [retraining_job.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/models/retraining_job.py), mất tác dụng khóa phân tán.
  - [deploy/dapr/statestore.yaml](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/deploy/dapr/statestore.yaml#L26-L27): Tham chiếu `secretStore: azurekeyvault` dù trong toàn bộ IaC không có Azure Key Vault nào và code Python không tích hợp Dapr.
- **Nguyên nhân gốc & Tác động:** Nhiều thành phần "enterprise" (Causal Uplift, Distributed Retrain Lock, Azurite/Blob Adapter, Bulkhead, RetryPolicy, Dapr) chỉ tồn tại để pass unit test riêng lẻ, không tham gia vào luồng thực thi API/serving.
- **Hướng khắc phục:** Tích hợp thực sự vào luồng dự đoán/khuyến nghị/retrain (kết nối Redis lock, Blob storage với `DefaultAzureCredential` + TLS verify), hoặc loại bỏ thành phần thừa không dùng như Dapr manifest không có Key Vault.

---

### BUG-10 [P0 - Critical]: Báo cáo `factual_metrics_audit.md` sai cộng số học KKBox và mâu thuẫn kết quả Checkov/Security/Trivy

- **Vị trí & Bằng chứng:**
  - **Sai lệch số liệu KKBox:**
    - [data/processed/kkbox_execution_metrics.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/data/processed/kkbox_execution_metrics.json#L10-L35) ghi: `member = 6,769,473`, `churn_label = 1,963,891 (2 partitions)`, `subscription_transaction = 22,975,416 (2 partitions)`, `listening_day = 410,502,905 (27 partitions)` -> tổng = `442,211,685` dòng, `32` partitions, `7,522,254,856` bytes.
    - [docs/requirements/factual_metrics_audit.md](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/requirements/factual_metrics_audit.md#L50-L54) tuyên bố "KHỚP 100%" nhưng lại đổi `churn_label` thành `970,960` / `7,772,330` bytes / `1 tệp` và `listening_day` thành `411,494,336` / `6,990,430,635` bytes / `27 tệp` trong khi vẫn giữ nguyên dòng tổng `442,211,685` dòng, `7,522,254,856` bytes, `32 tệp`. Tổng cộng thực tế của các dòng thành phần trong bảng đó chỉ là `442,210,185` dòng (lệch `1,500` dòng) và `31` tệp (lệch `1` tệp).
  - **Mâu thuẫn Checkov & Security trong chính tài liệu:**
    - [factual_metrics_audit.md](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/requirements/factual_metrics_audit.md#L247) ghi `31 checks`, nhưng tại [dòng 403](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/requirements/factual_metrics_audit.md#L403) lại ghi `28 pass`. Chạy live `checkov -d deploy/azure` cho kết quả: `terraform: Passed 18, Failed 0, Skipped 0` + `arm: Passed 10, Failed 0, Skipped 0` (tổng `28` pass, với điều kiện `.checkov.yml` đang skip `12` rule).
    - [factual_metrics_audit.md](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/requirements/factual_metrics_audit.md#L257-L263) ghi Security Audit đạt `183 rules, 182 rules` đạt, `99.45%`, `MEDIUM: 1, LOW: 0`. Trái ngược hoàn toàn với [dòng 403](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/requirements/factual_metrics_audit.md#L403) và tệp gốc [reports/security_audit_report.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/reports/security_audit_report.json#L8-L17) ghi rõ: `"total_rules": 182, "passed_count": 177, "failed_count": 5, "compliance_score_percent": 97.25, "summary": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 3, "LOW": 2}`.
    - **Kết quả quét Trivy thực tế (`trivy config --severity CRITICAL,HIGH,MEDIUM deploy`):** Phát hiện **3 lỗi MEDIUM** đang tồn tại: `arm_template.json` có `AZU-0056` (Blob soft delete tắt) và `AZU-0057` (Storage logging tắt); `main.tf` có `AZU-0060` (thiếu customer-managed keys cho encryption); `Dockerfile` có `0` lỗi.
- **Nguyên nhân gốc & Tác động:** Tài liệu đối chiếu số liệu trung tâm (`factual_metrics_audit.md`) chứa số liệu tự chỉnh sửa bằng tay không khớp công thức toán học và không khớp JSON/tool thật, gây rủi ro nghiêm trọng về liêm chính học thuật nếu đưa vào báo cáo.
- **Hướng khắc phục:** Sinh lại toàn bộ bảng số liệu trực tiếp từ JSON và output chạy tool thật; xóa bỏ các con số mâu thuẫn và ghi rõ kết quả 3 lỗi MEDIUM của Trivy cùng danh sách rule Checkov đã skip.

---

### BUG-11 [P0 - Critical]: `dvc.lock` hỏng schema `'2.0'` và thiếu hash `md5`

- **Vị trí & Bằng chứng:**
  - **Kết quả chạy `dvc status` thực tế:** Thất bại ngay lập tức với thông báo `'.\dvc.lock' validation failed. extra keys not allowed, in stages -> kkbox_download_full -> metrics, line 17, column 5`.
  - [dvc.lock](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/dvc.lock#L14-L19): Stage `kkbox_download_full` chứa khóa `metrics:` (không hợp lệ trong `dvc.lock` schema `'2.0'`) và danh sách `outs:` không có trường `md5:`.
- **Nguyên nhân gốc & Tác động:** Tệp lock được tạo hoặc sửa thủ công sai đặc tả DVC, khiến toàn bộ pipeline theo dõi phiên bản dữ liệu bị vỡ, không thể `dvc repro` hay `dvc push/pull`.
- **Hướng khắc phục:** Bỏ trường `metrics:` không hợp lệ khỏi `dvc.lock` hoặc tạo lại bằng `dvc repro` / `dvc commit` để có đúng `md5:` checksum thực tế.

---

### BUG-12 [P0 - Critical]: Giao diện `/ui` thiếu API Key (lỗi `401`) và Streamlit Dashboard trộn lẫn Kaggle/KKBox + tham chiếu ảnh bị xóa

- **Vị trí & Bằng chứng:**
  - [src/web/app.js](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/web/app.js#L10-L15): Hàm `getApiKey()` chỉ tìm `window.__CHURN_API_KEY__ || sessionStorage.getItem("X_API_KEY") || ""`, trong khi [src/web/index.html](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/web/index.html#L1-L181) không có bất kỳ ô nhập hay cơ chế nạp API Key nào. Khi người dùng bấm dự đoán tại `POST /predict` (dòng 65), API trả `401 Unauthorized` (xác nhận qua `TestClient`: `UI_PREDICT_NO_KEY: 401`).
  - [src/web/dashboard.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/web/dashboard.py#L63-L169):
    - Sidebar (dòng 63) ghi nhận `KKBox_LGBM_Champion (ROC-AUC: 0.8764)` và `Feast 0.66`.
    - Phần thân (dòng 89, 102, 134, 155, 159, 167, 169) lại đọc `drift_metrics.json` & `error_analysis_report.json` của Kaggle, hiển thị cùng `XGBoost` / `Random Forest`, và mở ảnh từ `docs/images/*.png` (vốn đã bị `.dockerignore:16` loại bỏ khỏi container).
    - Gọi `st.image(..., use_column_width=True)` - tham số này đi kèm tham số mới `use_container_width` trong chữ ký hàm `st.image` của `streamlit 1.51.0` (`use_column_width` đã lỗi thời).
- **Nguyên nhân gốc & Tác động:** UI `/ui` không thể sử dụng được cho dự đoán thực tế; Streamlit Dashboard trộn lẫn hai hệ dataset khác nhau và sẽ lỗi thiếu ảnh/báo cáo khi chạy trong Docker.
- **Hướng khắc phục:** Chuyển hướng giao diện chính về KKBox hoặc thêm form nhập/lưu `X-API-Key` an toàn cho `/ui`; cập nhật `dashboard.py` đọc đúng báo cáo KKBox, thay `use_column_width=True` bằng `use_container_width=True`, và kiểm tra tồn tại ảnh/JSON trước khi vẽ.

---

### BUG-13 [P1 - High]: Feature Store & Database chỉ dùng SQLite cục bộ, không có Redis/Managed DB Cloud

- **Vị trí & Bằng chứng:**
  - [data/kkbox_feast/feature_store.yaml](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/data/kkbox_feast/feature_store.yaml#L1-L10): Khai báo `provider: local`, `online_store: sqlite`.
  - [src/kkbox/prepare_feast.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/kkbox/prepare_feast.py#L1-L110): Chỉ nạp feature vào Feast SQLite cục bộ trên ổ đĩa.
  - [src/api/database.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/database.py#L1-L42): Chỉ tạo kết nối SQLite WAL cục bộ (`logs`/A-B analytics).
  - **Kết quả probe thực tế `GET /health`:** Tự xác nhận `'feast_online_store': 'CONNECTED (SQLite Only - Redis Offline)'`.
- **Nguyên nhân gốc & Tác động:** Mặc dù Terraform và ARM Template có khai báo Azure Cache for Redis (`Balanced_B0`), code Python phục vụ (`/health`, `/features`, Feast, A/B logging) vẫn chạy trên tệp SQLite nằm bên trong từng container. Khi triển khai Azure Container Apps hoặc autoscale nhiều instance, dữ liệu online feature và log A/B test sẽ bị mất khi restart container hoặc sai lệch giữa các replica.
- **Hướng khắc phục:** Cấu hình Feast `online_store` sang `redis` khi chạy môi trường Azure (`AZURE_REDIS_HOST`, `AZURE_REDIS_PORT`, `AZURE_REDIS_PASSWORD`) và kết nối DB bền vững (hoặc Azure Blob/Postgres) cho A/B logging.

---

### BUG-14 [P1 - High]: Giao diện `/demo` vi phạm bảng màu `DESIGN.md`, vượt giới hạn 200 dòng và CSS nén bất thường

- **Vị trí & Bằng chứng:**
  - [src/kkbox/web/index.html](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/kkbox/web/index.html#L35): Trong SVG `linearGradient` sử dụng stop màu tím-xanh `#546afa` (`#546afa`, `#30d5c5`, `#b5f083`), không nằm trong bảng màu Oceanic Navy / Amber / Emerald của [DESIGN.md](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/DESIGN.md#L1-L74) và vi phạm `INVARIANT-03`.
  - Kiểm tra số dòng & kích thước thực tế:
    - `src/kkbox/web/app.js`: `222` dòng (`12,440` bytes) - vượt ngưỡng presentation component `< 200` dòng theo `AGENTS.md` (`INVARIANT-06`).
    - `src/kkbox/web/style.css`: `14,023` bytes bị nén chặt vào chỉ `15` dòng, gây khó review và bảo trì.
  - [DESIGN.md](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/DESIGN.md#L1-L74): Tài liệu thiết kế vẫn chỉ mô tả giao diện Kaggle 13 cột cũ, chưa cập nhật đặc tả cho giao diện KKBox `/demo`.
- **Nguyên nhân gốc & Tác động:** UI KKBox phát triển nhanh bị trôi khỏi hệ thống thiết kế chuẩn (`DESIGN.md`) và quy tắc phân tách component nhỏ.
- **Hướng khắc phục:** Thay `#546afa` bằng token màu Oceanic Navy hợp lệ trong `DESIGN.md`; tách `src/kkbox/web/app.js` thành các module `< 200` dòng; format lại `style.css`; cập nhật `DESIGN.md` cho hệ KKBox.

---

### BUG-15 [P2 - Medium]: Script đóng gói bàn giao (`audit_vision_and_package.py`) bỏ sót tài liệu và cấu hình cốt lõi

- **Vị trí & Bằng chứng:**
  - [scripts/audit_vision_and_package.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/scripts/audit_vision_and_package.py#L148-L153): Danh sách `allowed_dirs` và `allowed_files` loại bỏ `.checkov.yml`, `dvc.lock`, `reports/`, `docs/requirements/`, `docs/experiments/`, `docs/MASTER_PROJECT_TRUTH.md`, và `data/`.
- **Nguyên nhân gốc & Tác động:** Khi đóng gói tệp zip bàn giao cuối kỳ, người chấm hoặc hệ thống tái tạo môi trường sẽ thiếu các tệp cấu hình kiểm toán, DVC lock, báo cáo thử nghiệm pilot và tệp đặc tả yêu cầu.
- **Hướng khắc phục:** Bổ sung các thư mục và tệp cấu hình thiết yếu (không chứa dữ liệu thô dung lượng lớn) vào whitelist đóng gói.

---

### BUG-16 [P2 - Medium]: 5 điểm mù trong bộ test & kiểm định tự động tạo kết quả "Xanh giả" (False Green)

- **Vị trí & Bằng chứng:** Tại sao nhiều lỗi P0/P1 tồn tại mà các bộ test sẵn vẫn PASS? Thanh tra trực tiếp `tests/` và `scripts/verification/` phát hiện 5 nguyên nhân hệ thống:
  1. **Nuốt lỗi trùng lặp ARM trong `test_azure_iac_waf.py`:** [tests/test_azure_iac_waf.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/tests/test_azure_iac_waf.py#L38) dùng `{r.get("type"): r for r in arm_data.get("resources", [])}`, âm thầm ghi đè khi có nhiều tài nguyên cùng `type` (bỏ sót lỗi duplicate `blobServices` trong `arm_template.json`). Dòng 120-121 cũng cấm tên tham số chứa `password`/`secret` trong khi ép `publicNetworkAccess == "Disabled"` bất chấp ACR `Basic` không hỗ trợ.
  2. **Test bảo mật đọc JSON tĩnh:** [tests/test_devsecops_compliance.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/tests/test_devsecops_compliance.py#L18-L27) chỉ đọc tệp `reports/security_audit_report.json` đã commit sẵn mà không kích hoạt quét lại Trivy/Checkov/Bandit trên mã nguồn hiện hành.
  3. **Test DVC không chạy `dvc status`:** [tests/test_audit_team_1.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/tests/test_audit_team_1.py#L286-L342) chỉ parse `dvc.yaml` bằng `yaml.safe_load`, không hề kiểm tra `dvc.lock` hay chạy `dvc status` (nên bỏ sót lỗi hỏng schema `BUG-11`).
  4. **Ẩn các failed check qua `.checkov.yml`:** [.checkov.yml](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/.checkov.yml#L1-L21) bỏ qua (skip) tới `12` rule bảo mật, khiến kết quả chạy `checkov` luôn ra `0 failed`.
  5. **Kiểm tra domain chỉ chặn tên bộ dữ liệu thương mại điện tử:** [scripts/verification/assert_domain_semantic_integrity.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/scripts/verification/assert_domain_semantic_integrity.py#L22-L26) chỉ quét từ khóa `rees46`, `2019-Oct.csv`, `ecommerce-behavior-data`, hoàn toàn bỏ sót toàn bộ pipeline Kaggle churn synthetic đang tồn tại ngay trong `src/` (`BUG-01`).
- **Nguyên nhân gốc & Tác động:** Các bài test được thiết kế theo hướng hợp thức hóa cấu hình hiện tại thay vì kiểm thử khắc nghiệt (adversarial testing), tạo sự an tâm giả tạo trước khi deploy.
- **Hướng khắc phục:** Thay dictionary comprehension bằng list iteration, bỏ skip thừa trong `.checkov.yml`, bổ sung kiểm tra `dvc status` và chạy scanner thực trong test pipeline, đồng thời cập nhật `assert_domain_semantic_integrity.py` phát hiện cả pipeline Kaggle legacy.

---

## 3. Lộ Trình Khắc Phục Đề Xuất (4 Giai Đoạn - Chờ Phê Duyệt)

Theo quy tắc `conversational_consent_gate`, chưa có bất kỳ tệp mã nguồn hay cấu hình nào bị chỉnh sửa trong đợt kiểm toán này. Dưới đây là lộ trình khắc phục đề xuất theo thứ tự ưu tiên nếu bạn đồng ý triển khai:

1. **Giai đoạn 1 - Khóa bảo mật & Sửa lỗi Data/ML Liêm chính (`BUG-02`, `BUG-03`, `BUG-05`, `BUG-11`):**
   - Thêm `Depends(verify_api_key)` cho toàn bộ `routes_management.py`, xóa fallback key mặc định tại `src/api/utils.py`.
   - Bỏ `default_weights` SHAP giả và background `np.zeros` trong `src/models/explain.py` & `utils.py`.
   - Sửa `kkbox_etl.py` lọc `label_window` và `<= cutoff` cho cả giao dịch lẫn nghe nhạc; đổi `train_kkbox.py` sang Time-Based Split.
   - Sửa `dvc.lock` đúng schema `'2.0'` và checksum `md5:` hợp lệ khi chạy `dvc status`.
2. **Giai đoạn 2 - Hợp nhất Kiến trúc KKBox, Serving & UI (`BUG-01`, `BUG-06`, `BUG-12`, `BUG-13`, `BUG-14`):**
   - Train model KKBox chính thức (thay `pilot-05ff8789`), đảm bảo `/v1/health` `healthy` và gộp kiến trúc về một domain KKBox nhất quán; bổ sung `KKBOX_API_KEY` và xử lý thiếu `.parquet` an toàn trong `drift_detector.py` & `.dockerignore`.
   - Kết nối Feast online store sang Redis (`BUG-13`) khi chạy cloud và sửa luồng dự đoán/dashboard `/ui` & `/demo` đúng màu `DESIGN.md`, `< 200` dòng (`BUG-12`, `BUG-14`).
3. **Giai đoạn 3 - Sửa Azure IaC, CI/CD & Tích hợp Resilience (`BUG-07`, `BUG-08`, `BUG-09`, `BUG-04`):**
   - Sửa xung đột ACR Basic vs `publicNetworkAccess`/`retention_policy` và Storage public access trong `main.tf` / `deploy_azure.*`; xóa duplicate `blobServices` và thêm `roleAssignments` (`AcrPull`) trong `arm_template.json`; xử lý 3 cảnh báo MEDIUM của Trivy (`AZU-0056`, `AZU-0057`, `AZU-0060`).
   - Sửa CI chạy `--live` scanner, bỏ hardcode branch/URL, sửa A/B testing (`latency` + Chi-Square), và dọn dẹp/nối kết Causal Uplift + `AzuriteStorageAdapter` (bật SSL + `DefaultAzureCredential`) + Redis Retrain Lock.
4. **Giai đoạn 4 - Chuẩn hóa Kiểm thử, Đóng gói & Báo cáo sự thật (`BUG-10`, `BUG-15`, `BUG-16`):**
   - Loại bỏ các điểm mù trong `tests/` & `verification/`, bổ sung whitelist trong `audit_vision_and_package.py`.
   - Cập nhật lại toàn bộ `factual_metrics_audit.md` bằng số liệu chính xác sau khi tất cả các test, Checkov, Trivy và DVC thực tế đều pass.
