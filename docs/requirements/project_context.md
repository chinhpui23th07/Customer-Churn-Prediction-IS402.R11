# ĐẶC TẢ NGỮ CẢNH DỰ ÁN & BỘ BIẾN SỐ ĐỘNG (PROJECT CONTEXT SPECIFICATION)

> **Mục đích:** Tệp cấu hình đặc tả trung tâm lưu trữ toàn bộ các thông tin động, biến số thực nghiệm, metadata tác giả, bộ dữ liệu và tiêu chí đánh giá của dự án. Tầng quy chuẩn quản trị (`AGENTS.md` và `.agents/rules/`) giữ nguyên tắc phổ quát, độc lập và đọc các thông số từ tệp này để tránh ghép cặp cứng (Decoupled Governance Architecture).

---

## 1. Thông Tin Định Danh Học Thuật & Tác Giả
- **Cơ sở đào tạo:** Trường Đại học Công nghệ Thông tin - ĐHQG-HCM (UIT).
- **Khoa:** Hệ thống Thông tin | **Bộ môn:** Mạng và Hệ thống Thông tin.
- **Môn học:** Điện toán Đám mây (Cloud Computing) - **Mã môn:** IS402.
- **Giảng viên hướng dẫn:** ThS. Hà Lê Hoài Trung.
- **Sinh viên thực hiện:** Nguyễn Trọng Khôi.
- **Mã số sinh viên (MSSV):** 23520783 (Khóa 2023 - 2027, Lớp IS402).
- **Tên đề tài chính thức:** Đề tài 11 - MLOps: Xây dựng hệ thống dự đoán khách hàng rời bỏ dịch vụ (Customer Churn Prediction) kết hợp nền tảng Microsoft Azure.

---

## 2. Đặc Tả Bộ Dữ Liệu Thực Nghiệm (Canonical Dataset Specifications)
- **Tên bộ dữ liệu chuẩn:** KKBox Customer Churn Dataset (HuggingFace `vaibhavkhurana/subscriber-retention-intelligence`).
- **Quy mô danh định:** 7.52 GB (32 tệp Parquet Snappy).
- **Cấu trúc 4 bảng quan hệ:**
  1. `member`: Thông tin nhân khẩu học của thành viên (`msno`, `city`, `bd`, `gender`, `registered_via`, `registration_init_time`).
  2. `subscription_transaction`: Lịch sử giao dịch gói dịch vụ (`msno`, `payment_method_id`, `payment_plan_days`, `plan_list_price`, `actual_amount_paid`, `is_auto_renew`, `transaction_date`, `membership_expire_date`, `is_cancel`).
  3. `listening_day`: Nhật ký nghe nhạc theo ngày (`msno`, `date`, `num_25`, `num_50`, `num_75`, `num_985`, `num_100`, `num_unq`, `total_secs`).
  4. `churn_label`: Nhãn mục tiêu rời bỏ dịch vụ (`msno`, `is_churn`).
- **Thực thể định danh duy nhất (Entity Key):** `msno` (chuỗi ký tự).
- **Nhãn mục tiêu (Target Label):** `is_churn` (nhị phân: 0 hoặc 1).
- **Nguyên tắc nhất quán:** 100% các thành phần trong hệ thống (ETL, Storage, Feature Store Feast, Model Training, FastAPI Serving, Web UI) bắt buộc phải dùng chung thực thể `msno` và nhãn `is_churn`.

---

## 3. Kiến Trúc Hạ Tầng Đám Mây & FinOps
- **Nhà cung cấp đám mây:** Microsoft Azure (Khu vực Southeast Asia).
- **Dịch vụ tích hợp:** Azure Container Apps, Azure Blob Storage, Azure Cache for Redis (Port 6380 SSL).
- **Lưu trữ cục bộ:** Parquet Snappy Offline Store & SQLite WAL Online Store (`online_store.db`).
- **Ngân sách FinOps:** TCO $74.67/tháng.

---

## 4. Danh Mục Tài Liệu Nghiên Cứu & Đối Chuẩn (Literature & Repositories)
- **Danh mục kho lưu trữ đối chuẩn:** 27 GitHub Repositories lưu tại `docs/research/repos/` (bao gồm `aio2025-mlops-project01`, `Gees14_feast_drift`, `Oyebamiji_Micheal_dvc_mlflow`, `HinnoNguyen_IS402`...).
- **Danh mục bài báo khoa học:** 14 bài báo lý thuyết lưu tại `docs/research/papers/` (bao gồm Kreuzberger 2022 MLOps Review, Lundberg 2017 SHAP, Rabanser 2019 Dataset Shift...).
- **Bảng tổng hợp chi tiết:** `docs/requirements/grounding_catalog.md`.

---

## 5. Tiêu Chuẩn Rubric & Cơ Chế Đánh Giá
- **Bảng phân công & Rubric gốc:** `docs/requirements/Phan_cong_MLOps_KKBox_Azure.xlsx`.
- **Cơ chế đánh giá Dual-Track:**
  * **Trạng thái thực tế cục bộ (Local Real Execution State):** Đánh giá trung thực năng lực chạy trên máy trạm cục bộ, ghi nhận chính xác các hạng mục cần live cloud subscription để đạt trọn điểm.
  * **Trạng thái mục tiêu đám mây (Target Cloud SLA State):** Đạt trọn vẹn khi hệ thống được provision sống trên Microsoft Azure.

---

## 6. Danh Mục Tệp Sản Phẩm Đầu Ra (Deliverables)
- **Báo cáo thuyết minh (Word):** `docs/Bao_Cao_Bai_Tap_Lon_MLOps_Customer_Churn.docx`
- **Báo cáo PDF chính thức:** `docs/Bao_Cao_Bai_Tap_Lon_MLOps_Customer_Churn.pdf`
- **Slide báo cáo (PowerPoint):** `docs/Slide_Thuyet_Trinh_MLOps_Customer_Churn.pptx`
- **Giao diện Web:** `src/web/index.html` (Bento Grid)
- **Tệp nộp bài chuẩn UIT:** `23520783_BTL_Cloud_Computing_MLOps.zip`
