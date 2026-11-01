# SỔ TAY HƯỚNG DẪN VẬN HÀNH HỆ THỐNG TOÀN DIỆN (MASTER OPERATIONAL RUNBOOK)
## Nền Tảng ChurnGuard-MLOps Level 2 Enterprise Platform

Tài liệu này là cẩm nang vận hành thực nghiệm chuẩn mực cao nhất, cung cấp hướng dẫn chi tiết từng bước (Step-by-Step Operating Guide) để tương tác, kiểm thử và làm chủ toàn bộ các phân hệ của nền tảng ChurnGuard-MLOps.

Mỗi thao tác trong tài liệu đều quy định rõ: **Truy cập đường dẫn nào? Tên trang gì? Thẻ Tab nào? Nhấn nút nào? Nút có màu sắc và hình dáng ra sao? Nút nằm ở vị trí nào (trên/dưới/trái/phải/giữa)? Khi nhấn hiện ra hiện tượng gì? Dấu hiệu nhận biết thành công là gì? Dấu hiệu lỗi thế nào và cách xử lý triệt để ra sao.**

---

## 1. BẢNG TRA CỨU ĐIỂM TRUY CẬP MẠNG & LIÊN KẾT HỆ THỐNG

| Phân Hệ / Giao Diện | Địa Chỉ Truy Cập Mạng (Exact URL) | Giao Thức / Port | Chức Năng Chính & Lưu Ý Điều Hướng |
| :--- | :--- | :--- | :--- |
| **Giao Diện Điều Hành Web Bento Grid** | **`http://localhost:8000/ui`**<br>*(Alias: `http://localhost:8000/web`)* | HTTP / 8000 | **Bàn làm việc điều hành chính:** Form dự đoán thời gian thực cho từng khách hàng, giải thích XAI SHAP, dự đoán hàng loạt CSV, so sánh 4 mô hình và theo dõi drift.<br>**Lưu ý kiến trúc & điều hướng:** Tệp giao diện được phục vụ trực tiếp từ `src/web/` (`index.html`, `app.js`, `style.css`, `charts.js`), không tồn tại thư mục `src/web/static/`. Đường dẫn gốc `http://localhost:8000/` tự động chuyển hướng (`HTTP 307 Temporary Redirect`) sang `/docs`. Để vào Bento Grid, **bắt buộc truy cập `/ui`**. |
| **Bảng Điều Khiển Giám Sát Streamlit** | **`http://localhost:8501`** | HTTP / 8501 | **Trung tâm giám sát vận hành:** 4 tab chuyên sâu gồm `Giám Sát Suy Luận & KPI` (SQLite WAL 9,276 bản ghi), `Giám Sát Data Drift & Cảnh Báo` (PSI & KS-Test), `Thử Nghiệm A/B Testing` (Welch t-test) và `Chẩn Đoán Mô Hình & Phân Tích Lỗi`. |
| **FastAPI Swagger OpenAPI UI** | **`http://localhost:8000/docs`** | HTTP / 8000 | **Kiểm thử REST API tương tác:** Tiêu đề `ChurnGuard MLOps Serving API` v2.0.0. Thực thi trực tiếp các endpoint `/predict`, `/batch_predict`, `/upload_csv_predict`, `/api/v1/trigger_retrain`, `/api/v1/reload_model`. Yêu cầu header xác thực `x-api-key: mlops-churn-secret-2026`. |
| **FastAPI ReDoc Interactive Spec** | **`http://localhost:8000/redoc`** | HTTP / 8000 | **Tài liệu kỹ thuật 3 cột:** Đặc tả chi tiết từng schema Pydantic, tham số header, body JSON và các mã trạng thái phản hồi HTTP. |
| **Tệp Cấu Trúc OpenAPI 3.1.0 JSON** | **`http://localhost:8000/openapi.json`** | HTTP / 8000 | **Định dạng cấu trúc máy đọc:** Phục vụ tích hợp Postman, Swagger Codegen, kịch bản CI/CD và kiểm toán tự động. |
| **Báo Cáo Trực Quan Data Drift HTML** | **`http://localhost:8000/docs/drift_report.html`** | HTTP / 8000 | **Báo cáo chuyên sâu Evidently/Plotly:** Trực quan hóa phân phối xác suất 13 đặc trưng dữ liệu giữa tập Reference (Train) và Current (Inference). |
| **Cổng Đăng Ký Azure for Students** | **`https://azure.microsoft.com/en-us/free/students/`**<br>*(Bản tiếng Việt: `/vi-vn/free/students/`)* | HTTPS / 443 | **Cổng cấp phát tài khoản học viện:** Nhận $100 USD credit miễn phí trong 12 tháng, không yêu cầu thẻ tín dụng, xác thực qua email trường `@student.uit.edu.vn`, tự động kích hoạt Spending Limit: Enabled. |
| **Cổng Quản Trị Microsoft Azure Portal** | **`https://portal.azure.com`** | HTTPS / 443 | **Bảng điều khiển đám mây:** Quản lý Resource Group, kiểm tra Subscription ID, sử dụng Azure Cloud Shell (`>_`), Container Apps, Redis C0 và ACR. |

---

## 2. KHỞI ĐỘNG CÁC PHÂN HỆ DỊCH VỤ CỤC BỘ (LOCAL STARTUP PROCEDURES)

Trước khi thao tác trên trình duyệt, khởi chạy hai phân hệ máy chủ cục bộ bằng hai cửa sổ dòng lệnh riêng biệt:

### 2.1 Khởi động FastAPI Model Serving & Web Console (Port 8000)
1. **Lệnh thực thi trên Windows CMD:**
   ```bash
   cmd /c "python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
   ```
   *(Dành cho lập trình viên phát triển: thêm cờ `--reload` để tự động làm mới mã nguồn).*
2. **Kiến trúc tệp Web phục vụ:**
   - Toàn bộ mã nguồn giao diện người dùng nằm trực tiếp trong thư mục `src/web/` (`index.html`, `app.js`, `style.css`, `charts.js`).
   - Trong `src/api/main.py`, FastAPI gán biến `WEB_DIR = os.path.join(BASE_DIR, "src", "web")` và mount trực tiếp vào `/ui` và `/web`. **Không có thư mục `src/web/static/`**.
3. **Tiến trình khởi tạo nội tại (Lifespan Startup):**
   - Hệ thống tự động nạp mô hình Champion XGBoost (`champion_model.joblib`), bộ tiền xử lý chuẩn hóa (`scaler.joblib`) và siêu dữ liệu huấn luyện (`metadata.json`).
   - Khởi tạo bộ giải thích giải thuật cây SHAP `TreeExplainer(clf)` với dự phòng `LinearExplainer`.
   - Kết nối cơ sở dữ liệu SQLite tại `data/inference_logs.db`, thiết lập chế độ an toàn luồng `PRAGMA journal_mode=WAL;`.
4. **Dấu hiệu THÀNH CÔNG:**
   - Màn hình terminal xuất hiện các dòng log tiêu chuẩn:
     ```text
     INFO:     Started server process [PID]
     INFO:     Waiting for application startup.
     INFO:     Application startup complete.
     INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
     ```
5. **Dấu hiệu LỖI & Cách xử lý triệt để:**
   - **Hiện tượng 1: Cổng 8000 bị chiếm dụng (`[Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)`):**
     * *Nguyên nhân:* Tiến trình Uvicorn cũ hoặc ứng dụng khác đang chạy ngầm trên cổng 8000.
     * *Bước 1:* Tìm mã tiến trình (PID) đang chiếm cổng:
       ```bash
       cmd /c "netstat -ano | findstr :8000"
       ```
       *(Ví dụ kết quả: `TCP 0.0.0.0:8000 ... LISTENING 14280`)*
     * *Bước 2:* Tiêu diệt tiến trình:
       ```bash
       cmd /c "taskkill /F /PID 14280"
       ```
     * *Bước 3:* Chạy lại lệnh khởi động Uvicorn.
   - **Hiện tượng 2: Thiếu tệp mô hình (`FileNotFoundError: champion_model.joblib`):**
     * *Khắc phục:* Chạy pipeline huấn luyện trước khi phục vụ: `cmd /c "python src/models/train_pipeline.py"`.
   - **Hiện tượng 3: Thiếu gói phụ thuộc (`ModuleNotFoundError: No module named 'fastapi'`):**
     * *Khắc phục:* Cài đặt môi trường: `cmd /c "pip install -r requirements.txt"`.

---

### 2.2 Khởi động Streamlit Observability Dashboard (Port 8501)
1. **Mở thêm một cửa sổ Terminal mới** và thực thi:
   ```bash
   cmd /c "streamlit run src/web/dashboard.py --server.port 8501"
   ```
2. **Dấu hiệu THÀNH CÔNG:**
   - Terminal hiển thị thông tin lắng nghe mạng:
     ```text
     You can now view your Streamlit app in your browser.
     Local URL: http://localhost:8501
     Network URL: http://...:8501
     ```
   - Trình duyệt tự động mở tab mới truy cập `http://localhost:8501`.
3. **Dấu hiệu LỖI & Cách xử lý:**
   - **Báo lỗi thiếu gói:** Chạy `cmd /c "pip install streamlit plotly scipy"`.
   - **Cổng 8501 bị chiếm:** Đổi cổng linh hoạt bằng cách thêm tham số `--server.port 8502`.

---

## 3. HƯỚNG DẪN CHI TIẾT GIAO DIỆN WEB BENTO GRID CONSOLE (`http://localhost:8000/ui`)

- **Địa chỉ truy cập chính xác:** **`http://localhost:8000/ui`** (hoặc `http://localhost:8000/ui/index.html`, alias `http://localhost:8000/web`).
- **Hành vi đường dẫn gốc `/`:** Truy cập `http://localhost:8000/` sẽ nhận mã `HTTP 307 Temporary Redirect` chuyển hướng sang `/docs`. Muốn vào Web Console Bento Grid, người dùng **bắt buộc phải nhập hậu tố `/ui`**.
- **Tiêu đề trang (HTML Title Tag):** `ChurnGuard MLOps - Enterprise Customer Retention Platform`.
- **Cấu trúc tệp vật lý:** Toàn bộ giao diện được phục vụ trực tiếp từ `src/web/` (`index.html`, `app.js`, `style.css`, `charts.js`). Không sử dụng thư mục con `static/`.

---

### 3.1 Cấu trúc định danh, Header Navbar & Hàng 4 Thẻ KPI

1. **Thanh điều hướng cố định đỉnh trang (Fixed Header Navbar):**
   - **Khối Logo thương hiệu (Góc trên bên trái):**
     * Biểu tượng SVG (kích thước 36x36px): Hình khiên Deep Teal `#0F766E` kết hợp đường xung nhịp tim ECG màu Cam Hổ Phách `#F59E0B` (độ dày nét 2.5px).
     * Chữ thương hiệu: Tiêu đề chính `CHURN` màu Trắng Ngà `#F8FAFC` kết hợp `GUARD` màu Cam Hổ Phách `#F59E0B` (font Outfit 20px, font-weight 800), phụ đề `ENTERPRISE MLOPS` (màu `#64748B`, font 10px, letter-spacing 1px).
   - **Khối trạng thái kết nối & Phiên bản mô hình (Góc trên bên phải):**
     * Chấm trạng thái nhấp nháy `.pulse-dot` (8x8px, bo tròn 50%, màu Xanh Lục Emerald `#10B981`, phát sáng `box-shadow: 0 0 8px #10B981`, hiệu ứng animation `pulse 2s infinite`).
     * Nhãn trạng thái API (`#api-status-text`): Khi server hoạt động hiển thị **`FastAPI: HEALTHY (Online)`**; khi mất kết nối chuyển sang **`FastAPI: Offline (Chưa bật server)`**.
     * Huy hiệu Champion Model (`.model-badge`): Nền xanh đen `#0F2942`, viền `1px solid #233554`, chữ Xanh Da Trời `#38BDF8`. Nội dung: `Champion: XGBoost` (hoặc `Chưa kết nối` nếu mất server).

2. **Hàng 4 thẻ chỉ số KPI trên cùng (`.kpi-row`, grid 4 cột bằng nhau, gap 16px):**
   - **Thẻ 1 (Ngoài cùng bên trái):** Tiêu đề: `MÔ HÌNH CHAMPION` (màu `#64748B`, font 11px) | Giá trị chính: `XGBoost` | Dòng phụ: `ROC-AUC: 0.9989 | F1: 0.9785` (chữ số màu xanh ngọc `#10B981`).
   - **Thẻ 2 (Giữa trái):** Tiêu đề: `FEAST FEATURE STORE` | Giá trị chính: `13 Features` | Dòng phụ: `CONNECTED (SQLite Only - Redis Offline)` (hoặc thông tin chuỗi do API `/health` trả về).
   - **Thẻ 3 (Giữa phải):** Tiêu đề: `ĐỘ TRỄ DỰ ĐOÁN (INFERENCE)` | Giá trị chính: `0.45 ms` (hoặc độ trễ đo thực tế) | Dòng phụ: `SLA: Tối ưu (< 10ms)` (chữ xanh ngọc `#10B981`).
   - **Thẻ 4 (Ngoài cùng bên phải):** Tiêu đề: `TRẠNG THÁI DATA DRIFT` | Giá trị chính: `ỔN ĐỊNH` (`#10B981`) hoặc `CẢNH BÁO DRIFT` (`#EF4444`) | Dòng phụ: `Kiểm định KS-Test & PSI: Bonferroni`.

3. **Khu vực làm việc Workspace 2 cột tỷ lệ 5:7 (`.workspace-grid`, gap 24px):**
   - **Cột bên trái (Tỷ lệ 5/12):** Form dự đoán thời gian thực cho từng khách hàng (`#prediction-form`) và Khung kết quả XAI SHAP (`#prediction-result`).
   - **Cột bên phải (Tỷ lệ 7/12):** Thẻ phân tích gồm hệ thống 3 Tab (Dự Đoán Hàng Loạt CSV, So Sánh Mô Hình, Giám Sát Drift).

---

### 3.2 Thao tác 1: Dự đoán thời gian thực cho 1 khách hàng đơn lẻ (Single Prediction)

- **Vị trí thao tác:** Thẻ Bento ở **Cột bên trái màn hình**, bên dưới tiêu đề `Dự Đoán Thời Gian Thực` (kèm huy hiệu nhỏ `REST API: /predict`).

#### A. Bảng kiểm kê toàn diện 11 ô nhập liệu Form Dự Đoán (`#prediction-form`)
Xếp thành 6 hàng (`.form-row`, grid 2 cột `1fr 1fr`, gap 12px). Đối chiếu 100% với nhãn HTML và schema Pydantic `src/api/schemas.py`:

| STT | Vị trí trong Form | Element ID | Thẻ HTML & Type | Nhãn văn bản đầy đủ (`<label>`) | Giá trị mặc định (`value`) | Giới hạn HTML5 (`min/max`) | Ràng buộc Backend Pydantic (`src/api/schemas.py`) | Ghi chú & Tùy chọn |
| :---: | :--- | :--- | :---: | :--- | :---: | :---: | :--- | :--- |
| **1** | Hàng 1, Cột trái | `inp-customer-id` | `<input type="number">` | `Mã khách hàng (Customer ID)` | `1001` | `min="1"` | `customer_id: Optional[int] >= 1` | Bắt buộc (`required`). Nếu trống JS fallback về 1001. |
| **2** | Hàng 1, Cột phải | `age` | `<input type="number">` | `Độ tuổi` | `38` | `min="18" max="100"` | `age: float, ge=18, le=100` | Bắt buộc (`required`), chặn NaN/Inf. |
| **3** | Hàng 2, Cột trái | `gender` | `<select>` | `Giới tính` | `Male` | N/A | `gender: Literal["Female", "Male"]` | Dropdown: `Nữ (Female)` và `Nam (Male)` (selected). |
| **4** | Hàng 2, Cột phải | `tenure` | `<input type="number">` | `Thời gian gắn bó (tháng)` | `24` | `min="0"` | `tenure: float, ge=0, le=120` | Bắt buộc (`required`), chặn số âm. |
| **5** | Hàng 3, Cột trái | `usage_frequency` | `<input type="number">` | `Tần suất sử dụng (lần/tháng)` | `18` | `min="0"` | `usage_frequency: float, ge=0, le=50` | Bắt buộc (`required`). |
| **6** | Hàng 3, Cột phải | `support_calls` | `<input type="number">` | `Số cuộc gọi hỗ trợ` | `4` | `min="0"` | `support_calls: float, ge=0, le=30` | Bắt buộc (`required`). |
| **7** | Hàng 4, Cột trái | `payment_delay` | `<input type="number">` | `Trễ hạn thanh toán (ngày)` | `8` | `min="0"` | `payment_delay: float, ge=0, le=90` | Bắt buộc (`required`). |
| **8** | Hàng 4, Cột phải | `subscription_type` | `<select>` | `Gói cước` | `Standard` | N/A | `Literal["Basic", "Standard", "Premium"]` | Dropdown: `Basic`, `Standard` (selected), `Premium`. |
| **9** | Hàng 5, Cột trái | `contract_length` | `<select>` | `Loại hợp đồng` | `Monthly` | N/A | `Literal["Monthly", "Quarterly", "Annual"]` | Dropdown: `Theo Tháng (Monthly)` (selected), `Theo Quý (Quarterly)`, `Theo Năm (Annual)`. |
| **10**| Hàng 5, Cột phải | `total_spend` | `<input type="number">` | `Tổng chi tiêu ($)` | `450` | `min="0"` | `total_spend: float, ge=0, le=100000` | Bắt buộc (`required`). |
| **11**| Hàng 6, Cột trái | `last_interaction` | `<input type="number">` | `Lần tương tác cuối (ngày)` | `15` | `min="0"` | `last_interaction: float, ge=0, le=60` | Bắt buộc (`required`). Cột phải hàng 6 để trống. |

#### B. Quy cách nút bấm dự đoán đơn lẻ (`#btn-submit-single`)
- **ID phần tử:** `#btn-submit-single`
- **Thẻ HTML:** `<button type="submit" class="btn btn-primary" id="btn-submit-single">Phân Tích Nguy Cơ Rời Bỏ</button>`
- **Chữ in trên nút:** **`Phân Tích Nguy Cơ Rời Bỏ`**
- **Màu sắc & Kiểu dáng:** Nút hình chữ nhật bo góc 8px (`border-radius: 8px`), nền màu **Cam Hổ Phách (Amber `#F59E0B`)**, chữ in đậm màu **Xanh Đen Midnight Navy (`#0A192F`)**, `font-weight: 700`, đệm `padding: 10px 18px`.
- **Hiệu ứng Hover:** Nền chuyển sang `#D97706`, nút trồi lên 2px (`transform: translateY(-2px)`), xuất hiện bóng mờ cam `box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35)`.
- **Vị trí không gian:** Nằm ở **DƯỚI CÙNG của khối Form bên trái** (dưới hàng 6 của form), chiếm 100% chiều ngang hàng nút.
- **Hành vi tức thời khi bấm:**
  * Nhãn nút đổi ngay lập tức thành: **`Đang Phân Tích...`**
  * Thuộc tính `disabled = true` được kích hoạt (chống bấm lặp gửi request trùng).
  * Con trỏ chuột chuyển sang biểu tượng chờ.
  * Sau khi nhận phản hồi từ backend (trong khối `finally`): nhãn nút phục hồi về `Phân Tích Nguy Cơ Rời Bỏ` và `disabled = false`.

#### C. Dấu hiệu THÀNH CÔNG (Phân tích kết quả trả về trong `#prediction-result`)
Sau khi bấm, khối `#prediction-result` trượt mở ra với animation `fadeIn 0.3s ease`:
1. **Khung chứa chính:** Nền Navy nổi `#1E3A5F`, viền `1px solid #233554`, bo góc 10px, đệm 16px.
2. **Huy hiệu rủi ro (`#risk-badge`) ở góc trên bên trái khung kết quả:**
   - **Xác suất $\ge 70\%$ (`churn_probability >= 0.70`):**
     * Lớp CSS: `risk-badge risk-high`
     * Nội dung: **`RỦI RO CAO (HIGH RISK)`**
     * Màu chữ & viền: Đỏ tươi Crimson **`#EF4444`** (`border: 1px solid #EF4444`)
     * Nền: Mờ 20% đỏ `rgba(239, 68, 68, 0.2)`
   - **Xác suất $40\% - 69.9\%$ (`0.40 <= churn_probability < 0.70`):**
     * Lớp CSS: `risk-badge risk-medium`
     * Nội dung: **`RỦI RO TRUNG BÌNH (MEDIUM RISK)`**
     * Màu chữ & viền: Vàng Cam Amber **`#FBBF24`** (`border: 1px solid #FBBF24`)
     * Nền: Mờ 20% vàng `rgba(251, 191, 36, 0.2)`
   - **Xác suất $< 40\%$ (`churn_probability < 0.40`):**
     * Lớp CSS: `risk-badge risk-low`
     * Nội dung: **`AN TOÀN (LOW RISK)`**
     * Màu chữ & viền: Xanh Ngọc Emerald **`#10B981`** (`border: 1px solid #10B981`)
     * Nền: Mờ 20% xanh `rgba(16, 185, 129, 0.2)`
3. **Huy hiệu độ trễ (`#result-latency`) ở góc trên bên phải:** Hiển thị thời gian nội suy thực tế (ví dụ: `0.42 ms`), màu xám `#64748B`, font 12px.
4. **Thanh đo xác suất trực quan (`.gauge-container`):**
   - Số phần trăm lớn (`#prob-display`): font Outfit 32px, font-weight 800, định dạng `(Number(prob) * 100).toFixed(1) + "%"` (ví dụ: **`88.5%`**).
   - Thanh đo nằm ngang (`#gauge-fill` bên trong nền `#0A192F`): Đổ đầy tương ứng với xác suất, màu sắc đồng bộ: High `#EF4444`, Medium `#FBBF24`, Low `#10B981`.
5. **Khung đề xuất hành động giữ chân (`.action-box`):**
   - Viền trái màu Cam Hổ Phách `#F59E0B` dày 3px, nền `rgba(10, 25, 47, 0.6)`.
   - Tiêu đề: `HÀNH ĐỘNG GIỮ CHÂN ĐỀ XUẤT:` (chữ hoa màu cam `#F59E0B`, font 11px, font-weight 700).
   - Đoạn văn khuyến nghị (`#recommendation-text`): Sinh ra từ hàm chuẩn hóa $e\text{-Profits}$ (`src/api/utils.py`).
     *Đối với bộ dữ liệu mặc định của Form* (Tuổi 38, Nam, Gắn bó 24 tháng, Gọi hỗ trợ 4 lần, Chậm trả 8 ngày, Gói Standard, Hợp đồng Monthly, Tổng chi $450, Tương tác cuối 15 ngày):
      **`ƯU TIÊN KHẨN CẤP (CLV Cao $450, Hợp đồng Monthly): Điều động chuyên viên VIP giải quyết khiếu nại kỹ thuật và tặng 1 tháng dịch vụ.`**
6. **Khung giải thích mô hình XAI SHAP Attributions (`#xai-box`):**
   - Tiêu đề: `GIẢI THÍCH MÔ HÌNH (XAI - SHAP ATTRIBUTIONS)` màu `#38BDF8`, kèm badge `NeurIPS 2017`.
   - Tóm tắt tự động (`#xai-summary-text`): Ví dụ `"Đặc trưng thúc đẩy rời bỏ chính (base_value=-0.124): support_calls (SHAP: +0.284) | payment_delay (SHAP: +0.195) | ..."`
   - Danh sách thanh đo SHAP (`#xai-bars`):
     * **Yếu tố làm tăng nguy cơ rời bỏ (`weight >= 0`):** Nhãn giá trị mang dấu `+` màu cam `#F59E0B` (`.xai-val-pos`). Thanh đo gradient từ Cam sang Đỏ: `linear-gradient(90deg, #F59E0B, #EF4444)`.
     * **Yếu tố giữ chân / giảm nguy cơ rời bỏ (`weight < 0`):** Nhãn giá trị mang dấu `-` màu xanh `#10B981` (`.xai-val-neg`). Thanh đo gradient từ Xanh Da Trời sang Xanh Lục: `linear-gradient(90deg, #0EA5E9, #10B981)`.

#### D. Dấu hiệu LỖI & Cách xử lý triệt để
1. **Lỗi nhập liệu phía Client (HTML5 Validation Tooltip):**
   - Nếu người dùng nhập tuổi < 18 hoặc > 100, để trống các trường bắt buộc, hoặc nhập số âm ở các trường `min="0"`:
   - Trình duyệt tự động kích hoạt bong bóng thông báo HTML5 mặc định (Tooltip): *"Please enter a number greater than or equal to 18"*, chặn không gửi request ra mạng.
2. **Lỗi xác thực dữ liệu Backend Pydantic (HTTP 422 Unprocessable Entity):**
   - Xảy ra khi dữ liệu gửi lên vi phạm schema Pydantic (`src/api/schemas.py`): ví dụ `support_calls > 30`, `payment_delay > 90`, `tenure > 120`, hoặc trường chứa giá trị `NaN`/`Inf`.
   - Frontend `app.js` bắt lỗi trong khối `catch` và hiển thị hộp thoại trình duyệt `alert(...)`.
   - *Khắc phục:* Nhập lại các giá trị nằm đúng trong khoảng cho phép của bảng kiểm kê 3.2.A.
3. **Lỗi máy chủ FastAPI Serving Offline (Không kết nối được Port 8000):**
   - Khi bấm `Phân Tích Nguy Cơ Rời Bỏ` mà máy chủ chưa chạy hoặc tiến trình bị tắt:
     * Hộp thoại trình duyệt hiện thông báo: **`Không thể kết nối đến FastAPI Serving Endpoint! Đảm bảo server đang chạy tại port 8000.`**
     * Nút submit lập tức chuyển trạng thái từ `Đang Phân Tích...` trở lại `Phân Tích Nguy Cơ Rời Bỏ`, kích hoạt lại quyền bấm (`disabled = false`).
     * Trên thanh Navbar: Chữ trạng thái `#api-status-text` đổi thành **`FastAPI: Offline (Chưa bật server)`**, huy hiệu Champion đổi thành **`Chưa kết nối`**.
     * Trên Tab 2 (So Sánh Mô Hình): Hai khung biểu đồ Chart.js phủ lớp thông báo lỗi nền xám đậm `rgba(15, 23, 42, 0.88)`:  
       **`[CẢNH BÁO] Mất Kết Nối Backend API`** (màu đỏ `#EF4444`)  
       **`Khởi động FastAPI tại port 8000`** (màu xám `#94A3B8`).

---

### 3.3 Thao tác 2: Dự đoán hàng loạt bằng 5 khách hàng mẫu (Sample Batch)

- **Vị trí thao tác:** Thẻ Bento ở **Cột bên phải màn hình**, tại Tab 1: **`Dự Đoán Hàng Loạt (CSV)`** (chọn mặc định khi tải trang).
- **Quy cách nút bấm:**
  * **ID phần tử:** `#btn-sample-batch`
  * **Thẻ HTML:** `<button type="button" class="btn btn-outline" id="btn-sample-batch">Tải 5 Khách Hàng Mẫu</button>`
  * **Chữ in trên nút:** **`Tải 5 Khách Hàng Mẫu`**
  * **Màu sắc & Kiểu dáng:** Nút viền ngoài trong suốt (Outline Button), viền `1px solid #38BDF8`, chữ màu **Xanh Da Trời (Sky Blue `#38BDF8`)**, font-weight 600, bo góc 8px. Khi rê chuột (hover) phủ lớp nền mờ `rgba(56, 189, 248, 0.1)`.
  * **Vị trí không gian:** Nằm ở **Cột bên phải**, trong Tab 1, vị trí **BÊN PHẢI** trong cụm 2 nút hành động (`.batch-actions`) bên dưới khung drop-zone (cạnh nút "Chọn Tệp CSV").
- **Thao tác thực hiện:**
  1. Bấm chuột trái vào nút **`Tải 5 Khách Hàng Mẫu`**.
  2. Giao diện gửi ngay mảng JSON gồm 5 khách hàng (#101 đến #105) tới `POST /batch_predict`.
- **Dấu hiệu THÀNH CÔNG:**
  - Khung `#batch-results-container` xuất hiện với 4 viên thuốc thống kê (Stat Pills) nằm ngang:
    * Viên 1: `Tổng số: 5`
    * Viên 2: `Rời bỏ: X` (chữ số màu Đỏ `#EF4444`)
    * Viên 3: `Ở lại: Y` (chữ số màu Xanh Lục `#10B981`)
    * Viên 4: `Tỷ lệ: Z%` (chữ số màu Cam Hổ Phách `#F59E0B`)
  - Bảng dữ liệu chi tiết hiện ra gồm 5 dòng: Cột Mã Khách Hàng, Xác Suất Churn, Mức Độ Rủi Ro (gắn huy hiệu màu), và Hành Động Giữ Chân.
  - Dưới cùng của bảng xuất hiện nút **`Xuất Báo Cáo CSV Gắn Nhãn`** (`#btn-download-batch-csv`):
    * Thẻ HTML: `<button class="btn btn-primary" id="btn-download-batch-csv">Xuất Báo Cáo CSV Gắn Nhãn</button>`
    * Màu sắc: Nền **Cam Hổ Phách (`#F59E0B`)**, chữ Xanh Đen `#0A192F` font-weight 700.
    * Khi bấm: Tự động tải xuống tệp `churn_predictions_annotated_<timestamp>.csv` gồm 5 cột: `CustomerID,ChurnPrediction,ChurnProbability,RiskLevel,RecommendedAction` mà không cần gọi lại API.

---

### 3.4 Thao tác 3: Tải tệp CSV tùy chỉnh từ máy tính để phân tích lô (CSV Upload)

- **Vị trí thao tác:** Vẫn tại Tab 1 **`Dự Đoán Hàng Loạt (CSV)`** ở cột bên phải.
- **Quy cách nút bấm:**
  * **ID phần tử:** `#btn-browse-file`
  * **Thẻ HTML:** `<button type="button" class="btn btn-secondary" id="btn-browse-file">Chọn Tệp CSV</button>`
  * **Chữ in trên nút:** **`Chọn Tệp CSV`**
  * **Màu sắc & Kiểu dáng:** Nút màu **Xanh Rêu Đậm (Deep Teal `#0F766E`)**, chữ in màu trắng `#FFFFFF`, font-weight 600, bo góc 8px. Khi hover đổi sang `#115E59`.
  * **Vị trí không gian:** Nằm ở **Cột bên phải**, trong Tab 1, vị trí **BÊN TRÁI** trong cụm nút `.batch-actions` (dưới biểu tượng đám mây tải lên SVG nét xanh trời `#38BDF8`).
- **Thao tác thực hiện:**
  1. Bấm chuột trái vào nút **`Chọn Tệp CSV`** (hoặc kéo thả tệp trực tiếp vào khung nét đứt `#drop-zone`).
  2. Hộp thoại Windows Explorer mở ra. Chọn tệp dữ liệu kiểm thử có sẵn:  
     `c:\Users\Nguyen Trong Khoi\Downloads\CLOUD\data\raw\customer_churn_dataset-testing-master.csv`
  3. Bấm **Open** để xác nhận tải tệp. Hàm JavaScript `uploadCsvFile(file)` tự động gửi tệp qua `POST /upload_csv_predict`.
- **Dấu hiệu THÀNH CÔNG:**
  - Sau 1 - 2 giây, bảng thống kê tự động hiển thị tổng số dòng xử lý, tỷ lệ rời bỏ và danh sách 10 dòng đầu tiên được gắn nhãn.
  - Bấm nút màu cam **`Xuất Báo Cáo CSV Gắn Nhãn`** để tải toàn bộ tệp kết quả.
- **Dấu hiệu LỖI & Cách xử lý:**
  - **Lỗi `400 Bad Request` (`Vui lòng chỉ tải lên tệp định dạng CSV!`):** Do tải tệp đuôi `.xlsx` hoặc `.txt`. Chọn đúng tệp có đuôi `.csv`.
  - **Lỗi `400 Bad Request` (`Tệp CSV thiếu cột bắt buộc: <tên_cột>`):** Tệp thiếu 1 trong 10 cột Kaggle bắt buộc. Sử dụng tệp mẫu chuẩn trong `data/raw/`.
  - **Lỗi `422 Unprocessable Entity` (`Dòng X: Cột 'Y' chứa giá trị trống (NaN)`):** Dữ liệu có ô trống chưa được điền. Cần tiền xử lý điền khuyết trước khi tải lên.
  - **Lỗi `422 Unprocessable Entity` (`Batch size exceeds maximum limit of 1000`):** Tệp vượt quá giới hạn an toàn 1,000 dòng. Cần trích xuất tập mẫu con $\le 1000$ dòng để tải lên giao diện web.

---

### 3.5 Thao tác 4: Đối chuẩn 4 mô hình & Đồ thị hội tụ Optuna (Model Comparison)

- **Vị trí thao tác:** Nhìn lên thanh chuyển Tab ở trên cùng của Thẻ Bento Cột bên phải (`.tab-header`).
- **Nút Tab cần chọn:**
  * **Tên Tab:** **`So Sánh Mô Hình`** (`<button class="tab-btn" data-tab="tab-models">So Sánh Mô Hình</button>`)
  * **Vị trí:** Nằm ở **CHÍNH GIỮA thanh chuyển Tab** (giữa tab "Dự Đoán Hàng Loạt" và tab "Giám Sát Drift").
- **Thao tác:** Bấm chuột trái vào tab **`So Sánh Mô Hình`**. Lớp `.tab-btn.active` được kích hoạt với nền xanh đậm `#1E3A5F` và chữ màu Xanh Da Trời `#38BDF8`.
- **Dấu hiệu THÀNH CÔNG:**
  - **Bảng đối chuẩn phía trên:** Hiển thị 4 mô hình máy học:
    1. `XGBoost (Champion)` (có huy hiệu chữ Champion màu cam nổi bật).
    2. `LightGBM`
    3. `Random Forest`
    4. `Logistic Regression`  
    Kèm các cột chỉ số đo lường trên tập kiểm thử: Accuracy, Precision, Recall, F1-Score, và ROC-AUC (XGBoost đạt **`0.9989`** màu xanh ngọc vượt trội).
  - **Biểu đồ cột bên trái:** Đồ thị tương tác Chart.js so sánh trực quan các chỉ số giữa 4 giải thuật.
  - **Biểu đồ đường bên phải:** Đồ thị hội tụ siêu tham số Optuna Bayesian TPE qua 12 trials, thể hiện ROC-AUC tăng dần đến điểm cực trị `0.9990`.
- **Dấu hiệu LỖI:** Nếu mất kết nối API, hai khung biểu đồ Chart.js phủ lớp thông báo lỗi `.chart-offline-notice` (nền `rgba(15, 23, 42, 0.88)`):  
  **`[CẢNH BÁO] Mất Kết Nối Backend API`** (màu đỏ `#EF4444`)  
  **`Khởi động FastAPI tại port 8000`** (màu xám `#94A3B8`).

---

### 3.6 Thao tác 5: Giám sát trôi dạt dữ liệu & Báo cáo HTML chuyên sâu (Drift Monitoring)

- **Vị trí thao tác:** Nhìn lên thanh chuyển Tab ở Thẻ Bento Cột bên phải.
- **Nút Tab cần chọn:**
  * **Tên Tab:** **`Giám Sát Drift`** (`<button class="tab-btn" data-tab="tab-drift">Giám Sát Drift</button>`)
  * **Vị trí:** Nằm ở **GÓC NGOÀI CÙNG BÊN PHẢI của thanh chuyển Tab**.
- **Thao tác:** Bấm chuột trái vào tab **`Giám Sát Drift`**.
- **Dấu hiệu THÀNH CÔNG:**
  - Hiển thị bảng đối soát thống kê 13 đặc trưng dữ liệu với các cột: Tên Đặc Trưng, Điểm KS-Statistic, P-Value Kolmogorov-Smirnov, Điểm PSI, và Huy hiệu trạng thái (`Stable` màu xanh lục, `Moderate` màu vàng, `High` màu đỏ).
  - Tìm nút mở báo cáo chi tiết:
    * **Thẻ HTML:** `<a href="/docs/drift_report.html" target="_blank" class="btn btn-outline btn-sm">Mở Báo Cáo HTML Chi Tiết</a>`
    * **Chữ in trên nút:** **`Mở Báo Cáo HTML Chi Tiết`**
    * **Kiểu dáng:** Nút viền ngoài mỏng `1px solid #38BDF8`, chữ màu Xanh Da Trời `#38BDF8`, padding `6px 12px`, font 12px.
    * **Vị trí chính xác:** Nằm ở **GÓC TRÊN BÊN PHẢI của khung tiêu đề Giám Sát Drift** (trong `.drift-header-box`).
  - Bấm vào nút này -> Trình duyệt tự động mở tab mới truy cập:  
    **`http://localhost:8000/docs/drift_report.html`** hiển thị toàn bộ biểu đồ phân phối xác suất tương tác Evidently/Plotly.
- **Dấu hiệu LỖI:** Nếu trình duyệt báo `404 Not Found`, tệp HTML chưa được sinh. Chạy lệnh: `cmd /c "python src/monitoring/drift_detector.py"`.

---

## 4. HƯỚNG DẪN CHI TIẾT BẢNG ĐIỀU KHIỂN GIÁM SÁT STREAMLIT (`http://localhost:8501`)

- **Địa chỉ truy cập chính xác:** **`http://localhost:8501`**
- **Tiêu đề tab trình duyệt:** `ChurnGuard MLOps Enterprise Dashboard`
- **Tiêu đề H1 trung tâm:** `[MONITOR] ChurnGuard Enterprise MLOps Monitoring Dashboard`
- **Phụ đề H1:** `Hệ thống giám sát toàn diện: Suy luận thời gian thực, Data Drift (PSI), A/B Testing và Chẩn đoán lỗi mô hình.`

---

### 4.1 Nhận diện trang & Thanh điều khiển Sidebar (`src/web/dashboard.py`)

1. **Cấu hình trang:** `st.set_page_config(page_title="ChurnGuard MLOps Enterprise Dashboard", layout="wide", initial_sidebar_state="expanded")`.
2. **Thanh bên trái (Sidebar):**
   - **Tiêu đề Sidebar:** `ChurnGuard MLOps`
   - **Phụ đề Sidebar:** `Enterprise Observability & Model Serving Platform`
   - Đường kẻ phân cách ngang: `---`
   - **Danh sách 4 dòng Metadata hệ thống:**
     * `- **Pipeline:** DVC + MLflow 3.16`
     * `- **Feature Store:** Feast 0.66`
     * `- **Champion Model:** XGBoost (AUC: 0.9990)`
     * `- **A/B Split:** 80% Champ / 20% Chall`
   - Đường kẻ phân cách ngang: `---`
   - **Nút bấm làm mới dữ liệu duy nhất:**
     * **Tên nhãn nút:** **`"Làm mới ngay (Refresh)"`**
     * **Vị trí:** Nằm ở **DƯỚI CÙNG của Sidebar**, ngay bên dưới đường kẻ phân cách thứ 2.
     * **Hành vi khi bấm:** Kích hoạt lệnh `st.rerun()`. Hàm `load_inference_logs()` kết nối trực tiếp SQLite WAL (`PRAGMA journal_mode=WAL;`) và không dùng cache, nạp lại tức thì toàn bộ bản ghi mới nhất từ `data/inference_logs.db`.
   - **Xác nhận thành phần loại trừ:** Trong Sidebar **HOÀN TOÀN KHÔNG CÓ** bộ chọn ngày tháng (Date Range Picker) hay bất kỳ widget bộ lọc nào (Selectbox/Multiselect). Thiết kế tối giản, tập trung vào quan sát thời gian thực.

---

### 4.2 Tab 1: `Giám Sát Suy Luận & KPI`

- **Vị trí:** Tab đầu tiên bên trái trên thanh tab ngang.
- **Nguồn dữ liệu:** Bảng `inference_logs` trong cơ sở dữ liệu `data/inference_logs.db` (hiện có 9,276 bản ghi thực tế: 8,995 Champion, 281 Challenger).
- **Hàng 4 thẻ Bento Card (`.metric-card`, dải màu `#0A2540` sang `#1A365D`, số màu Mint Teal `#00D4B2` 28px bold):**
  1. **Thẻ 1 (Trái cùng):** Tiêu đề `"TỔNG LƯỢT SUY LUẬN"` | Giá trị: `{total_inf:,}` (ví dụ: `9,276`) | Phụ đề: `"Lưu trữ trong SQLite Database"`.
  2. **Thẻ 2 (Giữa trái):** Tiêu đề `"TỶ LỆ DỰ ĐOÁN RỜI BỎ"` | Giá trị: `{churn_rate:.1f}%` (ví dụ: `55.2%`) | Phụ đề: `{churn_cnt:,} / {total_inf:,} khách hàng`.
  3. **Thẻ 3 (Giữa phải):** Tiêu đề `"ĐIỀU HƯỚNG CHAMPION"` | Giá trị: `{champ_pct:.1f}%` (ví dụ: `97.0%`) | Phụ đề: `"Mục tiêu: 80% (XGBoost)"`.
  4. **Thẻ 4 (Phải cùng):** Tiêu đề `"TRẠNG THÁI PHỤC VỤ"` | Giá trị: `"HOẠT ĐỘNG (ONLINE)"` (màu xanh lục Emerald `#06D6A0`) | Phụ đề: `"FastAPI + Feast Online Store"`.
- **Bảng nhật ký suy luận thời gian thực (`Nhật Ký Suy Luận Thời Gian Thực Gần Nhất`):**
  - Hiển thị qua `st.dataframe(disp_df, use_container_width=True, height=320)`.
  - Các cột: `id`, `timestamp`, `customer_id`, `churn_prediction`, `churn_probability`, `model_version`.
  - Cột `churn_prediction` được gắn nhãn trực quan: `"Rời bỏ (1)"` hoặc `"Giữ chân (0)"`.
  - Cột `churn_probability` được làm tròn 4 chữ số thập phân (`f"{p:.4f}"`).
  - Cho phép người dùng nhấp tiêu đề cột để sắp xếp tăng/giảm, tìm kiếm văn bản trong bảng, kéo thả độ rộng cột.
- **Trạng thái rỗng (Fallback):** Nếu database chưa có bản ghi, hiển thị banner thông tin:  
  `st.info("Chưa có lượt suy luận nào được ghi nhận. Hãy gửi yêu cầu dự đoán qua REST API.")`.
- **Lưu ý đối soát:** Tab 1 **KHÔNG** chứa biểu đồ Plotly; thông tin được trình bày qua 4 thẻ KPI Bento và bảng tương tác 320px.

---

### 4.3 Tab 2: `Giám Sát Data Drift & Cảnh Báo`

- **Vị trí:** Tab thứ 2 từ trái sang.
- **Nguồn dữ liệu:** Tệp JSON `data/processed/drift_metrics.json` (chứa kiểm định 13 đặc trưng dữ liệu giữa 309,547 mẫu huấn luyện và các mẫu suy luận).
- **Khung cảnh báo ngưỡng trôi dạt tự động:**
  - Nếu tỷ lệ đặc trưng lệch phân phối `drift_share >= 0.30` (ngưỡng 30%):  
    Hiện banner đỏ `st.error`: `CẢNH BÁO DATA DRIFT: Phát hiện X/13 đặc trưng bị lệch phân phối (Tỷ lệ: Y% >= ngưỡng 30%). Khuyến nghị kích hoạt Webhook tái huấn luyện tự động!`
  - Nếu `drift_share < 0.30`:  
    Hiện banner xanh lá `st.success`: `HỆ THỐNG ỔN ĐỊNH: Tỷ lệ đặc trưng biến động Y% nằm trong ngưỡng kiểm soát an toàn (< 30%).`
- **Biểu đồ thanh ngang Plotly Express (`px.bar`):**
  - Trực quan hóa điểm số Population Stability Index (PSI) cho 13 đặc trưng hành vi.
  - Kiểu: Thanh ngang (`orientation="h"`), trục X: `"PSI Score"`, trục Y: `"Đặc trưng"`.
  - Bảng màu: Stable (Xanh lục `#06D6A0`, PSI < 0.1), Moderate (Vàng Cam `#FFB703`, 0.1 <= PSI < 0.25), High (Đỏ Hồng `#EF476F`, PSI >= 0.25).
  - **Đường gióng cảnh báo đỏ nét đứt:** `fig_psi.add_vline(x=0.25, line_dash="dash", line_color="#EF476F", annotation_text="Ngưỡng biến động mạnh (PSI = 0.25)")`.
  - Chiều cao `420px`, theme `"plotly_white"`.
- **Bảng đối soát thống kê Kolmogorov-Smirnov (KS-Test):**
  - Tiêu đề con: `Bảng Đối Soát Thống Kê Kolmogorov-Smirnov (KS-Test)`.
  - Các cột: `Đặc trưng`, `PSI Score`, `P-Value (KS)`, `Mức độ`, `Lệch phân phối` (`"Có"` / `"Không"`).
- **Trạng thái thiếu tệp (Fallback):** Nếu chưa có tệp `drift_metrics.json`, hiển thị banner vàng:  
  `st.warning("Chưa tìm thấy tệp drift_metrics.json. Vui lòng chạy pipeline drift detection.")`.

---

### 4.4 Tab 3: `Thử Nghiệm A/B Testing`

- **Vị trí:** Tab thứ 3 từ trái sang.
- **Nguồn dữ liệu:** Hàm `analyze_ab_test_performance()` từ `src.api.ab_testing`.
- **Bố cục 2 cột phân tích:**
  - **Cột bên trái - Biểu đồ Donut tỷ lệ điều hướng lưu lượng:**
    * Tiêu đề con: `Phân Phối Lưu Lượng Điều Hướng Thực Tế`.
    * Biểu đồ Donut Plotly: `px.pie(donut_df, values="Số mẫu", names="Mô hình", hole=0.5, color_discrete_sequence=["#0A2540", "#00D4B2"])`.
    * Phân bổ thực tế: Champion XGBoost (màu `#0A2540`) chiếm ~96.97% và Challenger Random Forest (màu `#00D4B2`) chiếm ~3.03%. Chiều cao `320px`.
  - **Cột bên phải - Kết quả kiểm định giả thuyết thống kê:**
    * Tiêu đề con: `Kết Quả Kiểm Định Giả Thuyết Thống Kê (Two-Sample T-test)`.
    * Khung thông tin: `st.info`: Phương pháp: `Welch's Two-Sample T-test on Probability Distributions`.
    * Các thông số kiểm định thực nghiệm:
      - `- **T-statistic:** 14.4283`
      - `- **P-value:** 0.0` ($p < 0.05$)
      - `- **Kết luận nghiệp vụ:** Sự khác biệt giữa hai mô hình có ý nghĩa thống kê (p < 0.05).`
- **Bảng đối sánh hiệu năng hai phiên bản:**
  | Phiên bản | Tên mô hình | Tỷ lệ Churn dự đoán | Độ tin cậy trung bình |
  | :--- | :--- | :--- | :--- |
  | **v2.0.0-champion** | XGBoost | **56.30%** | 0.5598 |
  | **v1.0.0-challenger** | Random_Forest | **19.93%** | 0.2214 |
- **Trạng thái chưa đủ mẫu (Fallback):** Nếu mỗi phiên bản chưa tích lũy đủ 5 mẫu suy luận, hiển thị banner:  
  `st.info("Chưa có đủ dữ liệu A/B testing để chạy kiểm định thống kê.")`.
- **Xác nhận thành phần loại trừ:** Tab 3 **KHÔNG** chứa slider chọn kích thước mẫu (sample size slider) hay slider mức ý nghĩa. Mọi dữ liệu được trích xuất hoàn toàn tự động từ SQLite.

---

### 4.5 Tab 4: `Chẩn Đoán Mô Hình & Phân Tích Lỗi`

- **Vị trí:** Tab thứ 4 ngoài cùng bên phải.
- **Hàng 1: Đồ thị học tập & Độ hiệu chuẩn (Side-by-side):**
  * Tiêu đề con: `Đường Cong Học Tập (Learning Curves) & Độ Hiệu Chuẩn (Calibration)`.
  * Cột trái: Hiển thị tệp ảnh `docs/images/learning_curves.png`, chú thích: `"Learning Curves: Hội tụ điểm ROC-AUC trên 5-Fold Stratified CV"`.
  * Cột phải: Hiển thị tệp ảnh `docs/images/calibration_curve.png`, chú thích: `"Calibration Curve: Xác suất dự đoán bám sát xác suất thực tế"`.
- Đường kẻ phân cách ngang: `st.markdown("---")`.
- **Hàng 2: Phân tích lỗi sai FP & FN (Error Analysis):**
  * Tiêu đề con: `Phân Tích Lỗi Sai (Error Analysis: False Positives & False Negatives)`.
  * Cột trái (tỷ lệ 1.2): Hiển thị tệp ảnh `docs/images/error_analysis.png`, chú thích: `"Phân bố xác suất và hành vi nhóm lỗi dự đoán FP và FN"`.
  * Cột phải (tỷ lệ 1.0): Nạp dữ liệu thực nghiệm từ tệp `data/processed/error_analysis_report.json` và xuất Markdown:
    * **Thống kê phân loại trên tập kiểm thử (Test Set - 66,332 mẫu):**
      - **True Negatives (TN):** `28,619` mẫu
      - **True Positives (TP):** `37,627` mẫu
      - **False Positives (FP - Báo động nhầm):** `70` mẫu
      - **False Negatives (FN - Bỏ sót churn):** `16` mẫu
    * **Hiệu năng tổng thể:**
      - **Accuracy:** `0.9987`
      - **F1-Score:** `0.9989`
      - **ROC-AUC:** `0.9989`

---

## 5. HƯỚNG DẪN KIỂM THỬ TRỰC TIẾP QUA FASTAPI SWAGGER REST API (`http://localhost:8000/docs`)

- **Địa chỉ Swagger UI chính xác:** **`http://localhost:8000/docs`**
- **Địa chỉ ReDoc Spec:** **`http://localhost:8000/redoc`**
- **Địa chỉ OpenAPI JSON:** **`http://localhost:8000/openapi.json`**
- **Tiêu đề API:** `ChurnGuard MLOps Serving API`, Version: `2.0.0`.
- **Cơ chế xác thực bảo mật:** Header **`x-api-key: mlops-churn-secret-2026`** (Cấu hình qua biến môi trường `API_KEY`). Khi thiếu hoặc sai key, API trả về `HTTP 401 Unauthorized` kèm JSON: `{"detail": "Thiếu hoặc sai API Key! Vui lòng cung cấp header 'X-API-Key' hợp lệ."}`.

---

### 5.1 Bảng Kiểm Kê Toàn Bộ 18 Endpoints Phân Bổ Theo 9 Nhóm Tags

| Nhóm Tag | Phương Thức | Đường Dẫn (Route) | Màu Badge | Tóm Tắt Chức Năng | Tham Số Yêu Cầu | Mã Phản Hồi |
| :--- | :---: | :--- | :---: | :--- | :--- | :---: |
| **Inference** | `POST` | `/predict` | Xanh Lục | Dự đoán 1 khách hàng & XAI SHAP | Header `x-api-key`, Body `CustomerInput` | 200, 401, 422 |
| **Inference** | `POST` | `/batch_predict` | Xanh Lục | Dự đoán hàng loạt (List JSON $\le 1000$) | Header `x-api-key`, Body `List[CustomerInput]` | 200, 401, 422 |
| **Inference** | `POST` | `/upload_csv_predict`| Xanh Lục | Dự đoán từ tệp CSV tải lên | Header `x-api-key`, Form `file: binary` | 200, 400, 422 |
| **A/B Testing**| `POST` | `/predict/ab_test` | Xanh Lục | Dự đoán định tuyến A/B Testing | Header `x-api-key`, Body `CustomerInput` | 200, 401, 422 |
| **A/B Testing**| `GET` | `/ab_test/analytics`| Xanh Dương| Báo cáo kiểm định A/B t-test | Không | 200 |
| **Feature Store & Serving** | `GET` | `/predict/feast/online/{customer_id}` | Xanh Dương | Dự đoán từ Feast Online ID | Path `customer_id`, Header `x-api-key` | 200, 404, 422 |
| **Feature Store & Serving** | `GET` | `/predict/customer/{customer_id}` | Xanh Dương | Alias dự đoán Feast ID | Path `customer_id`, Header `x-api-key` | 200, 404, 422 |
| **Feature Store & Serving** | `POST` | `/predict/feast/online` | Xanh Lục | Dự đoán Feast qua JSON Body | Query/Body `customer_id`, Header `x-api-key` | 200, 404, 422 |
| **Feature Store** | `GET` | `/features/{customer_id}` | Xanh Dương | Truy vấn đặc trưng Online Feast | Path `customer_id` | 200, 500 |
| **Monitoring** | `GET` | `/docs/drift_report.html` | Xanh Dương | Báo cáo trực quan Drift HTML | Không | 200 |
| **Monitoring** | `GET` | `/drift/status` | Xanh Dương | Trạng thái trôi dạt dữ liệu JSON | Không | 200 |
| **MLOps Automation** | `POST` | `/api/v1/trigger_retrain` | Xanh Lục | Kích hoạt huấn luyện lại tự động | Query `force`, `dry_run`, Header `x-api-key` | 200, 401 |
| **MLOps Automation** | `POST` | `/api/v1/reload_model` | Xanh Lục | Hot-reload nạp lại mô hình trong RAM | Header `x-api-key` | 200, 401 |
| **Analytics** | `GET` | `/models/summary` | Xanh Dương| So sánh chỉ số 4 mô hình máy học| Không | 200, 404 |
| **Analytics** | `GET` | `/models/tuning` | Xanh Dương| Lịch sử 12 trials Optuna TPE | Không | 200, 404 |
| **Observability** | `GET` | `/metrics` | Xanh Dương| Chỉ số Uptime & Tổng số request | Không | 200 |
| **General** | `GET` | `/` | Xanh Dương| Chuyển hướng (`HTTP 307`) sang `/docs` | Không | 307 |
| **General** | `GET` | `/health` | Xanh Dương| Trạng thái sức khỏe toàn hệ thống | Không | 200 |

---

### 5.2 Thao tác chi tiết Endpoint `POST /predict` (Dự đoán khách hàng đơn lẻ & SHAP)

1. **Mở Accordion:** Cuộn đến nhóm **Inference**, nhấp chuột vào thanh màu xanh lục `POST /predict`.
2. **Kích hoạt chỉnh sửa ("Try it out"):**
   - Vị trí nút: Nằm ở **GÓC TRÊN CÙNG BÊN PHẢI** của khối nội dung endpoint.
   - Kiểu dáng: Nút chữ nhật nhỏ, viền mỏng xanh dương `#4990e2`, nền trắng, chữ `Try it out`.
   - Khi nhấp: Nút đổi thành nhãn `Cancel`, đồng thời mở khóa ô nhập Header và Request Body.
3. **Điền Header bảo mật:**
   - Tại ô **`x-api-key (header)`**: Nhập chuỗi: **`mlops-churn-secret-2026`**.
4. **Soạn thảo Request Body JSON (`CustomerInput`):**
   - Khung textarea hiển thị sẵn schema mẫu đầy đủ 11 thuộc tính:
     ```json
     {
       "customer_id": 1,
       "age": 35.0,
       "gender": "Female",
       "tenure": 24.0,
       "usage_frequency": 15.0,
       "support_calls": 3.0,
       "payment_delay": 5.0,
       "subscription_type": "Standard",
       "contract_length": "Monthly",
       "total_spend": 650.0,
       "last_interaction": 12.0
     }
     ```
   - Ràng buộc Pydantic kiểm tra tính hợp lệ (`src/api/schemas.py`):
     * `customer_id`: Số nguyên $\ge 1$.
     * `age`: Số thực từ `18.0` đến `100.0`.
     * `gender`: Chuỗi thuộc `["Female", "Male"]`.
     * `tenure`: Số thực từ `0.0` đến `120.0`.
     * `usage_frequency`: Số thực từ `0.0` đến `50.0`.
     * `support_calls`: Số thực từ `0.0` đến `30.0`.
     * `payment_delay`: Số thực từ `0.0` đến `90.0`.
     * `subscription_type`: Chuỗi thuộc `["Basic", "Standard", "Premium"]`.
     * `contract_length`: Chuỗi thuộc `["Monthly", "Quarterly", "Annual"]`.
     * `total_spend`: Số thực từ `0.0` đến `100000.0`.
     * `last_interaction`: Số thực từ `0.0` đến `60.0`.
     * Tuyệt đối không chấp nhận giá trị `NaN` hoặc `Inf`.
5. **Nút thực thi ("Execute"):**
   - Vị trí nút: Nằm ở **NGAY DƯỚI khung soạn thảo Request Body**.
   - Kiểu dáng: Nút dạng khối ngang (Block button), màu **Xanh Dương Đậm (`#4990e2`)**, chữ in hoa màu trắng `"EXECUTE"`.
   - Khi nhấp: Giao diện gửi request và xuất hiện hiệu ứng xoay chờ (Loading spinner).
6. **Kết quả trả về khi THÀNH CÔNG (`Code 200 OK`):**
   - Màn hình Responses hiển thị mã màu xanh lá: **`Code 200`**.
   - Dòng lệnh `curl` tự động sinh kèm theo.
   - Cấu trúc JSON trả về (`PredictionResponse`):
     ```json
     {
       "customer_id": 1,
       "churn_prediction": 1,
       "churn_probability": 0.9868,
       "risk_level": "High Risk",
       "recommended_action": "RỦI RO CAO (VIP Monthly): Đề xuất chiết khấu 20% chuyển đổi sang hợp đồng Annual...",
       "feature_attributions": {
         "contract_length_encoded": 6.4165,
         "support_calls": -1.0729,
         "usage_frequency": -0.9604,
         "tenure": 0.7511
       },
       "explanation_summary": "Đặc trưng thúc đẩy rời bỏ chính (base_value=+0.272): contract_length_encoded (SHAP: +6.417)...",
       "model_version": "v2.0.0-champion",
       "latency_ms": 4.57
     }
     ```
7. **Xử lý các mã lỗi:**
   - **`Code 401 Unauthorized`:** Do thiếu hoặc sai header `x-api-key`.
   - **`Code 422 Unprocessable Entity`:** Dữ liệu vi phạm ràng buộc Pydantic (ví dụ `age: 10`). Swagger hiển thị rõ vị trí lỗi:
     ```json
     {
       "detail": [
         {
           "type": "greater_than_equal",
           "loc": ["body", "age"],
           "msg": "Input should be greater than or equal to 18",
           "input": 10.0,
           "ctx": {"ge": 18.0}
         }
       ]
     }
     ```

---

### 5.3 Thao tác chi tiết Endpoint `POST /batch_predict` & `POST /upload_csv_predict`

1. **`POST /batch_predict`:**
   - Mở rộng dòng `POST /batch_predict` trong nhóm **Inference**, bấm `Try it out`.
   - Điền header `x-api-key: mlops-churn-secret-2026`.
   - Truyền mảng JSON các đối tượng khách hàng:
     ```json
     [
       {"customer_id": 101, "age": 42.0, "gender": "Male", "tenure": 12.0, "usage_frequency": 20.0, "support_calls": 5.0, "payment_delay": 10.0, "subscription_type": "Standard", "contract_length": "Monthly", "total_spend": 300.0, "last_interaction": 5.0},
       {"customer_id": 102, "age": 28.0, "gender": "Female", "tenure": 36.0, "usage_frequency": 25.0, "support_calls": 1.0, "payment_delay": 0.0, "subscription_type": "Premium", "contract_length": "Annual", "total_spend": 1200.0, "last_interaction": 20.0}
     ]
     ```
   - Giới hạn an toàn: Tối đa 1,000 bản ghi (`MAX_BATCH_SIZE = 1000`). Nếu vượt quá, trả về mã lỗi `422 Unprocessable Entity` kèm thông điệp `Batch size exceeds maximum limit of 1000`.
   - Bấm nút `Execute` màu xanh dương `#4990e2` -> Nhận phản hồi **200 OK** với cấu trúc tổng hợp gồm `total_processed`, `churn_count`, `retention_count`, `overall_churn_rate`, `risk_distribution` và danh sách chi tiết `predictions`.
2. **`POST /upload_csv_predict`:**
   - Mở rộng dòng `POST /upload_csv_predict`, bấm `Try it out`.
   - Điền header `x-api-key: mlops-churn-secret-2026`.
   - Tại trường `file`, bấm nút **`Choose File`** (hoặc `Browse...`) xuất hiện bên dưới.
   - Chọn tệp CSV chuẩn từ máy tính.
   - Bấm nút **`Execute`** màu xanh dương `#4990e2`.
   - Phản hồi **200 OK**: Trả về thống kê tổng hợp và danh sách kết quả dự đoán của từng dòng.
   - Nếu tệp không có đuôi `.csv`, trả về `400 Bad Request` (`"Vui lòng chỉ tải lên tệp định dạng CSV!"`).

---

### 5.4 Thao tác chi tiết Endpoint Tái Huấn Luyện `POST /api/v1/trigger_retrain`

1. **Tìm endpoint:** Cuộn xuống nhóm **MLOps Automation**, mở rộng dòng **`POST /api/v1/trigger_retrain`**.
2. **Thao tác:** Bấm nút **`Try it out`** ở góc trên cùng bên phải.
3. **Các tham số:**
   - `force` (Query parameter, kiểu boolean dropdown, mặc định `false`): Chọn `true` nếu muốn ép buộc huấn luyện lại ngay lập tức bất chấp dữ liệu có trôi dạt hay không.
   - `dry_run` (Query parameter, kiểu boolean dropdown, mặc định `false`): Chọn `true` để chạy thử nghiệm tiến trình mà không ghi đè mô hình đang phục vụ.
   - Điền header `x-api-key: mlops-churn-secret-2026`.
4. **Bấm "Execute":**
   - **Nếu phát hiện Data Drift hoặc bật `force=true`:** Trả về `Code 200 OK` với `status: "TRIGGERED"`:
     ```json
     {
       "status": "TRIGGERED",
       "message": "Đã kích hoạt tái huấn luyện thành công qua MLOps Pipeline.",
       "drift_share": 1.0,
       "triggered_at": "2026-10-30 06:36:55 UTC"
     }
     ```
   - **Nếu tiến trình huấn luyện trước đó đang chạy:** Trả về `status: "ALREADY_RUNNING"` (bị chặn bởi `RETRAIN_LOCK`).
   - **Nếu dữ liệu ổn định và `force=false`:** Trả về `status: "SKIPPED"` (*Phân phối dữ liệu ổn định, không cần tái huấn luyện*).

---

### 5.5 Thao tác chi tiết Endpoint Hot-Reload RAM `POST /api/v1/reload_model`

1. **Tìm endpoint:** Trong nhóm **MLOps Automation**, mở rộng dòng **`POST /api/v1/reload_model`**.
2. **Thao tác:** Bấm nút **`Try it out`**, điền header `x-api-key: mlops-churn-secret-2026`.
3. **Bấm "Execute":**
   - Hệ thống sử dụng khóa tái nhập an toàn luồng `MODEL_LOCK` (`threading.RLock()`) để nạp lại trọng số mô hình mới nhất từ ổ đĩa vào bộ nhớ RAM phục vụ của Uvicorn mà không cần khởi động lại tiến trình server (Zero-Downtime Hot Reload).
   - Phản hồi **200 OK**:
     ```json
     {
       "status": "RELOADED",
       "model_version": "v2.0.0-champion",
       "reloaded_at": "2026-10-30 09:20:00 UTC"
     }
     ```

---

### 5.6 Các Endpoint Giám Sát Nhanh 1-Click (Quick Health & Metrics)

1. **`GET /health` (Nhóm General):**
   - Mở rộng dòng `GET /health` -> Bấm `Try it out` -> Bấm `Execute` (Không cần API Key).
   - Phản hồi **200 OK**: Trả về trạng thái `HEALTHY`, thông tin Feast Feature Store (`SQLite Only - Redis Offline` hoặc `Redis Online`), tên mô hình Champion `XGBoost`, mức RAM tiêu thụ và Uptime hệ thống.
2. **`GET /metrics` (Nhóm Observability):**
   - Mở rộng dòng `GET /metrics` -> Bấm `Try it out` -> Bấm `Execute`.
   - Phản hồi **200 OK**: Trả về các chỉ số đếm số lượt request, thời gian hoạt động phục vụ tích hợp Prometheus.
3. **`GET /ab_test/analytics` (Nhóm A/B Testing):**
   - Mở rộng dòng `GET /ab_test/analytics` -> Bấm `Try it out` -> Bấm `Execute`.
   - Phản hồi **200 OK**: Trả về thống kê phân bổ lưu lượng thực tế và kết quả kiểm định Welch's Two-Sample t-test.

---

## 6. HƯỚNG DẪN ĐĂNG KÝ AZURE FOR STUDENTS ($100 CREDIT MIỄN PHÍ) & TRIỂN KHAI CLOUD 1-CLICK

Quy trình này hướng dẫn chi tiết cách sở hữu tài khoản đám mây Microsoft Azure hoàn toàn miễn phí dành riêng cho sinh viên ($0 chi phí, tuyệt đối không cần thẻ ngân hàng) và đưa toàn bộ hệ thống lên Cloud phục vụ công khai bằng kiến trúc Cloud-Native Serverless.

---

### 6.1 Quy trình Wizard 5 bước đăng ký tài khoản Azure for Students

1. **Bước 1 - Truy cập cổng đăng ký chính thức:**
   - Mở trình duyệt web truy cập: **`https://azure.microsoft.com/en-us/free/students/`**  
     *(hoặc bản tiếng Việt: `https://azure.microsoft.com/vi-vn/free/students/`)*.
   - **Đặc điểm trang web:** Tiêu đề trang `Azure for Students | Microsoft Azure`. Tiêu đề khối Hero: `Azure for Students` với thông điệp: $100 USD credit sử dụng trong 12 tháng, không yêu cầu thẻ tín dụng (`No credit card required`).
   - **Tìm nút bấm kích hoạt (Hero CTA Button):**
     * **Chữ in trên nút:** **`Start free`** (hoặc `Bắt đầu miễn phí`).
     * **Màu sắc & Kiểu dáng:** Nút màu **Xanh Dương Microsoft (`#0078D4`)** hoặc Xanh Lục (`#107C41`), chữ in màu trắng `#FFFFFF`, font Segoe UI semibold, bo góc `border-radius: 4px`.
     * **Vị trí chính:** Nằm ở **CHÍNH GIỮA khối Hero Banner** (căn giữa-trái), ngay bên dưới các dòng mô tả lợi ích.
     * **Vị trí phụ:** Góc trên bên phải thanh Header cố định cạnh nút `Sign in`.
   - Bấm vào nút **`Start free`**.
2. **Bước 2 - Đăng nhập tài khoản Microsoft:**
   - Trang web chuyển hướng sang màn hình `login.microsoftonline.com`.
   - Nhập tài khoản Microsoft cá nhân hoặc Office 365 trường cấp (ví dụ: `23520783@gm.uit.edu.vn` hoặc `mssv@student.uit.edu.vn`).
   - Bấm nút **`Next`** màu xanh dương ở góc dưới bên phải khung đăng nhập, nhập mật khẩu và bấm **`Sign in`**.
3. **Bước 3 - Xác thực danh tính sinh viên (Academic Verification):**
   - Tại mục "Verification method", chọn **`School email address`**.
   - Nhập lại email sinh viên của trường và bấm nút màu xanh **`Send verification email`**.
   - Mở hòm thư sinh viên nhận thư từ Microsoft có chứa mã PIN xác nhận 6 chữ số.
   - Quay lại trang Azure, nhập 6 chữ số vào ô "Verification code" và bấm nút **`Verify code`**.
   - *(Dự phòng: Nếu trường chưa liên kết trực tiếp, hỗ trợ xác thực thông qua GitHub Student Developer Pack).*
4. **Bước 4 - Xác minh thiết bị qua SMS OTP (Tuyệt đối không cần thẻ tín dụng):**
   - Chọn quốc gia `Vietnam (+84)`, điền số điện thoại cá nhân (bỏ số 0 đầu) và bấm **`Send code`**.
   - Nhập mã OTP 6 chữ số nhận được qua tin nhắn SMS và bấm **`Verify code`**.
   - **Minh chứng an toàn tuyệt đối:** Bước này chỉ nhằm chống spam tài khoản, **hoàn toàn KHÔNG xuất hiện bất kỳ form nhập thẻ Visa/Mastercard nào**.
5. **Bước 5 - Chấp thuận điều khoản & Hoàn tất:**
   - Điền thông tin Họ tên, quốc gia Vietnam.
   - Tích chọn ô vuông: *"I agree to the subscription agreement, offer details and privacy statement"*.
   - Tìm nút hoàn tất: Nút **`Sign up`** to màu xanh dương nằm ở **DƯỚI CÙNG BÊN PHẢI form đăng ký**. Bấm vào nút **`Sign up`**.

---

### 6.2 Kiểm tra trạng thái gói thuê bao trong Microsoft Azure Portal

1. Sau khi đăng ký xong, hệ thống tự động chuyển hướng về trang chủ: **`https://portal.azure.com`**.
2. Trên thanh tìm kiếm ở đỉnh trang (`Search resources, services, and docs`), gõ từ khóa: **`Subscriptions`**.
3. Bấm vào dịch vụ **`Subscriptions`** (biểu tượng chiếc chìa khóa màu vàng).
4. **Dấu hiệu THÀNH CÔNG:**
   - `Subscription name`: **`Azure for Students`**
   - `Subscription ID`: Chuỗi GUID 36 ký tự (ví dụ: `1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d`). Nhấp vào biểu tượng hai ô vuông chồng nhau (**Copy to clipboard**) ở ngay bên cạnh để sao chép mã này.
   - `Status`: **`Active`** (Đang hoạt động, huy hiệu màu xanh lục).
   - `Role`: **`AccountAdmin`** hoặc **`Owner`**.
   - `Spending Limit`: **`Enabled`** kèm biểu tượng ổ khóa bảo vệ màu xanh.
   - Hạn mức số dư ban đầu: **`$100.00 USD Credit`** sử dụng trong 12 tháng. Khi cạn số dư, dịch vụ tự động tạm dừng mà không bao giờ phát sinh nợ cá nhân.
5. **Nút Azure Cloud Shell trên Portal:**
   - **Vị trí:** Nằm ở **Góc trên bên phải thanh Header Toolbar của Azure Portal**, ngay bên cạnh biểu tượng Quả chuông thông báo (Notifications) và Bánh răng cài đặt (Settings).
   - **Biểu tượng:** Icon terminal hình **`>_`**.
   - **Tiện ích vượt trội:** Nhấp vào nút `>_` để mở terminal Bash hoặc PowerShell trực tiếp ngay trong trình duyệt web. Môi trường này đã cài sẵn và tự động xác thực Azure CLI (`az`), giúp sinh viên thực thi toàn bộ lệnh triển khai mà **không cần cài đặt bất kỳ phần mềm nào lên máy tính cá nhân**.

---

### 6.3 Đăng nhập và liên kết Azure CLI trên máy trạm Windows

1. **Kiểm tra và đăng nhập:** Mở terminal CMD thực thi:
   ```bash
   cmd /c "az login"
   ```
   *(Trình duyệt tự động mở tab đăng nhập Microsoft, chọn tài khoản sinh viên vừa kích hoạt).*
2. **Thiết lập gói thuê bao mặc định (sử dụng Subscription ID đã sao chép):**
   ```bash
   cmd /c "az account set --subscription \"Azure for Students\""
   ```
3. **Kiểm tra xác nhận ngữ cảnh hoạt động:**
   ```bash
   cmd /c "az account show --output table"
   ```
   *(Bảng kết quả in ra cột Name là `Azure for Students` và IsDefault là `True`).*

---

### 6.4 Thực thi kịch bản triển khai tự động 1-Click `deploy/azure/deploy_azure.bat`

Kịch bản tự động hóa tại `deploy/azure/deploy_azure.bat` (101 dòng) thực hiện toàn bộ quy trình cấp phát hạ tầng đám mây Serverless:

1. **Lệnh thực thi duy nhất trên Windows CMD:**
   ```bash
   cmd /c "deploy\azure\deploy_azure.bat"
   ```
2. **Bảng giải mã các biến cấu hình trong script:**
   | Biến trong Script | Giá Trị Mặc Định | Ý Nghĩa Kỹ Thuật & Dịch Vụ Đám Mây |
   | :--- | :--- | :--- |
   | `RESOURCE_GROUP` | `rg-churnguard-mlops-sea` | Nhóm tài nguyên chứa toàn bộ 6 dịch vụ con tại vùng Đông Nam Á |
   | `LOCATION` | `southeastasia` | Trung tâm dữ liệu Singapore (~26ms - 49ms RTT về Việt Nam) |
   | `ACR_NAME` | `churnguardacr` | Azure Container Registry (SKU Basic, Admin Enabled) |
   | `APP_ENV` | `env-churnguard-mlops` | Môi trường quản lý dùng chung cho Azure Container Apps |
   | `APP_NAME` | `churnguard-serving-app` | Dịch vụ Container App phục vụ suy luận thời gian thực và Web UI |
   | `STORAGE_ACCOUNT` | `stchurnguardsea2026` | Tài khoản Azure Blob Storage lưu trữ Parquet DVC & Model |
   | `BLOB_CONTAINER` | `churnguard-datasets` | Thùng chứa dữ liệu trong Blob Storage |
   | `REDIS_NAME` | `redis-churnguard-sea` | Azure Cache for Redis Basic C0 (SSL 6380) lưu trữ Feast Hot Cache |
   | `IMAGE_TAG` | `v2.0.0` | Thẻ phiên bản Docker image đóng gói |
3. **Tiến trình tự động diễn ra tuần tự trong 8 - 12 phút:**
   - **Bước 1-2:** Kiểm tra Azure CLI và tài khoản đăng nhập.
   - **Bước 3:** Tạo Resource Group `rg-churnguard-mlops-sea` tại Singapore (`southeastasia`).
   - **Bước 4:** Tạo Azure Storage Account `stchurnguardsea2026` và Blob Container `churnguard-datasets`.
   - **Bước 5:** Cấp phát Azure Cache for Redis C0 SSL Port 6380 (`redis-churnguard-sea`).
   - **Bước 6:** Cấp phát Azure Container Registry `churnguardacr` (SKU Basic).
   - **Bước 7:** **Cloud-Native Docker Build (`az acr build`):**
     * Lệnh: `az acr build --registry !ACR_NAME! --image churnguard-mlops:!IMAGE_TAG! --image churnguard-mlops:latest .`
     * **Ưu điểm Cloud-Native vượt trội:** Mã nguồn được nén và đẩy lên Azure Container Registry để đóng gói trực tiếp trên đám mây của Microsoft. **Người dùng HOÀN TOÀN KHÔNG CẦN cài đặt hoặc khởi động Docker Desktop cục bộ!** Điều này giải quyết triệt để sự cố crash Docker Daemon trên Windows.
   - **Bước 8:** Tạo Azure Container Apps Managed Environment `env-churnguard-mlops`.
   - **Bước 9:** Cấp phát Container App `churnguard-serving-app` với cấu hình 1.0 vCPU, 2.0 GiB RAM, mở cổng Ingress 8000 ra Internet, cơ chế tự động co giãn Serverless (`min-replicas: 0, max-replicas: 5`).
4. **Dấu hiệu THÀNH CÔNG:**
   - Màn hình terminal in ra khung thông báo hoàn tất:
     ```text
     ==============================================================================
     [+] CHUC MUNG! HE THONG MLOPS DA DUOC TRIEN KHAI THANH CONG TREN AZURE CLOUD!
     ==============================================================================
       - Public Endpoint URL : https://churnguard-serving-app.<unique_hash>.southeastasia.azurecontainerapps.io
       - Interactive Web UI  : https://churnguard-serving-app.<unique_hash>.southeastasia.azurecontainerapps.io/ui
       - Swagger API Docs    : https://churnguard-serving-app.<unique_hash>.southeastasia.azurecontainerapps.io/docs
       - Health Check        : https://churnguard-serving-app.<unique_hash>.southeastasia.azurecontainerapps.io/health
     ==============================================================================
     ```
   - Mở trình duyệt truy cập `Interactive Web UI` (`https://<FQDN>/ui`) để trải nghiệm giao diện Bento Grid hoạt động 100% trên nền tảng đám mây Microsoft Azure!

---

### 6.5 Đối chiếu kỹ thuật: Azure Container Apps (Hiện hữu) vs Azure App Service (Cổ điển)

Bảng đối chiếu cung cấp cơ sở kỹ thuật hỗ trợ đánh giá kiến trúc khi so sánh giữa phương án hiện đại (Container Apps) và truyền thống (App Service):

| Tiêu Chí Kỹ Thuật | Phương Án Hiện Hữu trong Codebase: **Azure Container Apps (ACA)** | Phương Án Cổ Điển: **Azure App Service (Web App for Containers)** |
| :--- | :--- | :--- |
| **Tệp kịch bản chính** | `deploy/azure/deploy_azure.bat` (101 dòng) | Kịch bản Web App truyền thống |
| **Công cụ yêu cầu** | Chỉ cần `az CLI` (hoặc chạy trên Azure Cloud Shell `>_`) | Cần cả `az CLI` và `docker CLI` (nếu build cục bộ) |
| **Cơ chế đóng gói Image**| **`az acr build` (Cloud-Native Build, không cần Docker Desktop)** | `docker build` + `docker push` (bắt buộc bật Docker Desktop) |
| **Cổng định tuyến Ingress**| Tham số trực tiếp: **`--target-port 8000`** | Thiết lập AppSettings: **`WEBSITES_PORT=8000`** |
| **Cơ chế Co giãn (Scaling)**| **Serverless Scale-to-Zero (`minReplicas: 0, maxReplicas: 5`)** -> Không có truy cập: chi phí compute = $0.00 | Luôn duy trì máy chủ B1 chạy 24/7 (~$13.14/tháng), không thể co về 0 |
| **Định dạng URL công khai** | `https://<APP_NAME>.<hash>.<REGION>.azurecontainerapps.io` | `https://<WEB_APP_NAME>.azurewebsites.net` |
| **Lệnh xem nhật ký** | `az containerapp logs show --name churnguard-serving-app --tail 100` | `az webapp log tail --name churnguard-serving-app` |
| **Đánh giá FinOps ($100 Credit)** | **Tối ưu chi phí ($74.67/tháng tổng thể):** Vận hành an toàn trong hạn mức $100 credit khả dụng, tự ngắt khi nhàn rỗi. | Kém linh hoạt hơn về dung lượng RAM (gói B1 chỉ có 1.75 GB RAM, dễ quá tải khi nạp SHAP TreeExplainer). |

---

### 6.6 Ma trận chẩn đoán sự cố triển khai Cloud thường gặp (Master Cloud Troubleshooting)

Danh mục 6 sự cố triển khai đám mây phổ biến nhất đối với tài khoản Azure for Students và quy trình khắc phục chuẩn hóa:

#### Sự cố 1: Lỗi chưa đăng ký không gian tên tài nguyên (`Namespace Not Registered`)
- **Thông báo lỗi đặc trưng:**
  ```text
  The subscription is not registered to use namespace 'Microsoft.ContainerRegistry'
  hoặc: The subscription is not registered to use namespace 'Microsoft.App'
  ```
- **Nguyên nhân gốc rễ:** Tài khoản Azure for Students mới kích hoạt lần đầu chưa được Microsoft tự động bật các Resource Providers cho Container.
- **Lệnh khắc phục triệt để:**
  ```bash
  cmd /c "az provider register --namespace Microsoft.ContainerRegistry"
  cmd /c "az provider register --namespace Microsoft.App"
  cmd /c "az provider register --namespace Microsoft.OperationalInsights"
  ```
  *Kiểm tra trạng thái đăng ký (đạt `Registered` là thành công):*
  ```bash
  cmd /c "az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv"
  ```

#### Sự cố 2: Lỗi nghẽn hạn mức vCPU tại Singapore (`ResourceProviderQuotaExceeded`)
- **Thông báo lỗi đặc trưng:**
  ```text
  ResourceProviderQuotaExceeded: A quota limit for ContainerAppResources in region southeastasia has been exceeded.
  ```
- **Nguyên nhân gốc rễ:** Vùng Singapore (`southeastasia`) chịu tải cao từ các tài khoản sinh viên miễn phí khu vực Đông Nam Á.
- **Cách khắc phục triệt để:**
  Mở tệp `deploy/azure/deploy_azure.bat`, sửa dòng số 15 chuyển sang trung tâm dữ liệu Hồng Kông hoặc Bờ Đông Hoa Kỳ:
  ```bat
  set LOCATION=eastasia
  REM hoặc: set LOCATION=eastus
  ```
  Sau đó chạy lại kịch bản: `cmd /c "deploy\azure\deploy_azure.bat"`.

#### Sự cố 3: Lỗi Docker Daemon chưa bật trên máy trạm (`Docker Offline`)
- **Thông báo lỗi đặc trưng:**
  ```text
  failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine...
  ```
- **Nguyên nhân gốc rễ:** Người dùng chạy lệnh `docker build` cục bộ khi Docker Desktop chưa bật.
- **Cách khắc phục triệt để:**
  - **Giải pháp tối ưu (Cloud-Native):** Không cần mở Docker Desktop! Kịch bản `deploy_azure.bat` sử dụng lệnh `az acr build` tại dòng 61. ACR Tasks trên đám mây sẽ tự kéo mã nguồn và đóng gói từ `Dockerfile`.
  - **Giải pháp cục bộ:** Nếu muốn chạy Docker trên máy, mở Docker Desktop từ Start Menu và đợi biểu tượng cá voi chuyển sang màu xanh lá cây.

#### Sự cố 4: Lỗi sập Container / Hết thời gian chờ phản hồi (`HTTP 502 Bad Gateway` / `HTTP 504 Timeout`)
- **Thông báo lỗi đặc trưng:** Truy cập URL Container App trên trình duyệt báo `502 Bad Gateway` hoặc `504 Gateway Timeout`.
- **Nguyên nhân gốc rễ:**
  1. Quá trình tải các artifact nặng (`champion_model.joblib`, `TreeExplainer`, `scaler.joblib`) bị quá RAM hoặc thiếu tệp khiến tiến trình Python bị thoát bất thường.
  2. Thời gian khởi động ứng dụng vượt quá ngưỡng `initialDelaySeconds` của Liveness Probe.
- **Lệnh điều tra nhật ký (Debugging Commands):**
  - Xem logs Container App:
    ```bash
    cmd /c "az containerapp logs show --name churnguard-serving-app --resource-group rg-churnguard-mlops-sea --type console --tail 100"
    ```
  - Kiểm tra trạng thái bản sửa đổi (Revision Status):
    ```bash
    cmd /c "az containerapp revision list --name churnguard-serving-app --resource-group rg-churnguard-mlops-sea -o table"
    ```

#### Sự cố 5: Lỗi lệch cổng định tuyến Ingress (`Port Mismatch`)
- **Thông báo lỗi đặc trưng:** Container hiển thị trạng thái `Running` nhưng không thể truy cập từ Internet hoặc báo `Connection Refused`.
- **Nguyên nhân gốc rễ:** Uvicorn trong Dockerfile lắng nghe tại cổng `8000`, nhưng cổng Ingress của Container App bị trỏ nhầm về cổng `80` hoặc `8080`.
- **Lệnh khắc phục triệt để:**
  ```bash
  cmd /c "az containerapp update --name churnguard-serving-app --resource-group rg-churnguard-mlops-sea --target-port 8000"
  ```

#### Sự cố 6: Lỗi trùng tên Azure Storage Account toàn cầu (`StorageAccountAlreadyTaken`)
- **Thông báo lỗi đặc trưng:**
  ```text
  StorageAccountAlreadyTaken: The storage account named stchurnguardsea2026 is already taken.
  ```
- **Nguyên nhân gốc rễ:** Tên Storage Account chia sẻ không gian tên miền toàn cầu của Microsoft (`<name>.blob.core.windows.net`), chỉ cần một người dùng trên thế giới đã đặt tên này thì hệ thống sẽ từ chối.
- **Cách khắc phục triệt để:**
  Mở tệp `deploy/azure/deploy_azure.bat`, sửa dòng số 19 gắn thêm hậu tố định danh duy nhất (unique suffix) hoặc mã cá nhân:
  ```bat
  set STORAGE_ACCOUNT=stchurn23520783sea
  ```
  *(Ràng buộc kỹ thuật: Tên Storage Account chỉ được chứa từ 3 đến 24 ký tự chữ thường và chữ số, tuyệt đối không chứa dấu gạch nối `-` hay chữ hoa).*

---

### 6.7 Lệnh thu hồi tài nguyên sau khi nghiệm thu (FinOps - Bảo toàn ngân sách)

Sau khi hoàn tất quy trình kiểm thử và nghiệm thu hệ thống, để giải phóng tài nguyên và bảo toàn số dư ngân sách $100 credit, thực thi **1 câu lệnh duy nhất**:

```bash
cmd /c "az group delete --name rg-churnguard-mlops-sea --yes --no-wait"
```
- **Hiện tượng:** Lệnh gửi chỉ thị thu hồi bất đồng bộ lên Azure Resource Manager và giải phóng terminal ngay lập tức.
- **Kết quả:** Toàn bộ 6 dịch vụ (Container App, ACR, Redis C0, Storage Account, Log Analytics, VNet) bị xóa sạch hoàn toàn, đưa chi phí phát sinh về mức $0.00 tuyệt đối.

---

## 7. BẢNG TỔNG HỢP MÃ LỖI THƯỜNG GẶP & GIẢI PHÁP KHẮC PHỤC TRIỆT ĐỂ (MASTER TROUBLESHOOTING MATRIX)

| Mã Lỗi / Hiện Tượng | Thông Báo Lỗi Đặc Trưng | Nguyên Nhân Kỹ Thuật Gốc Rễ | Lệnh & Thao Tác Khắc Phục Chuẩn Xác |
| :--- | :--- | :--- | :--- |
| **HTTP 401 Unauthorized** | `{"detail": "Thiếu hoặc sai API Key! Vui lòng cung cấp header 'X-API-Key' hợp lệ."}` | Thiếu header `X-API-Key` hoặc nhập sai chuỗi bí mật khi gọi REST API /docs | Thêm header `x-api-key` với giá trị bí mật mặc định: `mlops-churn-secret-2026` |
| **HTTP 422 Unprocessable** | `{"detail": [{"loc": ["body", "age"], "msg": "Input should be greater than or equal to 18"}]}` | Dữ liệu đầu vào vi phạm quy tắc Pydantic (tuổi < 18 hoặc > 100, số cuộc gọi âm, chuỗi enum sai) | Hiệu chỉnh lại dữ liệu JSON hoặc form theo đúng dải min/max trong Bảng kiểm kê mục 3.2.A |
| **HTTP 400 Bad Request** | `Vui lòng chỉ tải lên tệp định dạng CSV!` hoặc `Tệp CSV thiếu cột bắt buộc` | Tệp tải lên sai định dạng hoặc thiếu 1 trong 10 cột đặc trưng Kaggle Telco | Sử dụng đúng tệp CSV chuẩn trong `data/raw/customer_churn_dataset-testing-master.csv` |
| **HTTP 307 Temporary Redirect** | Tự động chuyển hướng từ `http://localhost:8000/` sang `/docs` | Đường dẫn gốc `/` được thiết kế chuyển hướng về Swagger UI | Nhập đầy đủ hậu tố `/ui` để vào giao diện Bento Grid: `http://localhost:8000/ui` |
| **HTTP 502 / 504 Gateway** | `502 Bad Gateway` hoặc `504 Gateway Timeout` | Container Cloud bị crash do quá tải RAM khi nạp SHAP hoặc Liveness probe timeout | Kiểm tra logs: `cmd /c "az containerapp logs show --name churnguard-serving-app --resource-group rg-churnguard-mlops-sea --tail 100"` |
| **Lỗi Chiếm Cổng 8000** | `[Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)` | Tiến trình Uvicorn cũ hoặc ứng dụng khác đang chiếm dụng cổng 8000 | Tìm PID: `cmd /c "netstat -ano \| findstr :8000"`<br>Diệt PID: `cmd /c "taskkill /F /PID <PID>"` |
| **Lỗi Chiếm Cổng 8501** | `Port 8501 is already in use` | Tiến trình Streamlit cũ đang chạy ngầm | Chạy Streamlit trên cổng phụ: `cmd /c "streamlit run src/web/dashboard.py --server.port 8502"` |
| **Lỗi Thiếu Trọng Số Model** | `FileNotFoundError: champion_model.joblib` | Chưa chạy pipeline huấn luyện mô hình | Sinh mới mô hình: `cmd /c "python src/models/train_pipeline.py"` |
| **Lỗi Thiếu Báo Cáo Drift** | `404 Not Found: docs/drift_report.html` | Chưa biên dịch báo cáo trôi dạt dữ liệu HTML | Sinh báo cáo drift: `cmd /c "python src/monitoring/drift_detector.py"` |
| **Lỗi Khóa Ghi SQLite WAL** | `sqlite3.OperationalError: database is locked` | Nhiều tiến trình cùng ghi vào SQLite khi chưa bật chế độ WAL | Mã nguồn đã tự động kích hoạt `PRAGMA journal_mode=WAL; busy_timeout=5000;` để tự giải tỏa |
| **Lỗi Docker Daemon Offline** | `failed to connect to the docker API at npipe://...` | Docker Desktop cục bộ chưa được bật | Kịch bản `deploy_azure.bat` sử dụng `az acr build` trên Cloud nên **hoàn toàn không cần Docker Desktop** |
| **Lỗi Azure Quota vCPU** | `Quota limit exceeded in region southeastasia` | Hạn ngạch tài khoản sinh viên tại vùng Singapore bị quá tải | Sửa dòng 15 trong `deploy_azure.bat` thành `set LOCATION=eastus` hoặc `eastasia` |
| **Lỗi Trùng Tên Storage** | `StorageAccountAlreadyTaken: ... is already taken` | Tên Azure Storage Account bị trùng lặp trên phạm vi toàn cầu | Sửa dòng 19 trong `deploy_azure.bat` thành `set STORAGE_ACCOUNT=stchurn23520783sea` |
| **Lỗi Chưa Đăng Ký Provider** | `The subscription is not registered to use namespace 'Microsoft.ContainerRegistry'` | Tài khoản Azure for Students mới chưa kích hoạt đủ namespace | Đăng ký namespace: `cmd /c "az provider register --namespace Microsoft.ContainerRegistry"` và `Microsoft.App` |
| **Lỗi Lệch Cổng Ingress Cloud** | Container báo `Running` nhưng không vào được mạng ngoài | Cổng Ingress trỏ nhầm sang cổng 80 thay vì 8000 | Cập nhật cổng: `cmd /c "az containerapp update --name churnguard-serving-app --resource-group rg-churnguard-mlops-sea --target-port 8000"` |
