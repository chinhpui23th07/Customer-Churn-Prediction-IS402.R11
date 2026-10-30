# SỔ TAY HƯỚNG DẪN VẬN HÀNH HỆ THỐNG (OPERATIONAL RUNBOOK)
## ChurnGuard-MLOps Level 2 Enterprise Platform

Tài liệu này cung cấp hướng dẫn chi tiết từng bước (Step-by-Step Runbook) để vận hành, kiểm thử và tương tác với toàn bộ các phân hệ của nền tảng ChurnGuard-MLOps, bao gồm:
1. **Khởi động dịch vụ cục bộ (Local Server & Streamlit Dashboard)**.
2. **Hướng dẫn thao tác chi tiết trên giao diện Web Bento Grid (`http://localhost:8000`)**.
3. **Hướng dẫn thao tác trên bảng điều khiển phân tích Streamlit (`http://localhost:8501`)**.
4. **Hướng dẫn kiểm thử trực tiếp qua Swagger REST API (`http://localhost:8000/docs`)**.
5. **Hướng dẫn từng bước đăng ký Azure for Students ($100 miễn phí) và Triển khai Cloud 1-Click**.

---

## 1. KHỞI ĐỘNG HỆ THỐNG MLOPS DƯỚI LOCAL

Trước khi tương tác trên trình duyệt web, mở Terminal (PowerShell hoặc Command Prompt) tại thư mục gốc của dự án (`c:\Users\Nguyen Trong Khoi\Downloads\CLOUD`) để khởi chạy các dịch vụ:

### 1.1 Khởi động FastAPI Model Serving & Web Console
- **Lệnh thực thi:**
  ```bash
  cmd /c "python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
  ```
- **Hiện tượng trên màn hình:**
  * Terminal hiển thị tiến trình nạp mô hình Champion (XGBoost), Scaler, và khởi tạo SHAP TreeExplainer.
- **Dấu hiệu THÀNH CÔNG:**
  * Xuất hiện các dòng log màu xanh lá:
    ```
    INFO:     Started server process [PID]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
    ```
- **Dấu hiệu LỖI & Cách xử lý:**
  * **Lỗi `[Errno 10048] Address already in use`:** Cổng 8000 đang bị ứng dụng khác chiếm dụng.  
    *Cách khắc phục:* Chạy lệnh giải phóng cổng:
    ```bash
    cmd /c "netstat -ano | findstr :8000"
    cmd /c "taskkill /F /PID <PID_tim_duoc>"
    ```

### 1.2 Khởi động Streamlit Monitoring Dashboard
- **Mở thêm 1 cửa sổ Terminal mới** và chạy lệnh:
  ```bash
  cmd /c "streamlit run src/web/dashboard.py --server.port 8501"
  ```
- **Dấu hiệu THÀNH CÔNG:**
  * Terminal hiển thị:
    ```
    You can now view your Streamlit app in your browser.
    Local URL: http://localhost:8501
    Network URL: http://...:8501
    ```
  * Trình duyệt tự động mở tab mới truy cập `http://localhost:8501`.
- **Dấu hiệu LỖI & Cách xử lý:**
  * Báo lỗi thiếu thư viện `plotly` hoặc `streamlit`: Chạy `cmd /c "pip install streamlit plotly"`.

---

## 2. HƯỚNG DẪN THAO TÁC TRÊN GIAO DIỆN WEB BENTO GRID

- **Địa chỉ truy cập (URL):** `http://localhost:8000/` (hoặc `http://localhost:8000/ui`)
- **Tên trang hiển thị:** `ChurnGuard MLOps - Enterprise Customer Retention Platform`
- **Bố cục tổng quan:**
  * **Thanh Header (Trên cùng):** Logo ChurnGuard bên trái; Trạng thái kết nối API (`FastAPI: healthy (Online)`) và huy hiệu mô hình (`Champion: XGBoost`) ở góc trên bên phải.
  * **Hàng chỉ số KPI (Phía trên):** 4 thẻ Bento Card (Mô hình Champion, Feast Feature Store, Độ trễ dự đoán, Trạng thái Data Drift).
  * **Khu vực làm việc chính (Phía dưới):** Chia thành 2 cột:
    - **Cột bên trái:** Form "Dự Đoán Thời Gian Thực" cho khách hàng đơn lẻ.
    - **Cột bên phải:** Thẻ "Phân Tích & Giám Sát" gồm 3 Tab chức năng.

---

### Thao tác 2.1: Phân tích nguy cơ rời bỏ của 1 khách hàng đơn lẻ
- **Vị trí thao tác:** Khung thẻ form màu xanh đậm ở **Cột bên trái màn hình**.
- **Tiêu đề khung:** `Dự Đoán Thời Gian Thực` (kèm nhãn tag `REST API: /predict`).
- **Các bước thực hiện:**
  1. Nhìn vào các ô nhập liệu trên form, có thể giữ nguyên giá trị mặc định hoặc thay đổi:
     - `Mã khách hàng (Customer ID)`: ví dụ `1001` (góc trên bên trái form).
     - `Độ tuổi`: ví dụ `38` (góc trên bên phải form).
     - `Giới tính`: chọn `Nam (Male)` hoặc `Nữ (Female)`.
     - `Thời gian gắn bó (tháng)`: ví dụ `24`.
     - `Tần suất sử dụng (lần/tháng)`: ví dụ `18`.
     - `Số cuộc gọi hỗ trợ`: ví dụ `4`.
     - `Trễ hạn thanh toán (ngày)`: ví dụ `8`.
     - `Gói cước`: chọn `Basic`, `Standard`, hoặc `Premium`.
     - `Loại hợp đồng`: chọn `Theo Tháng (Monthly)`, `Theo Quý (Quarterly)`, hoặc `Theo Năm (Annual)`.
     - `Tổng chi tiêu ($)`: ví dụ `450`.
     - `Lần tương tác cuối (ngày)`: ví dụ `15`.
  2. Tìm nút bấm phân tích:
     - **Tên nút:** **`Phân Tích Nguy Cơ Rời Bỏ`**
     - **Màu sắc & Kiểu dáng:** Nút hình chữ nhật bo tròn góc, màu xanh Teal đậm (`#0F766E`), chữ in màu trắng, độ rộng chiếm 100% chiều ngang form.
     - **Vị trí chính xác:** Nằm ở **DƯỚI CÙNG của khung form bên trái**.
  3. Bấm chuột trái vào nút **`Phân Tích Nguy Cơ Rời Bỏ`**.
- **Hiện tượng diễn ra sau khi bấm:**
  * Chữ trên nút tạm thời đổi thành `Đang Phân Tích...` trong khoảng 0.5 giây.
  * Khung kết quả dự đoán (`#prediction-result`) trượt mở ra ngay bên dưới nút bấm.
- **Dấu hiệu THÀNH CÔNG:**
  * **Huy hiệu mức độ rủi ro (Nằm ở góc trên bên trái của khối kết quả):**
    - Nếu rủi ro cao: Huy hiệu màu đỏ tươi mang dòng chữ **`RỦI RO CAO (HIGH RISK)`**.
    - Nếu rủi ro trung bình: Huy hiệu màu vàng cam **`RỦI RO TRUNG BÌNH (MEDIUM RISK)`**.
    - Nếu an toàn: Huy hiệu màu xanh ngọc **`AN TOÀN (LOW RISK)`**.
  * **Huy hiệu độ trễ (Nằm ở góc trên bên phải của khối kết quả):** Hiển thị thời gian phản hồi siêu tốc, ví dụ `0.42 ms` hoặc `1.15 ms`.
  * **Đồng hồ đo xác suất (Nằm ở giữa khối kết quả):**
    - Hiển thị con số phần trăm lớn, ví dụ: **`88.5%`**.
    - Thanh đo nằm ngang (`Gauge Bar`) đổ đầy màu tương ứng (đỏ nếu cao, xanh nếu thấp).
  * **Khung chiến lược giữ chân đề xuất:** Hiển thị giải pháp nghiệp vụ $e\text{-Profits}$ cụ thể (ví dụ: *"Cung cấp ưu đãi giảm giá 20% khi gia hạn hợp đồng năm..."*).
  * **Khung giải thích mô hình (SHAP Attributions):**
    - Hiển thị đoạn tóm tắt nhân tố chính.
    - Hiển thị các thanh đo hai chiều: thanh màu đỏ có dấu `+` biểu thị nhân tố làm tăng nguy cơ rời bỏ (như `support_calls`, `payment_delay`); thanh màu xanh có dấu `-` biểu thị nhân tố giúp níu giữ khách hàng (như `total_spend`, `tenure`).
- **Dấu hiệu LỖI & Cách xử lý:**
  * Trình duyệt hiện hộp thoại thông báo (Alert): *"Không thể kết nối đến FastAPI Serving Endpoint! Đảm bảo server đang chạy tại port 8000."*  
    *Khắc phục:* Kiểm tra lại cửa sổ Terminal của bước 1.1 xem máy chủ Uvicorn có đang chạy không.

---

### Thao tác 2.2: Dự đoán hàng loạt bằng 5 khách hàng mẫu
- **Vị trí thao tác:** Khung thẻ "Phân Tích & Giám Sát" ở **Cột bên phải màn hình**.
- **Các bước thực hiện:**
  1. Nhìn vào thanh chuyển Tab ở trên cùng của thẻ bên phải.
  2. Bấm vào Tab đầu tiên bên trái có tên **`Dự Đoán Hàng Loạt (CSV)`** (Mặc định tab này đã được kích hoạt sẵn).
  3. Quan sát khung nét đứt màu xanh nhạt (Khu vực kéo thả file).
  4. Tìm nút bấm dữ liệu mẫu:
     - **Tên nút:** **`Tải 5 Khách Hàng Mẫu`**
     - **Màu sắc & Kiểu dáng:** Nút viền trong suốt (Outline button), viền trắng bạc, chữ màu trắng.
     - **Vị trí chính xác:** Nằm ở **GÓC DƯỚI BÊN PHẢI bên trong khung kéo thả file** (nằm cạnh nút "Chọn Tệp CSV").
  5. Bấm chuột trái vào nút **`Tải 5 Khách Hàng Mẫu`**.
- **Hiện tượng diễn ra sau khi bấm:**
  * Hệ thống gửi ngay gói dữ liệu 5 khách hàng mẫu đến API `/batch_predict`.
  * Khu vực kết quả hàng loạt xuất hiện ngay bên dưới khung kéo thả file.
- **Dấu hiệu THÀNH CÔNG:**
  * Xuất hiện 4 viên thuốc thống kê tổng quan (Stat Pills) nằm ngang:
    - Viên 1: `Tổng số: 5`
    - Viên 2: `Rời bỏ: X` (chữ màu đỏ)
    - Viên 3: `Ở lại: Y` (chữ màu xanh lá)
    - Viên 4: `Tỷ lệ: Z%` (chữ màu vàng)
  * Xuất hiện một bảng dữ liệu chi tiết gồm 5 dòng tương ứng với 5 khách hàng (#101 đến #105), hiển thị xác suất rời bỏ, mức độ rủi ro có gắn nhãn màu, và chiến lược giữ chân riêng cho từng khách hàng.
  * Xuất hiện một nút bấm màu xanh dương **`Xuất Báo Cáo CSV Gắn Nhãn`** ở **dưới cùng của bảng**. Bấm vào nút này sẽ tự động tải về máy tính một tệp `churn_predictions_annotated_<timestamp>.csv`.
- **Dấu hiệu LỖI & Cách xử lý:**
  * Alert: *"Không thể gửi dữ liệu mẫu đến API."* -> Kiểm tra lại kết nối mạng hoặc tiến trình Uvicorn.

---

### Thao tác 2.3: Tải tệp CSV tùy chỉnh từ máy tính để phân tích lô
- **Vị trí thao tác:** Vẫn tại Tab **`Dự Đoán Hàng Loạt (CSV)`** ở cột bên phải.
- **Các bước thực hiện:**
  1. Tìm nút bấm chọn tệp:
     - **Tên nút:** **`Chọn Tệp CSV`**
     - **Màu sắc & Kiểu dáng:** Nút màu xám than (Secondary button), chữ màu trắng.
     - **Vị trí chính xác:** Nằm ở **GÓC DƯỚI BÊN TRÁI bên trong khung kéo thả file** (cạnh biểu tượng đám mây tải lên).
  2. Bấm chuột trái vào nút **`Chọn Tệp CSV`**.
  3. Cửa sổ chọn tệp của hệ điều hành Windows mở ra. Điều hướng tới tệp CSV dữ liệu kiểm thử trong thư mục dự án:  
     `c:\Users\Nguyen Trong Khoi\Downloads\CLOUD\data\raw\customer_churn_dataset-testing-master.csv`
  4. Bấm **Open** (hoặc nhấn đúp chuột vào tệp).
- **Hiện tượng diễn ra sau khi bấm:**
  * Tệp CSV được tải ngầm lên endpoint `/upload_csv_predict`.
  * Sau 1 - 2 giây xử lý lô, bảng kết quả hiển thị dữ liệu đã được gán nhãn dự đoán cho toàn bộ danh sách khách hàng trong tệp.
- **Dấu hiệu THÀNH CÔNG:**
  * Bảng thống kê hiển thị chính xác tổng số dòng trong tệp CSV, số lượng khách hàng rời bỏ/ở lại và tỷ lệ churn.
  * Bảng hiển thị 10 dòng đầu tiên làm mẫu và cho phép bấm nút **`Xuất Báo Cáo CSV Gắn Nhãn`** để tải toàn bộ kết quả phân loại đã được làm giàu về máy.
- **Dấu hiệu LỖI & Cách xử lý:**
  * Alert: *"Lỗi tải tệp CSV! Đảm bảo các cột đúng định dạng Kaggle Customer Churn."*  
    *Khắc phục:* Tệp CSV thiếu các cột bắt buộc (`Age`, `Gender`, `Tenure`, `Usage Frequency`, `Support Calls`, `Payment Delay`, `Subscription Type`, `Contract Length`, `Total Spend`, `Last Interaction`). Sử dụng tệp CSV chuẩn trong thư mục `data/raw/`.

---

### Thao tác 2.4: Xem bảng so sánh 4 mô hình & Đồ thị Optuna
- **Vị trí thao tác:** Nhìn lên thanh chuyển Tab ở trên cùng của thẻ bên phải.
- **Các bước thực hiện:**
  1. Tìm nút tab:
     - **Tên tab:** **`So Sánh Mô Hình`**
     - **Vị trí chính xác:** Nằm ở **CHÍNH GIỮA thanh tab** (giữa tab "Dự Đoán Hàng Loạt" và tab "Giám Sát Drift").
  2. Bấm chuột trái vào tab **`So Sánh Mô Hình`**.
- **Hiện tượng diễn ra sau khi bấm:**
  * Nội dung tab chuyển sang màn hình đối chuẩn thuật toán học máy.
- **Dấu hiệu THÀNH CÔNG:**
  * **Bảng dữ liệu phía trên:** Hiển thị đầy đủ 4 mô hình:
    1. `XGBoost (Champion)` (có chữ Champion màu vàng cam)
    2. `LightGBM`
    3. `Random Forest`
    4. `Logistic Regression`
    Kèm các cột chỉ số Accuracy, Precision, Recall, F1-Score, và ROC-AUC (XGBoost đạt `0.9989` màu xanh lá nổi bật).
  * **Khung đồ thị bên trái:** Biểu đồ cột tương tác (Interactive Bar) so sánh trực quan các chỉ số giữa 4 mô hình. Rê chuột vào các cột để xem điểm số chi tiết.
  * **Khung đồ thị bên phải:** Biểu đồ đường cong hội tụ siêu tham số (Optuna Convergence) thể hiện ROC-AUC tăng dần qua 12 trials thử nghiệm của thuật toán Bayesian TPE.
- **Dấu hiệu LỖI & Cách xử lý:**
  * Bảng hiển thị: *"Đang đồng bộ số liệu hiệu năng 4 mô hình từ REST API..."* quá lâu -> Kiểm tra xem tệp `data/models/evaluation_results.json` có tồn tại trên ổ đĩa không.

---

### Thao tác 2.5: Giám sát Data Drift & Mở báo cáo HTML chuyên sâu
- **Vị trí thao tác:** Nhìn lên thanh chuyển Tab ở trên cùng của thẻ bên phải.
- **Các bước thực hiện:**
  1. Tìm nút tab:
     - **Tên tab:** **`Giám Sát Drift`**
     - **Vị trí chính xác:** Nằm ở **GÓC NGOÀI CÙNG BÊN PHẢI của thanh tab**.
  2. Bấm chuột trái vào tab **`Giám Sát Drift`**.
- **Hiện tượng diễn ra sau khi bấm:**
  * Hiển thị bảng đối soát thống kê 13 đặc trưng dữ liệu giữa tập Reference (Train) và Current (Inference logs).
- **Dấu hiệu THÀNH CÔNG:**
  * Bảng hiển thị đầy đủ các cột: Tên Đặc Trưng, KS-Statistic, P-Value (kiểm định 2 mẫu Kolmogorov-Smirnov), PSI Score, và Trạng Thái (gắn nhãn màu xanh lá `Stable`, vàng `Moderate`, hoặc đỏ `High`).
  * Tìm nút mở báo cáo chi tiết:
    - **Tên nút:** **`Mở Báo Cáo HTML Chi Tiết`**
    - **Màu sắc & Kiểu dáng:** Nút viền ngoài nhỏ gọn, chữ màu trắng.
    - **Vị trí chính xác:** Nằm ở **GÓC TRÊN BÊN PHẢI của khung tiêu đề Giám Sát Drift**.
  * Bấm chuột vào nút **`Mở Báo Cáo HTML Chi Tiết`** -> Trình duyệt tự động mở tab mới truy cập đường dẫn `http://localhost:8000/docs/drift_report.html` hiển thị toàn bộ biểu đồ phân phối xác suất tương tác.
- **Dấu hiệu LỖI & Cách xử lý:**
  * Trình duyệt báo lỗi `404 Not Found` khi mở trang HTML: Tệp `docs/drift_report.html` chưa được biên dịch. Chạy lệnh: `cmd /c "python src/monitoring/drift_detector.py"`.

---

## 3. HƯỚNG DẪN THAO TÁC TRÊN BẢNG ĐIỀU KHIỂN STREAMLIT

- **Địa chỉ truy cập (URL):** `http://localhost:8501/`
- **Tên trang:** `ChurnGuard MLOps Enterprise Dashboard`
- **Cột Sidebar (Bên trái):**
  * Hiển thị thông số cấu hình hệ thống (Pipeline DVC, Feast Feature Store, Mô hình Champion XGBoost, Tỷ lệ A/B 80/20).
  * Tìm nút: **`Làm mới ngay (Refresh)`** nằm ở giữa Sidebar. Bấm vào nút này để đọc lại toàn bộ dữ liệu mới nhất từ SQLite database.
- **Khu vực hiển thị chính gồm 4 Tab ngang:**

### 3.1 Tab 1: `[KPI] Giám Sát Suy Luận & KPI` (Tab mặc định)
- **Vị trí:** Tab đầu tiên bên trái trên thanh tab ngang.
- **Nội dung hiển thị:**
  * 4 khối thẻ KPI màu gradient xanh đen: Tổng Lượt Suy Luận, Tỷ Lệ Dự Đoán Rời Bỏ, Điều Hướng Champion (80%), Trạng Thái Phục Vụ (`[ONLINE] HOẠT ĐỘNG`).
  * Khung bảng dữ liệu: `Nhật Ký Suy Luận Thời Gian Thực Gần Nhất` lưu trong SQLite WAL (`data/inference_logs.db`), cho phép tìm kiếm, lọc và phân trang từng lượt dự đoán.

### 3.2 Tab 2: `[DRIFT] Giám Sát Data Drift & Cảnh Báo`
- **Vị trí:** Tab thứ hai từ trái sang.
- **Nội dung hiển thị:**
  * Khung trạng thái cảnh báo màu xanh lá (`[OK] HỆ THỐNG ỔN ĐỊNH`) hoặc màu đỏ (`[ALERT] CẢNH BÁO DATA DRIFT`).
  * Biểu đồ thanh ngang Plotly hiển thị chỉ số Population Stability Index (PSI) cho từng đặc trưng, có vạch kẻ đỏ nét đứt tại ngưỡng biến động mạnh `PSI = 0.25`.
  * Bảng đối soát thống kê kiểm định Kolmogorov-Smirnov hiệu chỉnh Bonferroni ($\alpha = 0.003846$).

### 3.3 Tab 3: `[A/B] Thử Nghiệm A/B Testing`
- **Vị trí:** Tab thứ ba từ trái sang.
- **Nội dung hiển thị:**
  * Cột trái: Biểu đồ hình tròn Donut thể hiện tỷ lệ điều hướng thực tế qua thuật toán băm Murmur3 (80% lưu lượng tới Champion XGBoost và 20% tới Challenger Random Forest).
  * Cột phải: Bảng kết quả kiểm định giả thuyết thống kê (Welch's Two-Sample t-test) gồm T-statistic, P-value và kết luận nghiệp vụ.

### 3.4 Tab 4: `[DIAG] Chẩn Đoán Mô Hình & Lỗi Dự Đoán`
- **Vị trí:** Tab thứ tư ngoài cùng bên phải.
- **Nội dung hiển thị:**
  * 2 hình ảnh đồ thị phân tích: Đường cong học tập (Learning Curves) và Đường cong hiệu chuẩn xác suất (Calibration Curve).
  * Hình ảnh biểu đồ phân tích lỗi sai (Error Analysis): Phân tích phân bố của nhóm False Positives (FP) và False Negatives (FN).
  * Bảng chỉ số ma trận nhầm lẫn chuẩn xác: $TN=28,619, TP=37,627, FP=70, FN=16$, Accuracy $0.9989$, ROC-AUC $0.9989$.

---

## 4. HƯỚNG DẪN KIỂM THỬ TRỰC TIẾP QUA SWAGGER REST API

- **Địa chỉ truy cập (URL):** `http://localhost:8000/docs`
- **Giao diện hiển thị:** Trang Swagger UI chuẩn OpenAPI với danh sách các endpoint REST API được gom nhóm.

### Thao tác 4.1: Kiểm thử dự đoán đơn lẻ qua `POST /predict`
1. Cuộn chuột đến nhóm **Inference**, tìm dòng thanh màu xanh lá mang nhãn **`POST /predict`**.
2. Bấm chuột trái vào dòng **`POST /predict`** để mở rộng chi tiết endpoint.
3. Tìm nút:
   - **Tên nút:** **`Try it out`**
   - **Kiểu dáng:** Nút nhỏ hình chữ nhật, viền đen xám.
   - **Vị trí:** Nằm ở **GÓC TRÊN BÊN PHẢI của khung chi tiết endpoint**.
4. Bấm vào nút **`Try it out`**. Khung soạn thảo `Request body` sẽ chuyển sang chế độ cho phép chỉnh sửa văn bản JSON.
5. Giữ nguyên JSON mẫu hoặc chỉnh sửa thông số khách hàng.
6. Cuộn xuống một chút, tìm nút thực thi:
   - **Tên nút:** **`Execute`**
   - **Kiểu dáng:** Nút hình chữ nhật to, màu xanh dương đậm (`#4990E2`), chữ trắng in hoa.
   - **Vị trí:** Nằm ở **GÓC DƯỚI BÊN TRÁI của khung soạn thảo Request body**.
7. Bấm vào nút **`Execute`**.
- **Dấu hiệu THÀNH CÔNG:**
  * Khung `Responses` bên dưới hiển thị mã phản hồi màu xanh lá: **`Code 200`**.
  * Khung `Response body` hiển thị định dạng JSON chuẩn:
    ```json
    {
      "customer_id": 1001,
      "churn_prediction": 1,
      "churn_probability": 0.885,
      "risk_level": "High Risk",
      "recommended_action": "Cung cap uu dai giam gia...",
      "latency_ms": 0.45,
      "feature_attributions": { ... }
    }
    ```
- **Dấu hiệu LỖI & Cách xử lý:**
  * Mã phản hồi màu đỏ **`Code 422 Unprocessable Entity`**: Dữ liệu đầu vào sai kiểu dữ liệu (ví dụ: nhập chữ vào trường số `age`, hoặc để trống trường bắt buộc). Xem chi tiết trường lỗi trong phần `detail` của JSON.

### Thao tác 4.2: Kích hoạt Webhook tái huấn luyện qua `POST /api/v1/trigger_retrain`
1. Cuộn xuống nhóm **Operations**, tìm dòng **`POST /api/v1/trigger_retrain`**.
2. Bấm mở rộng -> Bấm nút **`Try it out`** ở góc trên bên phải.
3. Bấm nút **`Execute`** màu xanh dương.
- **Dấu hiệu THÀNH CÔNG:**
  * Trả về **`Code 200`** với cấu trúc JSON:
    ```json
    {
      "status": "SKIPPED",
      "message": "Data drift under threshold...",
      "drift_share": 0.15
    }
    ```
    (Hoặc `status: "TRIGGERED"` nếu tỷ lệ drift vượt 30%, hoặc `status: "ALREADY_RUNNING"` nếu tiến trình retrain nền đang thực thi).

---

## 5. HƯỚNG DẪN TỪNG BƯỚC ĐĂNG KÝ AZURE FOR STUDENTS & TRIỂN KHAI CLOUD 1-CLICK

Quy trình này giúp bạn sở hữu tài khoản Microsoft Azure hoàn toàn miễn phí ($0 chi phí cá nhân, không cần thẻ ngân hàng) và đưa hệ thống lên mây.

---

### Bước 5.1: Đăng ký tài khoản Azure for Students nhận $100 Credit miễn phí
1. **Truy cập đường dẫn chính thức:**  
   Mở trình duyệt web (Edge hoặc Chrome) và truy cập:  
   👉 **`https://azure.microsoft.com/free/students/`**
2. **Tìm nút đăng ký:**
   - **Tên nút:** **`Start free`** (hoặc `Bắt đầu miễn phí` nếu giao diện tiếng Việt).
   - **Màu sắc:** Nút màu xanh lá cây hoặc xanh dương sáng nổi bật.
   - **Vị trí chính xác:** Nằm ở **CHÍNH GIỮA banner trang chủ (Hero section)** hoặc góc trên bên phải thanh điều hướng.
3. Bấm vào nút **`Start free`**.
4. **Đăng nhập tài khoản Microsoft:**
   - Trang web chuyển hướng sang màn hình đăng nhập `login.microsoftonline.com`.
   - **Nhập email:** Sử dụng email sinh viên do trường đại học cấp (ví dụ: `mssv@gm.uit.edu.vn` hoặc `mssv@uit.edu.vn`).
   - Bấm nút **`Next`** màu xanh dương ở góc dưới bên phải khung đăng nhập.
   - Nhập mật khẩu tài khoản email trường và bấm **`Sign in`**.
5. **Xác thực danh tính sinh viên (Academic Verification):**
   - Hệ thống hiển thị trang yêu cầu xác nhận đối tượng sinh viên.
   - Tại mục "Verification method", chọn **`School email address`**.
   - Nhập lại địa chỉ email trường và bấm nút **`Send verification email`**.
   - Mở tab mới truy cập hộp thư sinh viên trường để nhận email từ Microsoft chứa mã số xác thực 6 chữ số.
   - Quay lại trang Azure, nhập 6 chữ số vào ô "Verification code" và bấm nút **`Verify code`**.
6. **Khai báo thông tin hồ sơ & Chấp thuận điều khoản:**
   - Điền Họ tên, số điện thoại di động (nhận mã OTP SMS xác thực thiết bị).
   - **Lưu ý đặc biệt:** Trang này **TUYỆT ĐỐI KHÔNG HỎI SỐ THẺ TÍN DỤNG HAY THẺ NGÂN HÀNG**.
   - Tích chọn vào ô vuông: *"I agree to the subscription agreement, offer details and privacy statement"* nằm ở góc dưới bên trái form.
7. **Bấm nút hoàn tất:**
   - **Tên nút:** **`Sign up`** (hoặc `Đăng ký`).
   - **Vị trí:** Nút màu xanh dương to nằm ở **DƯỚI CÙNG BÊN PHẢI form đăng ký**.
8. **Dấu hiệu THÀNH CÔNG:**
   - Màn hình chuyển hướng đến trang chủ **Microsoft Azure Portal** (`https://portal.azure.com`).
   - Một thông báo chào mừng hiện lên và mục Subscriptions hiển thị gói **`Azure for Students`** với số dư khả dụng **`$100.00 USD Credit`**.
   - Mặc định gói này có chốt chặn cứng (`Spending Limit: On`), đảm bảo 100% không phát sinh nợ hay trừ tiền.
9. **Dấu hiệu LỖI & Cách xử lý:**
   - Thông báo *"You're not eligible for an Azure student account"*: Email trường chưa được đồng bộ trong cơ sở dữ liệu học viện của Microsoft. Liên hệ phòng đào tạo/IT trường hoặc đăng ký xác thực qua GitHub Student Developer Pack.

---

### Bước 5.2: Đăng nhập Azure CLI trên máy tính của bạn
- Azure CLI 2.91.0 đã được cài đặt sẵn trên máy tính của bạn tại:  
  `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`
- **Mở Terminal (PowerShell hoặc CMD) và chạy lệnh:**
  ```bash
  cmd /c "\"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd\" login"
  ```
- **Hiện tượng trên màn hình:**
  * Trình duyệt web mặc định tự động bật lên một tab đăng nhập Microsoft.
  * Danh sách tài khoản hiện ra: Bấm chọn tài khoản sinh viên vừa đăng ký ở Bước 5.1.
- **Dấu hiệu THÀNH CÔNG:**
  * Trình duyệt web hiển thị thông báo: *"You have logged into Microsoft Azure!"*
  * Cửa sổ Terminal hiển thị thông tin gói thuê bao:
    ```json
    [
      {
        "cloudName": "AzureCloud",
        "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "isDefault": true,
        "name": "Azure for Students",
        "state": "Enabled"
      }
    ]
    ```
- **Dấu hiệu LỖI & Cách xử lý:**
  * Nếu trình duyệt không tự mở: Chạy lệnh `cmd /c "\"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd\" login --use-device-code"`, truy cập `https://microsoft.com/devicelogin` và nhập mã code hiển thị trên terminal.

---

### Bước 5.3: Thực thi kịch bản Triển khai 1-Click lên Cloud Azure
- **Chạy lệnh triển khai tự động duy nhất:**
  ```bash
  cmd /c "deploy\azure\deploy_azure.bat"
  ```
- **Tiến trình tự động diễn ra (mất khoảng 8 - 12 phút):**
  1. Kiểm tra Azure CLI và xác nhận đăng nhập hợp lệ.
  2. Tạo Resource Group `rg-churnguard-mlops-sea` tại khu vực Đông Nam Á (`southeastasia` - Singapore).
  3. Cấp phát Azure Storage Account `stchurnguardsea2026` và Blob Container `churnguard-datasets`.
  4. Cấp phát Azure Cache for Redis C0 (SSL Port 6380) cho Feast Feature Store.
  5. Cấp phát Azure Container Registry (ACR) `churnguardacr`.
  6. Thực hiện Cloud-Native Docker Build và đẩy Docker image lên ACR (`az acr build`).
  7. Tạo môi trường Azure Container Apps Managed Environment `env-churnguard-mlops`.
  8. Cấp phát và khởi chạy Container App `churnguard-serving-app` với cấu hình 1.0 vCPU, 2.0 GiB RAM và cơ chế tự co giãn Serverless Scale-to-Zero (`min-replicas: 0, max-replicas: 5`).
- **Dấu hiệu THÀNH CÔNG:**
  * Màn hình Terminal in ra khung thông báo hoàn tất:
    ```
    ==============================================================================
    [+] CHUC MUNG! HE THONG MLOPS DA DUOC TRIEN KHAI THANH CONG TREN AZURE CLOUD!
    ==============================================================================
      - Public Endpoint URL : https://churnguard-serving-app.<random>.southeastasia.azurecontainerapps.io
      - Interactive Web UI  : https://churnguard-serving-app.<random>.southeastasia.azurecontainerapps.io/ui
      - Swagger API Docs    : https://churnguard-serving-app.<random>.southeastasia.azurecontainerapps.io/docs
      - Health Check        : https://churnguard-serving-app.<random>.southeastasia.azurecontainerapps.io/health
    ==============================================================================
    ```
  * Mở trình duyệt truy cập vào đường dẫn `Interactive Web UI` để trải nghiệm hệ thống hoạt động trực tiếp trên hạ tầng Cloud của Microsoft!
- **Dấu hiệu LỖI & Cách xử lý:**
  * Lỗi `ResourceGroupNotFound` hoặc `SubscriptionNotFound`: Kiểm tra lại trạng thái đăng nhập qua `az account show`.
  * Lỗi `QuotaExceeded` cho Container Apps tại vùng Singapore: Mở tệp `deploy/azure/deploy_azure.bat`, đổi dòng 15 thành `set LOCATION=eastasia` (Hong Kong) rồi chạy lại.

---

### Bước 5.4: Lệnh dọn dẹp sạch sẽ tài nguyên sau khi chấm bài xong (Bảo vệ ngân sách)
Khi đã bảo vệ đồ án hoặc chấm bài xong, để đảm bảo không còn bất kỳ tài nguyên nào chạy ngầm làm hao hụt số dư $100 credit, bạn chỉ cần thực hiện **1 câu lệnh duy nhất**:

```bash
cmd /c "\"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd\" group delete --name rg-churnguard-mlops-sea --yes --no-wait"
```

- **Hiện tượng diễn ra:**
  * Lệnh gửi yêu cầu thu hồi bất đồng bộ lên Azure Resource Manager và trả về terminal ngay lập tức.
- **Dấu hiệu THÀNH CÔNG:**
  * Đăng nhập vào Azure Portal kiểm tra: Toàn bộ Resource Group `rg-churnguard-mlops-sea` cùng tất cả 6 dịch vụ con (Container App, ACR, Redis C0, Storage Account, Log Analytics, VNet) đều bị xóa sạch hoàn toàn khỏi hệ thống.
  * Chi phí phát sinh dừng lại ở mức $0.00 ngay tức khắc.
