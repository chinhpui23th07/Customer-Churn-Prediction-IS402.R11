# Kịch Bản Trình Diễn Hệ Thống & Hướng Dẫn Thao Tác (System Demonstration Playbook)

> **Hệ thống:** ChurnGuard MLOps Level 2 Platform  
> **Kiến trúc:** Feast Feature Store + MLflow Registry + FastAPI Serving + Evidently Drift Monitoring  
> **Mục tiêu:** Hướng dẫn quy trình vận hành và trình diễn thực nghiệm các phân hệ kỹ thuật  

---

## 1. Chuẩn Bị Môi Trường Vận Hành

Mở Terminal tại thư mục gốc dự án:

```bash
# Khởi chạy FastAPI Model Serving Server
cmd /c "python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
```

Khi server thông báo `Application startup complete. Uvicorn running on http://0.0.0.0:8000`, hệ thống đã sẵn sàng.

---

## 2. Kịch Bản Trình Diễn Từng Bước (Live Demonstration Walkthrough)

### 🔹 Bước 1: Khởi động & Kiểm tra Trạng thái Sức khỏe Hệ thống (HealthCheck)
1. Mở trình duyệt truy cập: `http://localhost:8000/health`
2. **Thuyết minh kỹ thuật:**
   - *"Hệ thống ChurnGuard MLOps đang hoạt động ở trạng thái HEALTHY."*
   - *"Mô hình Champion hiện tại là XGBoost (hoặc Random Forest) được tuyển chọn tự động qua MLflow Registry với ROC-AUC đạt >0.998."*
   - *"Feast Online Feature Store (SQLite/Redis) và MLflow Tracking Server đã được kết nối thông suốt."*

### 🔹 Bước 2: Trình diễn Giao diện Web Dashboard (Thời lượng: 2 phút)
1. Mở trình duyệt truy cập: `http://localhost:8000/web/` (hoặc mở trực tiếp file `src/web/index.html`).
2. **Điểm nhấn thiết kế (Google Stitch UI):**
   - Bảng màu tự nhiên **Oceanic Navy & Warm Amber** (loại bỏ màu tím đen cliché của AI).
   - Bố cục **Bento Grid** gồm 4 thẻ KPI tổng quan: Champion Model, Feast Features (13 đặc trưng), Độ trễ suy luận (~0.45 ms), Trạng thái Data Drift (Ổn định).

### 🔹 Bước 3: Thao tác Dự đoán Thời Gian Thực (Single Prediction Demo)
1. **Trường hợp Khách hàng Nguy cơ Cao (High Churn Risk):**
   - Nhập: Độ tuổi `42`, Gói cước `Basic`, Hợp đồng `Monthly`, Cuộc gọi hỗ trợ `5`, Trễ hạn thanh toán `12 ngày`, Tần suất sử dụng `3`.
   - Bấm **"Phân Tích Nguy Cơ Rời Bỏ"**.
   - **Kết quả hiển thị:** Đồng hồ đo nhảy lên mức đỏ `> 85%`, nhãn **High Risk**, độ trễ `< 1ms`.
   - **Hành động đề xuất tự động:** *"ƯU TIÊN KHẨN CẤP: Điều động chuyên viên giải quyết khiếu nại kỹ thuật và tặng 1 tháng dịch vụ miễn phí."*
2. **Trường hợp Khách hàng Trung thành (Low Churn Risk):**
   - Nhập: Hợp đồng `Annual`, Gói cước `Premium`, Cuộc gọi hỗ trợ `0`, Trễ hạn `0 ngày`, Tần suất sử dụng `25`.
   - Bấm **"Phân Tích Nguy Cơ Rời Bỏ"**.
   - **Kết quả hiển thị:** Mức xanh `Low Risk`, đề xuất: *"Chiến dịch Upsell gói dịch vụ nâng cao."*

### 🔹 Bước 4: Thao tác Dự đoán Hàng Loạt qua Tệp CSV (Batch Prediction Demo)
1. Tại tab **"Dự Đoán Hàng Loạt (CSV)"**, bấm nút **"Tải 5 Khách Hàng Mẫu"** (hoặc upload tệp CSV từ `data/raw/`).
2. Bảng kết quả hiển thị ngay lập tức danh sách khách hàng kèm phân loại rủi ro và hành động cụ thể.
3. Bấm **"Xuất Báo Cáo CSV Gắn Nhãn"** để tải về tệp kết quả phân tích.

### 🔹 Bước 5: Trình diễn Bảng So Sánh Mô Hình & Giám Sát Drift
1. Chuyển sang tab **"So Sánh Mô Hình"**: Giới thiệu bảng so sánh 4 thuật toán (Random Forest, XGBoost, LightGBM, Logistic Regression).
2. Chuyển sang tab **"Giám Sát Drift"**: Giải thích kiểm định 2 mẫu Kolmogorov-Smirnov (KS-test) và chỉ số PSI trên 13 đặc trưng. Bấm **"Mở Báo Cáo HTML Chi Tiết"** để mở trang `docs/drift_report.html`.

---

## 3. Các Câu Hỏi Phản Biện Kỹ Thuật Tiêu Biểu & Câu Trả Lời Kiến Trúc (Architecture FAQs)

### ❓ Câu 1: Tại sao hệ thống lại chọn Feast Feature Store mà không truy vấn trực tiếp từ Database?
> **Trả lời:** *"Feast Feature Store giải quyết triệt để vấn đề **Training-Serving Skew** - một lỗi nghiêm trọng trong MLOps khi đặc trưng dùng lúc train bị sai lệch logic so với lúc inference. Feast đồng bộ hóa nguồn dữ liệu Parquet offline cho huấn luyện và SQLite/Redis online cho phục vụ thời gian thực với độ trễ dưới 1ms, hỗ trợ truy vấn điểm thời gian (point-in-time correct) chống rò rỉ dữ liệu."*

### ❓ Câu 2: Tại sao kết quả benchmark của Parquet lại vượt trội so với CSV?
> **Trả lời:** *"Dựa trên thực nghiệm thực tế trên 442,211 bản ghi: Parquet nén Snappy theo dạng cột (Columnar Storage), chỉ đọc đúng các cột cần thiết (Column Projection) thay vì quét toàn bộ dòng như CSV. Kết quả thực nghiệm đo được: Parquet tiết kiệm **73% dung lượng đĩa** (nén 3.7x lần dung lượng) và có tốc độ đọc **nhanh gấp 14.41 lần** (111.77 MB/s so với 28.68 MB/s của CSV)."*

### ❓ Câu 3: Làm thế nào để hệ thống tự động nhận biết khi mô hình suy giảm độ chính xác trên Cloud?
> **Trả lời:** *"Hệ thống tích hợp module kiểm định thống kê Kolmogorov-Smirnov (KS-test) hiệu chỉnh Bonferroni cùng chỉ số PSI. Khi phân phối của dữ liệu khách hàng thực tế bị trôi dạt (Data Drift) vượt ngưỡng 30% số đặc trưng (`drift_share >= 0.30`), endpoint `/drift/status` sẽ gắn cờ cảnh báo và kích hoạt luồng tự động tái huấn luyện mô hình."*
