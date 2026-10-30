# SỔ TAY HƯỚNG DẪN VẬN HÀNH HỆ THỐNG TOÀN DIỆN (MASTER OPERATIONAL RUNBOOK)
## Nền Tảng ChurnGuard-MLOps Level 2 Enterprise Platform

Tài liệu này là cẩm nang vận hành thực nghiệm chuẩn mực cao nhất, cung cấp hướng dẫn chi tiết từng bước (Step-by-Step Operating Guide) để tương tác, kiểm thử và làm chủ toàn bộ các phân hệ của nền tảng ChurnGuard-MLOps.

Mỗi thao tác trong tài liệu đều quy định rõ: **Truy cập đường dẫn nào? Tên trang gì? Thẻ Tab nào? Nhấn nút nào? Nút có màu sắc và hình dáng ra sao? Nút nằm ở vị trí nào? Khi nhấn hiện ra hiện tượng gì? Dấu hiệu nhận biết thành công là gì? Dấu hiệu lỗi thế nào và cách xử lý triệt để ra sao.**

---

## 1. BẢNG TRA CỨU ĐIỂM TRUY CẬP MẠNG & LIÊN KẾT HỆ THỐNG

| Phân Hệ / Giao Diện | Địa Chỉ Truy Cập Mạng (Exact URL) | Giao Thức / Port | Chức Năng Chính & Lưu Ý Điều Hướng |
| :--- | :--- | :--- | :--- |
| **Giao Diện Điều Hành Web Bento Grid** | **`http://localhost:8000/ui`**<br>*(Alias: `http://localhost:8000/web`)* | HTTP / 8000 | **Bàn làm việc điều hành chính:** Form dự đoán thời gian thực cho từng khách hàng, giải thích XAI SHAP, dự đoán hàng loạt CSV, so sánh 4 mô hình và theo dõi drift.<br>⚠️ **Lưu ý cốt lõi:** Đường dẫn gốc `http://localhost:8000/` tự động chuyển hướng (`HTTP 307`) sang `/docs`. Để vào Bento Grid, **bắt buộc truy cập `/ui`**. |
| **Bảng Điều Khiển Giám Sát Streamlit** | **`http://localhost:8501`** | HTTP / 8501 | **Trung tâm giám sát vận hành:** 4 tab chuyên sâu gồm KPI suy luận thời gian thực từ SQLite WAL, cảnh báo Data Drift (PSI/KS-Test), phân tích A/B Testing (Welch t-test) và chẩn đoán lỗi mô hình. |
| **FastAPI Swagger OpenAPI UI** | **`http://localhost:8000/docs`** | HTTP / 8000 | **Kiểm thử REST API tương tác:** Thực thi trực tiếp các endpoint `/predict`, `/batch_predict`, `/upload_csv_predict`, `/api/v1/trigger_retrain`. Yêu cầu header xác thực `x-api-key`. |
| **FastAPI ReDoc Interactive Spec** | **`http://localhost:8000/redoc`** | HTTP / 8000 | **Tài liệu kỹ thuật 3 cột:** Đặc tả chi tiết từng schema Pydantic, tham số header, body JSON và các mã trạng thái phản hồi HTTP. |
| **Tệp Cấu Trúc OpenAPI 3.1.0 JSON** | **`http://localhost:8000/openapi.json`** | HTTP / 8000 | **Định dạng cấu trúc máy đọc:** Phục vụ tích hợp Postman, Swagger Codegen, kịch bản CI/CD và kiểm toán tự động. |
| **Báo Cáo Trực Quan Data Drift HTML** | **`http://localhost:8000/docs/drift_report.html`** | HTTP / 8000 | **Báo cáo chuyên sâu Evidently/Plotly:** Trực quan hóa phân phối xác suất 13 đặc trưng dữ liệu giữa tập Reference (Train) và Current (Inference). |
| **Cổng Đăng Ký Azure for Students** | **`https://azure.microsoft.com/en-us/free/students/`** | HTTPS / 443 | **Cổng cấp phát tài khoản học viện:** Nhận $100 credit miễn phí trong 12 tháng, không yêu cầu thẻ tín dụng, tự động kích hoạt Spending Limit: Enabled. |
| **Cổng Quản Trị Microsoft Azure Portal** | **`https://portal.azure.com`** | HTTPS / 443 | **Bảng điều khiển đám mây:** Quản lý Resource Group, kiểm tra hạn mức gói thuê bao Subscriptions, Container Apps, Redis C0 và ACR. |

---

## 2. KHỞI ĐỘNG CÁC PHÂN HỆ DỊCH VỤ CỤC BỘ (LOCAL STARTUP PROCEDURES)

Trước khi thao tác trên trình duyệt, khởi chạy hai phân hệ máy chủ cục bộ bằng hai cửa sổ dòng lệnh riêng biệt:

### 2.1 Khởi động FastAPI Model Serving & Web Console (Port 8000)
1. **Lệnh thực thi trên Windows CMD:**
   ```bash
   cmd /c "python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
   ```
   *(Dành cho lập trình viên phát triển: thêm cờ `--reload` để tự động làm mới mã nguồn).*
2. **Tiến trình khởi tạo nội tại (Lifespan Startup):**
   - Hệ thống tự động nạp mô hình Champion XGBoost (`champion_model.joblib`), bộ tiền xử lý chuẩn hóa (`scaler.joblib`) và siêu dữ liệu huấn luyện (`metadata.json`).
   - Khởi tạo bộ giải thích giải thuật cây SHAP `TreeExplainer(clf)` với dự phòng `LinearExplainer`.
   - Kết nối cơ sở dữ liệu SQLite tại `data/inference_logs.db`, thiết lập chế độ an toàn luồng `PRAGMA journal_mode=WAL;`.
3. **Dấu hiệu THÀNH CÔNG:**
   - Màn hình terminal xuất hiện các dòng log tiêu chuẩn:
     ```text
     INFO:     Started server process [PID]
     INFO:     Waiting for application startup.
     INFO:     Application startup complete.
     INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
     ```
4. **Dấu hiệu LỖI & Cách xử lý triệt để:**
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
- **Tiêu đề trang (HTML Title Tag):** `ChurnGuard MLOps - Enterprise Customer Retention Platform`

### 3.1 Cấu trúc định danh & Bố cục không gian Bento Grid
1. **Thanh điều hướng cố định đỉnh trang (Fixed Header Navbar):**
   - **Góc trên bên trái:** Logo khiên bảo vệ Deep Teal `#0F766E` với đường xung nhịp ECG màu Cam Hổ Phách `#F59E0B`. Chữ thương hiệu: `<span class="brand-title">CHURN<span>GUARD</span></span>` (chữ "CHURN" màu trắng ngà `#F8FAFC`, chữ "GUARD" màu cam `#F59E0B`, phụ đề `ENTERPRISE MLOPS`).
   - **Góc trên bên phải:**
     * Chấm trạng thái kết nối nhấp nháy `.pulse-dot` màu Xanh Lục Emerald **`#10B981`** (khi kết nối tốt: nhãn `FastAPI: HEALTHY (Online)`; khi mất kết nối: nhãn `FastAPI: Offline (Chưa bật server)`).
     * Huy hiệu mô hình: Nền xanh đen `#0F2942`, chữ Xanh Da Trời `#38BDF8`, nhãn: `Champion: XGBoost`.
2. **Hàng 4 thẻ chỉ số KPI trên cùng (`.kpi-row`):**
   - **Thẻ 1 (Ngoài cùng bên trái):** `MÔ HÌNH CHAMPION` -> Giá trị: `XGBoost`, ROC-AUC: `0.9989`, F1: `0.9785`.
   - **Thẻ 2 (Giữa trái):** `FEAST FEATURE STORE` -> Giá trị: `13 Features`, chế độ: `Online: SQLite | Offline: Parquet`.
   - **Thẻ 3 (Giữa phải):** `ĐỘ TRỄ DỰ ĐOÁN (INFERENCE)` -> Giá trị: `0.45 ms`, SLA: `Tối ưu (< 10ms)`.
   - **Thẻ 4 (Ngoài cùng bên phải):** `TRẠNG THÁI DATA DRIFT` -> Giá trị: `ỔN ĐỊNH` (`#10B981`) hoặc `CẢNH BÁO DRIFT` (`#EF4444`).
3. **Khu vực làm việc 2 cột tỷ lệ 5:7 (`.workspace-grid`):**
   - **Cột bên trái:** Form dự đoán thời gian thực cho từng khách hàng (`#prediction-form`) và Khung kết quả XAI SHAP (`#prediction-result`).
   - **Cột bên phải:** Thẻ phân tích gồm hệ thống 3 Tab (Dự Đoán Hàng Loạt CSV, So Sánh Mô Hình, Giám Sát Drift).

---

### 3.2 Thao tác 1: Dự đoán thời gian thực cho 1 khách hàng đơn lẻ (Single Prediction)
- **Vị trí thao tác:** Thẻ Bento ở **Cột bên trái màn hình**, bên dưới tiêu đề `Dự Đoán Thời Gian Thực` (kèm huy hiệu nhỏ `REST API: /predict`).

#### A. Bảng kiểm kê 11 ô nhập liệu (Input Fields Inventory)
Toàn bộ các ô nhập liệu được sắp xếp thành lưới 6 hàng 2 cột. Người dùng có thể giữ nguyên giá trị mặc định để kiểm thử nhanh hoặc nhập giá trị tùy biến:

| STT | Vị trí ô nhập | ID phần tử | Thẻ HTML | Nhãn hiển thị | Kiểu dữ liệu | Giá trị mặc định | Ràng buộc kiểm thực giao diện | Ràng buộc kiểm thực Backend Pydantic |
| :---: | :--- | :--- | :---: | :--- | :---: | :---: | :--- | :--- |
| **1** | Hàng 1, Cột trái | `inp-customer-id` | `<input>` | Mã khách hàng | Number | `1001` | `min="1"` | `customer_id: Optional[int] >= 1` |
| **2** | Hàng 1, Cột phải | `age` | `<input>` | Độ tuổi | Number | `38` | `min="18" max="100"` | `age: float` từ `18.0` đến `100.0` |
| **3** | Hàng 2, Cột trái | `gender` | `<select>` | Giới tính | Dropdown | `Male` (Nam) | `Male`, `Female` | `Literal["Female", "Male"]` |
| **4** | Hàng 2, Cột phải | `tenure` | `<input>` | Gắn bó (tháng) | Number | `24` | `min="0"` | `tenure: float` từ `0.0` đến `120.0` |
| **5** | Hàng 3, Cột trái | `usage_frequency`| `<input>` | Tần suất dùng | Number | `18` | `min="0"` | `usage_frequency: float` từ `0.0` đến `50.0` |
| **6** | Hàng 3, Cột phải | `support_calls` | `<input>` | Gọi hỗ trợ | Number | `4` | `min="0"` | `support_calls: float` từ `0.0` đến `30.0` |
| **7** | Hàng 4, Cột trái | `payment_delay` | `<input>` | Trễ hạn (ngày) | Number | `8` | `min="0"` | `payment_delay: float` từ `0.0` đến `90.0` |
| **8** | Hàng 4, Cột phải | `subscription_type`| `<select>`| Gói cước | Dropdown | `Standard` | `Basic`, `Standard`, `Premium` | `Literal["Basic", "Standard", "Premium"]` |
| **9** | Hàng 5, Cột trái | `contract_length` | `<select>`| Loại hợp đồng | Dropdown | `Monthly` (Tháng)| `Monthly`, `Quarterly`, `Annual` | `Literal["Monthly", "Quarterly", "Annual"]` |
| **10**| Hàng 5, Cột phải | `total_spend` | `<input>` | Tổng chi tiêu ($)| Number | `450` | `min="0"` | `total_spend: float` từ `0.0` đến `100000.0`|
| **11**| Hàng 6, Cột trái | `last_interaction`| `<input>` | Tương tác cuối | Number | `15` | `min="0"` | `last_interaction: float` từ `0.0` đến `60.0`|

#### B. Quy cách nút bấm dự đoán
- **ID phần tử:** `#btn-submit-single`
- **Chữ in trên nút:** **`Phân Tích Nguy Cơ Rời Bỏ`**
- **Màu sắc & Kiểu dáng:** Nút hình chữ nhật bo góc 8px, nền màu **Cam Hổ Phách (Amber `#F59E0B`)**, chữ in đậm màu **Xanh Đen Midnight Navy (`#0A192F`)**, chiếm 100% chiều ngang hàng nút. Khi rê chuột vào (hover), nút đổi sang màu `#D97706` và trồi lên nhẹ 2px với hiệu ứng bóng mờ amber.
- **Vị trí không gian:** Nằm ở **DƯỚI CÙNG của khối Form bên trái** (dưới hàng `last_interaction`).

#### C. Thao tác và hiện tượng sau khi bấm
1. Bấm chuột trái vào nút **`Phân Tích Nguy Cơ Rời Bỏ`**.
2. **Trạng thái đang tải (Loading state):**
   - Chữ trên nút lập tức đổi thành: **`Đang Phân Tích...`**
   - Nút chuyển sang trạng thái vô hiệu hóa (`disabled = true`), con trỏ chuột hiển thị biểu tượng chờ.
3. Sau khoảng 10 - 50ms, nút tự động chuyển về nhãn ban đầu và khối kết quả `#prediction-result` trượt mở ra ngay bên dưới form.

#### D. Dấu hiệu THÀNH CÔNG (Phân tích kết quả trả về)
Khối kết quả nền màu Navy nổi `#1E3A5F` xuất hiện gồm các thành phần:
- **Huy hiệu rủi ro (`#risk-badge`) ở góc trên bên trái:**
  * **Xác suất $\ge 70\%$:** Nhãn **`RỦI RO CAO (HIGH RISK)`**, màu đỏ tươi **Crimson `#EF4444`**, nền mờ `rgba(239, 68, 68, 0.2)`.
  * **Xác suất $40\% - 69\%$:** Nhãn **`RỦI RO TRUNG BÌNH (MEDIUM RISK)`**, màu vàng cam **Amber `#FBBF24`**, nền mờ `rgba(251, 191, 36, 0.2)`.
  * **Xác suất $< 40\%$:** Nhãn **`AN TOÀN (LOW RISK)`**, màu xanh ngọc **Emerald `#10B981`**, nền mờ `rgba(16, 185, 129, 0.2)`.
- **Huy hiệu độ trễ (`#result-latency`) ở góc trên bên phải:** Hiển thị thời gian nội suy thực tế (ví dụ: `0.42 ms`).
- **Thanh đo xác suất lớn (`#prob-display`):** Hiển thị số phần trăm lớn (ví dụ: **`88.5%`**), thanh đo nằm ngang đổ đầy dải màu đồng bộ với mức độ rủi ro.
- **Khung đề xuất hành động giữ chân (`.action-box`):** Viền trái màu cam `#F59E0B` dày 3px, xuất hiện chiến lược can thiệp $e\text{-Profits}$ chi tiết (ví dụ: *"Nguy cơ cực cao: Chậm thanh toán (8 ngày) và nhiều cuộc gọi hỗ trợ (4 lần). Cần CSKH liên hệ trực tiếp trong 24h..."*).
- **Khung giải thích mô hình XAI SHAP Attributions (`#xai-box`):**
  * Nhãn huy hiệu: `NeurIPS 2017`.
  * Đoạn tóm tắt tự động các đặc trưng dẫn dắt chính.
  * **Thanh đo nhân tố làm tăng nguy cơ rời bỏ:** Dải màu gradient từ Cam sang Đỏ (`linear-gradient(90deg, #F59E0B, #EF4444)`), chỉ số mang dấu **`+`** (ví dụ: `+28.4%` màu `#F59E0B`).
  * **Thanh đo nhân tố giúp giữ chân khách hàng:** Dải màu gradient từ Xanh Da Trời sang Xanh Lục (`linear-gradient(90deg, #0EA5E9, #10B981)`), chỉ số mang dấu **`-`** (ví dụ: `-14.1%` màu `#10B981`).

#### E. Dấu hiệu LỖI & Cách xử lý triệt để
- **Lỗi 1: Hộp thoại trình duyệt hiện thông báo `Không thể kết nối đến FastAPI Serving Endpoint!`:**
  * *Nguyên nhân:* Server FastAPI chưa chạy hoặc tiến trình Uvicorn bị tắt.
  * *Khắc phục:* Mở terminal chạy lệnh tại mục 2.1: `cmd /c "python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"`.
- **Lỗi 2: Trả về mã lỗi `422 Unprocessable Entity` trong Console:**
  * *Nguyên nhân:* Nhập giá trị vi phạm ràng buộc (ví dụ: tuổi < 18 hoặc > 100, số cuộc gọi hỗ trợ âm hoặc > 30).
  * *Khắc phục:* Nhập lại các số liệu nằm đúng khoảng min/max ghi trong bảng kiểm kê tại mục 3.2.A.

---

### 3.3 Thao tác 2: Dự đoán hàng loạt bằng 5 khách hàng mẫu (Sample Batch)
- **Vị trí thao tác:** Thẻ Bento ở **Cột bên phải màn hình**, tại Tab 1: **`Dự Đoán Hàng Loạt (CSV)`** (được chọn sẵn mặc định).
- **Quy cách nút bấm:**
  - **ID phần tử:** `#btn-sample-batch`
  - **Chữ in trên nút:** **`Tải 5 Khách Hàng Mẫu`**
  - **Màu sắc & Kiểu dáng:** Nút viền mỏng trong suốt (Outline Button), viền và chữ mang màu **Xanh Da Trời (Sky Blue `#38BDF8`)**, nền trong suốt, khi hover phủ lớp mờ `rgba(56, 189, 248, 0.1)`.
  - **Vị trí không gian:** Nằm ở **BÊN PHẢI trong cụm nút hành động bên dưới khung kéo thả file** (cạnh nút "Chọn Tệp CSV").
- **Thao tác thực hiện:**
  1. Bấm chuột trái vào nút **`Tải 5 Khách Hàng Mẫu`**.
  2. Giao diện gửi ngay mảng dữ liệu 5 khách hàng (#101 đến #105) tới `POST /batch_predict`.
- **Dấu hiệu THÀNH CÔNG:**
  - Xuất hiện 4 viên thuốc thống kê tổng quan (Stat Pills) nằm ngang:
    * Viên 1: `Tổng số: 5`
    * Viên 2: `Rời bỏ: X` (chữ số màu Đỏ `#EF4444`)
    * Viên 3: `Ở lại: Y` (chữ số màu Xanh Lục `#10B981`)
    * Viên 4: `Tỷ lệ: Z%` (chữ số màu Vàng `#F59E0B`)
  - Bảng dữ liệu chi tiết hiện ra gồm 5 dòng: Cột Mã Khách Hàng, Xác Suất Churn, Mức Độ Rủi Ro có huy hiệu màu, và Chiến Lược Giữ Chân.
  - Dưới cùng của bảng xuất hiện nút **`Xuất Báo Cáo CSV Gắn Nhãn`** (`#btn-download-batch-csv`) màu **Cam Hổ Phách (`#F59E0B`)** với chữ `#0A192F`. Bấm nút này sẽ tải ngay tệp CSV `churn_predictions_annotated_<timestamp>.csv` về máy.

---

### 3.4 Thao tác 3: Tải tệp CSV tùy chỉnh từ máy tính để phân tích lô (CSV Upload)
- **Vị trí thao tác:** Vẫn tại Tab 1 **`Dự Đoán Hàng Loạt (CSV)`** ở cột bên phải.
- **Quy cách nút bấm:**
  - **ID phần tử:** `#btn-browse-file`
  - **Chữ in trên nút:** **`Chọn Tệp CSV`**
  - **Màu sắc & Kiểu dáng:** Nút màu **Xanh Rêu Đậm (Deep Teal `#0F766E`)**, chữ in màu trắng `#FFFFFF`, bo góc 8px.
  - **Vị trí không gian:** Nằm ở **BÊN TRÁI trong cụm nút hành động bên dưới biểu tượng đám mây tải lên**.
- **Thao tác thực hiện:**
  1. Bấm chuột trái vào nút **`Chọn Tệp CSV`** (hoặc kéo thả tệp trực tiếp vào khung nét đứt `#drop-zone`).
  2. Hộp thoại Windows Explorer mở ra. Điều hướng tới tệp dữ liệu kiểm thử có sẵn:
     `c:\Users\Nguyen Trong Khoi\Downloads\CLOUD\data\raw\customer_churn_dataset-testing-master.csv`
  3. Bấm **Open** để xác nhận tải tệp.
- **Dấu hiệu THÀNH CÔNG:**
  - Sau khoảng 1 - 2 giây xử lý lô, bảng thống kê tự động tính toán tổng số bản ghi, tỷ lệ rời bỏ và hiển thị 10 dòng đầu tiên được gắn nhãn dự đoán chuẩn xác.
  - Bấm nút **`Xuất Báo Cáo CSV Gắn Nhãn`** để tải toàn bộ tệp kết quả.
- **Dấu hiệu LỖI & Cách xử lý:**
  - **Lỗi `Vui lòng chỉ tải lên tệp định dạng CSV!` (Mã 400):** Tải nhầm tệp `.xlsx` hoặc `.txt`. Chọn đúng tệp có đuôi mở rộng `.csv`.
  - **Lỗi `Tệp CSV thiếu cột bắt buộc: <tên_cột>` (Mã 400):** Tệp CSV tải lên thiếu 1 trong 10 cột dữ liệu Kaggle Telco. Sử dụng tệp mẫu chuẩn trong thư mục `data/raw/`.
  - **Lỗi `Dòng X: Cột Y chứa giá trị trống (NaN)` (Mã 422):** Dữ liệu có ô trống chưa được điền.
  - **Lỗi `Batch size exceeds maximum limit of 1000` (Mã 422):** Tệp vượt quá giới hạn an toàn 1,000 dòng. Cần trích xuất tập mẫu con $\le 1000$ dòng để tải lên giao diện web.

---

### 3.5 Thao tác 4: Đối chuẩn 4 mô hình & Đồ thị hội tụ Optuna (Model Comparison)
- **Vị trí thao tác:** Nhìn lên thanh chuyển Tab ở trên cùng của Thẻ Bento Cột bên phải.
- **Nút Tab cần chọn:**
  - **Tên Tab:** **`So Sánh Mô Hình`**
  - **Vị trí:** Nằm ở **CHÍNH GIỮA thanh chuyển Tab** (giữa tab "Dự Đoán Hàng Loạt" và tab "Giám Sát Drift").
- **Thao tác:** Bấm chuột trái vào tab **`So Sánh Mô Hình`**.
- **Dấu hiệu THÀNH CÔNG:**
  - **Bảng đối chuẩn phía trên:** Hiển thị 4 mô hình máy học:
    1. `XGBoost (Champion)` (có huy hiệu chữ Champion màu cam nổi bật).
    2. `LightGBM`
    3. `Random Forest`
    4. `Logistic Regression`
    Kèm các cột chỉ số đo lường trên tập kiểm thử: Accuracy, Precision, Recall, F1-Score, và ROC-AUC (XGBoost đạt **`0.9989`** màu xanh ngọc vượt trội).
  - **Biểu đồ cột bên trái:** Đồ thị tương tác Chart.js so sánh trực quan các chỉ số giữa 4 giải thuật.
  - **Biểu đồ đường bên phải:** Đồ thị hội tụ siêu tham số Optuna Bayesian TPE qua 12 trials, thể hiện ROC-AUC tăng dần đến điểm cực trị `0.9990`.
- **Dấu hiệu LỖI:** Nếu đồ thị hiện lớp phủ màu xám `"⚠️ Mất Kết Nối Backend API"`, kiểm tra lại dịch vụ FastAPI tại port 8000.

---

### 3.6 Thao tác 5: Giám sát trôi dạt dữ liệu & Báo cáo HTML chuyên sâu (Drift Monitoring)
- **Vị trí thao tác:** Nhìn lên thanh chuyển Tab ở Thẻ Bento Cột bên phải.
- **Nút Tab cần chọn:**
  - **Tên Tab:** **`Giám Sát Drift`**
  - **Vị trí:** Nằm ở **GÓC NGOÀI CÙNG BÊN PHẢI của thanh chuyển Tab**.
- **Thao tác:** Bấm chuột trái vào tab **`Giám Sát Drift`**.
- **Dấu hiệu THÀNH CÔNG:**
  - Hiển thị bảng đối soát thống kê 13 đặc trưng dữ liệu với các cột: Tên Đặc Trưng, Điểm KS-Statistic, P-Value Kolmogorov-Smirnov, Điểm PSI, và Huy hiệu trạng thái (`Stable` màu xanh lục, `Moderate` màu vàng, `High` màu đỏ).
  - Tìm nút mở báo cáo chi tiết:
    * **Tên nút:** **`Mở Báo Cáo HTML Chi Tiết`**
    * **Kiểu dáng:** Nút viền ngoài thanh mảnh, chữ màu trắng, bo góc 6px.
    * **Vị trí chính xác:** Nằm ở **GÓC TRÊN BÊN PHẢI của khung tiêu đề Giám Sát Drift**.
  - Bấm vào nút này -> Trình duyệt tự động mở tab mới truy cập đường dẫn:  
    👉 **`http://localhost:8000/docs/drift_report.html`** hiển thị toàn bộ biểu đồ phân phối xác suất tương tác.
- **Dấu hiệu LỖI:** Nếu trình duyệt báo `404 Not Found`, tệp HTML chưa được sinh. Chạy lệnh: `cmd /c "python src/monitoring/drift_detector.py"`.

---

## 4. HƯỚNG DẪN CHI TIẾT BẢNG ĐIỀU KHIỂN GIÁM SÁT STREAMLIT (`http://localhost:8501`)

- **Địa chỉ truy cập chính xác:** **`http://localhost:8501`**
- **Tiêu đề tab trình duyệt:** `ChurnGuard MLOps Enterprise Dashboard`
- **Tiêu đề H1 trung tâm:** `[MONITOR] ChurnGuard Enterprise MLOps Monitoring Dashboard`

### 4.1 Nhận diện trang & Thanh điều khiển Sidebar
1. **Thanh bên trái (Sidebar):**
   - Tiêu đề: `ChurnGuard MLOps`
   - Phụ đề: `Enterprise Observability & Model Serving Platform`
   - Thông số metadata hệ thống:
     * `Pipeline: DVC + MLflow 3.16`
     * `Feature Store: Feast 0.66`
     * `Champion Model: XGBoost (AUC: 0.9990)`
     * `A/B Split: 80% Champ / 20% Chall`
   - **Nút bấm làm mới dữ liệu:**
     * **Tên nút:** **`Làm mới ngay (Refresh)`**
     * **Vị trí:** Nằm trên thanh bên trái (Sidebar), ngay bên dưới đường kẻ phân cách metadata thứ 2.
     * **Hành vi khi bấm:** Kích hoạt `st.rerun()`, nạp lại tức thì toàn bộ dữ liệu mới nhất từ SQLite `inference_logs.db` mà không cần tải lại toàn bộ trang web.
2. **Hệ thống 4 Tab ngang:**
   Dashboard được phân bổ thành đúng 4 Tab chức năng với các tiền tố chuẩn mực:

---

### 4.2 Tab 1: `[KPI] Giám Sát Suy Luận & KPI`
- **Vị trí:** Tab đầu tiên bên trái trên thanh tab ngang.
- **Nội dung hiển thị:**
  1. **4 khối thẻ KPI Bento:**
     - `TỔNG LƯỢT SUY LUẬN`: Số nguyên có dấu phẩy (ví dụ: `7,611`), chú thích: *Lưu trữ trong SQLite Database*.
     - `TỶ LỆ DỰ ĐOÁN RỜI BỎ`: Số phần trăm (ví dụ: `55.4%`), chú thích: *4,213 / 7,611 khách hàng*.
     - `ĐIỀU HƯỚNG CHAMPION`: Số phần trăm (ví dụ: `96.7%`), chú thích: *Mục tiêu: 80% (XGBoost)*.
     - `TRẠNG THÁI PHỤC VỤ`: Nhãn **`[ONLINE] HOẠT ĐỘNG`** màu xanh lục Emerald `#06D6A0`.
  2. **Bảng nhật ký suy luận thời gian thực (`[LOG] Nhật Ký Suy Luận Thời Gian Thực Gần Nhất`):**
     - Bảng tương tác chiều cao 320px trích xuất từ SQLite WAL (`data/inference_logs.db`).
     - Cột nhãn dự đoán được tô màu trực quan: **`[WARNING] Rời bỏ (1)`** (màu đỏ) hoặc **`[OK] Giữ chân (0)`** (màu xanh).
     - Cho phép nhấp vào tiêu đề cột để sắp xếp, tìm kiếm hoặc kéo giãn kích thước cột.

---

### 4.3 Tab 2: `[DRIFT] Giám Sát Data Drift & Cảnh Báo`
- **Vị trí:** Tab thứ 2 từ trái sang.
- **Nội dung hiển thị:**
  1. **Khung cảnh báo trôi dạt tự động:**
     - Nếu tỷ lệ đặc trưng lệch phân phối `drift_share >= 30%`: Hiện banner màu đỏ (`st.error`):  
       `[ALERT] CẢNH BÁO DATA DRIFT: Phát hiện X/13 đặc trưng bị lệch phân phối (Tỷ lệ >= ngưỡng 30%). Khuyến nghị kích hoạt Webhook tái huấn luyện tự động!`
     - Nếu `drift_share < 30%`: Hiện banner màu xanh lá (`st.success`):  
       `[OK] HỆ THỐNG ỔN ĐỊNH: Tỷ lệ đặc trưng biến động nằm trong ngưỡng kiểm soát an toàn (< 30%).`
  2. **Biểu đồ thanh nằm ngang Plotly (PSI Scores):**
     - Đo lường chỉ số Population Stability Index (PSI) cho 13 đặc trưng hành vi.
     - Phân loại màu: Xanh lục `#06D6A0` (Ổn định, PSI < 0.1), Vàng `#FFB703` (Vừa phải, 0.1 <= PSI < 0.25), Đỏ `#EF476F` (Biến động mạnh, PSI >= 0.25).
     - **Vạch kẻ đỏ nét đứt** tại hoành độ `x = 0.25` với chú thích `"Ngưỡng biến động mạnh (PSI = 0.25)"`.
  3. **Bảng đối soát thống kê Kolmogorov-Smirnov (KS-Test):**
     - Kiểm định 2 mẫu với hiệu chỉnh Bonferroni ($\alpha = 0.003846$), hiển thị rõ cột `Lệch phân phối` (`Có` hoặc `Không`).

---

### 4.4 Tab 3: `[A/B] Thử Nghiệm A/B Testing`
- **Vị trí:** Tab thứ 3 từ trái sang.
- **Nội dung hiển thị:**
  1. **Cột bên trái - Biểu đồ Donut tỷ lệ điều hướng lưu lượng:**
     - Đồ thị Donut Chart Plotly phân bổ lưu lượng thực tế giữa 2 phiên bản mô hình:
       * **Champion (XGBoost):** Màu Xanh Biển Sâu Oceanic Navy `#0A2540`.
       * **Challenger (Random Forest):** Màu Xanh Bạc Hà Mint Teal `#00D4B2`.
  2. **Cột bên phải - Kết quả kiểm định giả thuyết thống kê:**
     - Phương pháp: **`Welch's Two-Sample T-test on Probability Distributions`** (chấp nhận phương sai hai nhóm không đồng nhất).
     - Số liệu thực chứng:
       * $T\text{-statistic}$: **`12.5006`**
       * $P\text{-value}$: **`0.0`** ($p < 0.05$)
       * Kết luận nghiệp vụ: *"Sự khác biệt về phân phối xác suất dự đoán giữa hai mô hình có ý nghĩa thống kê ở mức $\alpha = 0.05$."*
  3. **Bảng so sánh hiệu năng hai phiên bản:**
     - Mô hình Champion `v2.0.0-champion` (XGBoost): Tỷ lệ churn dự đoán `56.52%`, Độ tin cậy trung bình `0.5620`.
     - Mô hình Challenger `v1.0.0-challenger` (Random Forest): Tỷ lệ churn dự đoán `22.05%`, Độ tin cậy trung bình `0.2417`.

---

### 4.5 Tab 4: `[DIAG] Chẩn Đoán Mô Hình & Lỗi Dự Đoán`
- **Vị trí:** Tab thứ 4 ngoài cùng bên phải.
- **Nội dung hiển thị:**
  1. **Hàng trên - Đồ thị học tập & Độ hiệu chuẩn:**
     - Ảnh 1 (Trái): `Learning Curves` (Đường cong học tập hội tụ điểm ROC-AUC trên 5-Fold Cross Validation).
     - Ảnh 2 (Phải): `Calibration Curve` (Đường cong hiệu chuẩn thể hiện xác suất dự đoán bám sát xác suất thực nghiệm).
  2. **Hàng dưới - Phân tích lỗi sai (Error Analysis):**
     - Biểu đồ phân tích hành vi của 2 nhóm dự đoán sai: **False Positives (Báo động nhầm)** và **False Negatives (Bỏ sót churn)**.
     - **Bảng ma trận nhầm lẫn & Điểm số trên tập kiểm thử:**
       * True Negatives (TN): **`28,619`** mẫu
       * True Positives (TP): **`37,627`** mẫu
       * False Positives (FP): **`70`** mẫu
       * False Negatives (FN): **`16`** mẫu
       * Accuracy: **`0.9987`** | F1-Score: **`0.9989`** | ROC-AUC: **`0.9989`**

---

## 5. HƯỚNG DẪN KIỂM THỬ TRỰC TIẾP QUA FASTAPI SWAGGER REST API (`http://localhost:8000/docs`)

- **Địa chỉ truy cập chính xác:** **`http://localhost:8000/docs`**
- **Tiêu đề trang:** `ChurnGuard MLOps Serving API` (kèm phiên bản `2.0.0` và liên kết `[openapi.json]`).
- **Khóa bảo mật bắt buộc:** Header **`x-api-key: mlops-churn-secret-2026`**.

### 5.1 Giao diện Swagger UI chuẩn
- Phương thức `POST` có huy hiệu màu xanh lá cây `#49cc90`.
- Phương thức `GET` có huy hiệu màu xanh dương `#61affe`.
- Toàn bộ 9 nhóm endpoint được tổ chức khoa học: `Inference`, `A/B Testing`, `Feature Store & Serving`, `Feature Store`, `Monitoring`, `MLOps Automation`, `Analytics`, `Observability`, `General`.

---

### 5.2 Endpoint 1: `POST /predict` (Dự đoán khách hàng đơn lẻ & SHAP Attributions)
1. **Tìm endpoint:** Cuộn đến nhóm **Inference**, bấm vào dòng thanh màu xanh lá **`POST /predict`**.
2. **Kích hoạt chỉnh sửa:**
   - Tìm nút: **`Try it out`**
   - Kiểu dáng: Nút nhỏ hình chữ nhật, nền trắng, chữ màu xanh dương nhạt `#4990e2`.
   - Vị trí: Nằm ở **GÓC TRÊN CÙNG BÊN PHẢI của khối endpoint**.
   - Bấm vào nút `Try it out` (nút chuyển sang nhãn `Cancel`).
3. **Nhập khóa bảo mật (Header Parameter):**
   - Tại dòng **`x-api-key`**: Nhập chuỗi ký tự: **`mlops-churn-secret-2026`** (Bắt buộc).
4. **Kiểm tra/Chỉnh sửa Request Body JSON (`CustomerInput`):**
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
5. **Thực thi gọi API:**
   - Tìm nút: **`Execute`**
   - Kiểu dáng: Nút khối lớn màu xanh dương đậm (**`#4990e2`**), chữ in hoa màu trắng nổi bật, chiếm toàn bộ chiều ngang khối.
   - Vị trí: Nằm ở **NGAY DƯỚI khung soạn thảo Request body**.
   - Bấm chuột trái vào nút **`Execute`**.
6. **Dấu hiệu THÀNH CÔNG (Mã phản hồi HTTP 200 OK):**
   - Màn hình phản hồi hiển thị mã màu xanh lá: **`Code 200`**.
   - Cấu trúc JSON trả về đầy đủ các trường:
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
7. **Dấu hiệu LỖI & Cách xử lý:**
   - **Mã `401 Unauthorized`:**
     * *Thông báo:* `{"detail": "Thiếu hoặc sai API Key! Vui lòng cung cấp header 'X-API-Key' hợp lệ."}`
     * *Khắc phục:* Điền đúng chuỗi `mlops-churn-secret-2026` vào ô `x-api-key`.
   - **Mã `422 Unprocessable Entity`:**
     * *Thông báo:* `Input should be greater than or equal to 18` (khi nhập `age = 10`), hoặc lỗi enum khi nhập sai chữ `gender`.
     * *Khắc phục:* Nhập số tuổi $\ge 18$ và chọn đúng giá trị chuỗi cho phép.

---

### 5.3 Endpoint 2: `POST /upload_csv_predict` & `POST /batch_predict` (Dự đoán lô)
1. **Tải tệp CSV qua `POST /upload_csv_predict`:**
   - Mở rộng dòng **`POST /upload_csv_predict`** trong nhóm **Inference**.
   - Bấm nút **`Try it out`** ở góc trên bên phải.
   - Điền header `x-api-key: mlops-churn-secret-2026`.
   - Tại trường `file`, bấm nút **`Choose File`** (hoặc `Browse...`) xuất hiện bên dưới.
   - Chọn tệp CSV chứa dữ liệu khách hàng.
   - Bấm nút **`Execute`** màu xanh dương `#4990e2`.
   - Phản hồi **200 OK**: Trả về thống kê tổng hợp (`total_processed`, `churn_count`, `risk_distribution`) và danh sách kết quả dự đoán của từng dòng.
2. **Gửi mảng JSON qua `POST /batch_predict`:**
   - Gửi trực tiếp mảng JSON danh sách khách hàng `[{"customer_id": 1, ...}, {"customer_id": 2, ...}]` ($\le 1000$ phần tử) để nhận kết quả phân loại đồng loạt.

---

### 5.4 Endpoint 3: `POST /api/v1/trigger_retrain` (Kích hoạt Continuous Training)
1. **Tìm endpoint:** Cuộn xuống nhóm **MLOps Automation**, mở rộng dòng **`POST /api/v1/trigger_retrain`**.
2. **Thao tác:** Bấm nút **`Try it out`**.
3. **Các tham số:**
   - `force` (boolean dropdown): Chọn `true` nếu muốn ép buộc huấn luyện lại ngay lập tức bất chấp dữ liệu có bị trôi dạt hay không (mặc định: `false`).
   - `dry_run` (boolean dropdown): Chọn `true` để chạy thử nghiệm tiến trình mà không ghi đè mô hình đang phục vụ (mặc định: `false`).
   - Điền header `x-api-key: mlops-churn-secret-2026`.
4. **Bấm "Execute":**
   - **Nếu phát hiện Data Drift hoặc bật `force=true`:** Trả về `Code 200` với `status: "TRIGGERED"`:
     ```json
     {
       "status": "TRIGGERED",
       "message": "Đã kích hoạt tái huấn luyện thành công qua MLOps Pipeline.",
       "drift_share": 1.0,
       "triggered_at": "2026-10-30 06:36:55 UTC"
     }
     ```
   - **Nếu tiến trình huấn luyện trước đó đang chạy:** Trả về `status: "ALREADY_RUNNING"`.
   - **Nếu dữ liệu ổn định và `force=false`:** Trả về `status: "SKIPPED"` (*Phân phối dữ liệu ổn định, không cần tái huấn luyện*).

---

### 5.5 Các tài liệu đặc tả API thay thế
- **ReDoc Interactive Documentation:** `http://localhost:8000/redoc` (giao diện 3 cột trang nhã).
- **OpenAPI JSON Spec:** `http://localhost:8000/openapi.json`.
- **Evidently AI HTML Drift Report:** `http://localhost:8000/docs/drift_report.html`.

---

## 6. HƯỚNG DẪN ĐĂNG KÝ AZURE FOR STUDENTS ($100 CREDIT MIỄN PHÍ) & TRIỂN KHAI CLOUD 1-CLICK

Quy trình này hướng dẫn chi tiết cách sở hữu tài khoản đám mây Microsoft Azure hoàn toàn miễn phí dành riêng cho sinh viên ($0 chi phí, tuyệt đối không cần thẻ ngân hàng) và đưa toàn bộ hệ thống lên Cloud phục vụ công khai.

---

### 6.1 Quy trình Wizard 5 bước đăng ký tài khoản Azure for Students
1. **Bước 1 - Truy cập cổng đăng ký chính thức:**
   - Mở trình duyệt web truy cập: 👉 **`https://azure.microsoft.com/en-us/free/students/`**
   - **Tìm nút đăng ký:**
     * Chữ trên nút: **`Start free`** (hoặc `Bắt đầu miễn phí`).
     * Màu sắc: Nút màu **Xanh Lục / Xanh Dương (`#0078D4` / `#107C41`)**, chữ in màu trắng.
     * Vị trí: Nằm ở **CHÍNH GIỮA banner tiêu đề (Hero section)** hoặc góc trên bên phải thanh điều hướng.
   - Bấm vào nút **`Start free`**.
2. **Bước 2 - Đăng nhập tài khoản Microsoft:**
   - Trang web chuyển hướng sang màn hình `login.microsoftonline.com`.
   - Nhập địa chỉ email trường cấp (ví dụ: `mssv@gm.uit.edu.vn` hoặc `mssv@uit.edu.vn`).
   - Bấm nút **`Next`** màu xanh dương ở góc dưới bên phải khung đăng nhập, nhập mật khẩu và bấm **`Sign in`**.
3. **Bước 3 - Xác thực danh tính sinh viên (Academic Verification):**
   - Tại mục "Verification method", chọn **`School email address`**.
   - Nhập lại email sinh viên của trường và bấm nút màu xanh **`Send verification email`**.
   - Mở hòm thư sinh viên nhận thư từ Microsoft có chứa mã PIN 6 chữ số.
   - Quay lại trang Azure, nhập 6 chữ số vào ô "Verification code" và bấm nút **`Verify code`**.
   - *(Dự phòng: Nếu trường chưa liên kết trực tiếp, chọn xác thực thông qua GitHub Student Developer Pack).*
4. **Bước 4 - Xác minh thiết bị qua SMS OTP (Tuyệt đối không cần thẻ tín dụng):**
   - Chọn quốc gia `Vietnam (+84)`, điền số điện thoại cá nhân và bấm **`Send code`**.
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
3. Bấm vào dịch vụ **`Subscriptions`** (biểu tượng chìa khóa màu vàng).
4. **Dấu hiệu THÀNH CÔNG:**
   - `Subscription name`: **`Azure for Students`**
   - `Status`: **`Active`** (Đang hoạt động)
   - `Role`: **`AccountAdmin`** hoặc **`Owner`**
   - `Spending Limit`: **`Enabled`** kèm biểu tượng khóa bảo vệ.
   - Hạn mức số dư ban đầu: **`$100.00 USD Credit`** sử dụng trong 12 tháng. Khi cạn số dư, dịch vụ tự động tạm dừng mà không bao giờ phát sinh nợ cá nhân.

---

### 6.3 Đăng nhập và liên kết Azure CLI trên máy trạm Windows
1. **Kiểm tra và đăng nhập:** Mở terminal thực thi:
   ```bash
   cmd /c "az login"
   ```
   *(Trình duyệt tự động mở tab đăng nhập Microsoft, chọn tài khoản sinh viên vừa kích hoạt).*
2. **Thiết lập gói thuê bao mặc định:**
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
Kịch bản tự động hóa tại `deploy/azure/deploy_azure.bat` (101 dòng) thực hiện toàn bộ 9 bước cấp phát hạ tầng đám mây:

1. **Lệnh thực thi duy nhất trên Windows CMD:**
   ```bash
   cmd /c "deploy\azure\deploy_azure.bat"
   ```
2. **Tiến trình tự động diễn ra tuần tự trong 8 - 12 phút:**
   - **Bước 1-2:** Kiểm tra Azure CLI và tài khoản đăng nhập.
   - **Bước 3:** Tạo Resource Group `rg-churnguard-mlops-sea` tại khu vực Đông Nam Á (`southeastasia` - Singapore, RTT ~26ms về Việt Nam).
   - **Bước 4:** Tạo Azure Storage Account `stchurnguardsea2026` và Blob Container `churnguard-datasets`.
   - **Bước 5:** Cấp phát Azure Cache for Redis C0 SSL Port 6380 (`redis-churnguard-sea`).
   - **Bước 6:** Cấp phát Azure Container Registry `churnguardacr` (SKU Basic, Admin Enabled).
   - **Bước 7:** **Cloud-Native Docker Build (`az acr build`):** Đóng gói mã nguồn và build Docker Image trực tiếp trên hạ tầng Cloud của Azure. **Ưu điểm vượt trội: Người dùng không cần bật Docker Desktop trên máy tính cá nhân!**
   - **Bước 8:** Tạo Azure Container Apps Environment `env-churnguard-mlops`.
   - **Bước 9:** Cấp phát Container App `churnguard-serving-app` với cấu hình 1.0 vCPU, 2.0 GiB RAM, mở cổng Ingress 8000 ra Internet, cơ chế tự động co giãn Serverless (`min-replicas: 0, max-replicas: 5`).
3. **Dấu hiệu THÀNH CÔNG:**
   - Màn hình terminal in ra khung thông báo hoàn tất:
     ```text
     ==============================================================================
     [+] CHUC MUNG! HE THONG MLOPS DA DUOC TRIEN KHAI THANH CONG TREN AZURE CLOUD!
     ==============================================================================
       - Public Endpoint URL : https://churnguard-serving-app.<random>.southeastasia.azurecontainerapps.io
       - Interactive Web UI  : https://churnguard-serving-app.<random>.southeastasia.azurecontainerapps.io/ui
       - Swagger API Docs    : https://churnguard-serving-app.<random>.southeastasia.azurecontainerapps.io/docs
       - Health Check        : https://churnguard-serving-app.<random>.southeastasia.azurecontainerapps.io/health
     ==============================================================================
     ```
   - Mở trình duyệt truy cập `Interactive Web UI` (`https://<FQDN>/ui`) để trải nghiệm giao diện Bento Grid hoạt động 100% trên nền tảng đám mây Microsoft Azure!

---

### 6.5 Chẩn đoán sự cố triển khai Cloud thường gặp & Cách khắc phục triệt để
- **Sự cố 1: Lỗi nghẽn hạn mức vCPU tại Singapore (`ResourceProviderQuotaExceeded`):**
  * *Nguyên nhân:* Vùng `southeastasia` chịu tải cao từ các tài khoản sinh viên miễn phí.
  * *Khắc phục:* Mở tệp `deploy/azure/deploy_azure.bat`, sửa dòng 15 thành `set LOCATION=eastus` (Mỹ) hoặc `set LOCATION=eastasia` (Hong Kong), sau đó chạy lại script.
- **Sự cố 2: Lỗi trùng tên Storage Account toàn cầu (`StorageAccountAlreadyTaken`):**
  * *Nguyên nhân:* Tên `stchurnguardsea2026` đã có người khác đăng ký trên DNS toàn cầu của Microsoft.
  * *Khắc phục:* Mở `deploy/azure/deploy_azure.bat`, sửa dòng 19 thành `set STORAGE_ACCOUNT=stchurnguard%RANDOM%2026` (hoặc gắn thêm MSSV).
- **Sự cố 3: Lỗi lệch cổng Ingress (502 Bad Gateway / Connection Refused):**
  * *Khắc phục:* Kiểm tra cổng đích Container App đã trỏ đúng 8000 hay chưa bằng lệnh:
    ```bash
    cmd /c "az containerapp update --name churnguard-serving-app --resource-group rg-churnguard-mlops-sea --target-port 8000"
    ```

---

### 6.6 Lệnh thu hồi tài nguyên sau khi nghiệm thu (FinOps - Bảo toàn ngân sách)
Sau khi kết thúc buổi bảo vệ đồ án hoặc kiểm thử, để đảm bảo không còn dịch vụ nào chạy ngầm làm suy hao số dư $100 credit, thực thi **1 câu lệnh duy nhất**:

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
| **Lỗi Chiếm Cổng 8000** | `[Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)` | Tiến trình Uvicorn cũ hoặc ứng dụng khác đang chiếm dụng cổng 8000 | Tìm PID: `cmd /c "netstat -ano \| findstr :8000"`<br>Diệt PID: `cmd /c "taskkill /F /PID <PID>"` |
| **Lỗi Chiếm Cổng 8501** | `Port 8501 is already in use` | Tiến trình Streamlit cũ đang chạy ngầm | Chạy Streamlit trên cổng phụ: `cmd /c "streamlit run src/web/dashboard.py --server.port 8502"` |
| **Lỗi Thiếu Trọng Số Model** | `FileNotFoundError: champion_model.joblib` | Chưa chạy pipeline huấn luyện mô hình | Sinh mới mô hình: `cmd /c "python src/models/train_pipeline.py"` |
| **Lỗi Thiếu Báo Cáo Drift** | `404 Not Found: docs/drift_report.html` | Chưa biên dịch báo cáo trôi dạt dữ liệu HTML | Sinh báo cáo drift: `cmd /c "python src/monitoring/drift_detector.py"` |
| **Lỗi Khóa Ghi SQLite WAL** | `sqlite3.OperationalError: database is locked` | Nhiều tiến trình cùng ghi vào SQLite khi chưa bật chế độ WAL | Mã nguồn đã tự động kích hoạt `PRAGMA journal_mode=WAL; busy_timeout=5000;` để tự giải tỏa |
| **Lỗi Docker Daemon Offline** | `failed to connect to the docker API at npipe://...` | Docker Desktop cục bộ chưa được bật | Kịch bản `deploy_azure.bat` sử dụng `az acr build` trên Cloud nên **hoàn toàn không cần Docker Desktop** |
| **Lỗi Azure Quota vCPU** | `Quota limit exceeded in region southeastasia` | Hạn ngạch tài khoản sinh viên tại vùng Singapore bị quá tải | Sửa dòng 15 trong `deploy_azure.bat` thành `set LOCATION=eastus` hoặc `eastasia` |
| **Lỗi Trùng Tên Storage** | `StorageAccountAlreadyTaken: ... is already taken` | Tên Azure Storage Account bị trùng lặp trên phạm vi toàn cầu | Sửa dòng 19 trong `deploy_azure.bat` thành `set STORAGE_ACCOUNT=stchurnguard%RANDOM%2026` |
