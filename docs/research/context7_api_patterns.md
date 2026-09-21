# Báo Cáo Tra Cứu Tài Liệu API Chuẩn: Context7 API Patterns

> **Mục tiêu:** Ghi nhận toàn bộ các chuẩn cú pháp API, mẫu triển khai tối ưu và tài liệu tra cứu chính thức thông qua Context7 MCP cho các thư viện cốt lõi trong hệ sinh thái MLOps.  
> **Tuân thủ:** Rule 01 (Autonomous Research Protocol & Context7 API Patterns).

---

## 1. Kết Quả Tra Cứu Feast Feature Store (Context7 Library: `/feast-dev/feast`)

- **Context7 Library ID:** `/feast-dev/feast` (Reputation: High, Benchmark Score: 83.49, Code Snippets: 6,616).
- **Trang tài liệu:** `/websites/feast_dev` (Benchmark Score: 85.93).

### Cú Pháp & Mẫu Thiết Kế Chuẩn Được Áp Dụng:
1. **Cấu hình `feature_store.yaml`:**
   ```yaml
   project: customer_churn_feature_store
   registry: data/registry.db
   provider: local
   offline_store:
     type: file
   online_store:
     type: sqlite
     path: data/online_store.db
   ```
2. **Định nghĩa Entity & Feature View (Chuẩn Feast v0.40+):**
   - Thay thế cú pháp cũ `ValueType` đã deprecated bằng `Field(name=..., dtype=Float32/Int64)`.
   - Sử dụng `join_keys=["customerid"]` làm khóa liên kết chính giữa offline batch features và online streaming features.
3. **Cơ chế Materialization:**
   - Dùng `store.apply([entity, feature_view])` để lưu schema vào registry.
   - Dùng `store.materialize(start_date, end_date)` để trích xuất trạng thái đặc trưng mới nhất vào SQLite database phục vụ serving dưới 1ms.
4. **Truy vấn Online Features thời gian thực:**
   ```python
   response = store.get_online_features(
       features=["customer_churn_features:tenure", "customer_churn_features:support_calls", ...],
       entity_rows=[{"customerid": 166838}]
   )
   feature_dict = response.to_dict()
   ```

---

## 2. Kết Quả Tra Cứu MLflow Model Lifecycle (Context7 Library: `/mlflow/mlflow`)

- **Context7 Tra Cứu:** Quản lý vòng đời mô hình học máy và lưu trữ Experiment Tracking.

### Cú Pháp & Mẫu Thiết Kế Chuẩn Được Áp Dụng:
1. **Chuyển đổi từ FileStore sang SQLite Backend:**
   - Phiên bản MLflow 3.x đã đưa FileStore (`./mlruns`) vào trạng thái *maintenance mode*.
   - Khuyến nghị tối ưu: Thiết lập URI cơ sở dữ liệu SQLite:
     ```python
     sqlite_uri = f"sqlite:///{BASE_DIR}/data/mlflow.db"
     mlflow.set_tracking_uri(sqlite_uri)
     mlflow.set_experiment("Customer_Churn_Prediction_Enterprise")
     ```
   - Lợi ích: Đảm bảo tính toàn vẹn dữ liệu ACID, hỗ trợ song song đa tiến trình huấn luyện mà không bị tranh chấp khóa file (file locking collision).
2. **Ghi nhận Thí nghiệm (Experiment Logging):**
   - `mlflow.log_params(cfg["params"])`: Ghi lại siêu tham số của từng thuật toán (Random Forest, XGBoost, LightGBM, Logistic Regression).
   - `mlflow.log_metrics({...})`: Ghi nhận các độ đo đa chiều (Accuracy, Precision, Recall, F1-Score, ROC-AUC, thời gian huấn luyện).
   - `mlflow.log_artifact(model_path)`: Đăng ký tệp weights `.joblib` vào kho lưu trữ artifacts.

---

## 3. Kết Quả Tra Cứu FastAPI & Pydantic v2 (Context7 Tra Cứu)

- **Chuẩn Pydantic v2 Migration:**
  - Thay thế `Field(..., example=...)` cũ bằng `Field(..., json_schema_extra={"example": ...})` để loại bỏ 100% cảnh báo `PydanticDeprecatedSince20`.
  - Sử dụng `BaseModel` với type annotations chuẩn (`Optional[int]`, `float`, `str`) đảm bảo dữ liệu đầu vào tự động được validate và sinh schema OpenAPI Swagger chuẩn mực.
- **FastAPI Endpoints:**
  - `POST /predict`: Nhận JSON payload của một khách hàng, tiền xử lý và trả về xác suất rời bỏ cùng hành động giữ chân.
  - `POST /upload_csv_predict`: Xử lý multipart file upload `UploadFile = File(...)` để dự đoán hàng loạt trực tiếp từ tệp CSV của Kaggle.

---

## 4. Kết Quả Tra Cứu DVC (Data Version Control)

- Khởi tạo kho dữ liệu: `python -m dvc init`.
- Theo dõi tệp dữ liệu lớn: `python -m dvc add data/raw`.
- Kết quả: Tạo tệp con trỏ `data/raw.dvc` chứa mã băm md5 của tập dữ liệu thực tế, cho phép commit con trỏ lên Git mà không làm phình to Git repository.
