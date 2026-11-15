# HỢP ĐỒNG DỮ LIỆU CHUẨN (DATA CONTRACT SPECIFICATION) - KKBOX CUSTOMER CHURN

> **Mục tiêu nghiệm thu:** Đáp ứng tiêu chí tiên quyết của **Mốc Nghiệm Thu G0** (Deadline: 2026-11-03) theo [Phan_cong_MLOps_KKBox_Azure.xlsx](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/requirements/Phan_cong_MLOps_KKBox_Azure.xlsx) và [project_spec.md](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/requirements/project_spec.md).

---

## 1. Thông Tin Định Danh Dữ Liệu & Bài Toán
- **Tên dự án:** ChurnGuard MLOps - Customer Churn Prediction System.
- **Tập dữ liệu chuẩn:** KKBox Customer Churn Dataset (`vaibhavkhurana/subscriber-retention-intelligence`).
- **Nguồn phát hành:** Hugging Face Datasets (Dung lượng danh định: 7.52 GB / 7,522,254,856 bytes, gồm 32 tệp Parquet Snappy).
- **Thực thể định danh duy nhất (Entity Key):** `msno` (Kiểu chuỗi String UTF-8).
- **Nhãn mục tiêu (Target Label):** `is_churn` (Kiểu nhị phân `int32`: 0 = Tiếp tục sử dụng, 1 = Rời bỏ dịch vụ).
- **Khung thời gian Cutoff:** 2 kỳ nhãn `window=2017-02` và `window=2017-03`.

---

## 2. Đặc Tả Lược Đồ 4 Bảng Quan Hệ (Relational Schemas)

### 2.1. Bảng 1: `member` (Thông tin nhân khẩu học)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc (Constraints) | Ý Nghĩa Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `msno` | `STRING` | Primary Key, `NOT NULL` | Mã định danh người dùng KKBox |
| `city` | `INT32` | Optional (1..22) | Mã thành phố cư trú |
| `bd` | `INT32` | Range: [0, 100] (Lọc outlier) | Tuổi của thành viên |
| `gender` | `STRING` | Values: `'male'`, `'female'`, `NULL` | Giới tính |
| `registered_via` | `INT32` | Categorical | Kênh đăng ký dịch vụ |
| `registration_init_time` | `INT64` | Format: `YYYYMMDD` | Ngày bắt đầu mở tài khoản |

### 2.2. Bảng 2: `subscription_transaction` (Lịch sử giao dịch & gói cước)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Ý Nghĩa Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `msno` | `STRING` | Foreign Key, `NOT NULL` | Mã người dùng thực hiện giao dịch |
| `payment_method_id` | `INT32` | Categorical (1..41) | Phương thức thanh toán |
| `payment_plan_days` | `INT32` | Range: [0, 450] | Số ngày của gói cước |
| `plan_list_price` | `FLOAT64` | Non-negative ($\ge 0$) | Giá niêm yết của gói dịch vụ |
| `actual_amount_paid` | `FLOAT64` | Non-negative ($\ge 0$) | Số tiền thực tế khách hàng thanh toán |
| `is_auto_renew` | `INT32` | Binary: 0 hoặc 1 | Đăng ký tự động gia hạn cước |
| `transaction_date` | `INT64` | Format: `YYYYMMDD` | Ngày phát sinh giao dịch |
| `membership_expire_date`| `INT64` | Format: `YYYYMMDD` | Ngày hết hạn quyền thành viên |
| `is_cancel` | `INT32` | Binary: 0 hoặc 1 | Khách hàng chủ động hủy gói cước |

### 2.3. Bảng 3: `listening_day` (Nhật ký hành vi nghe nhạc theo ngày)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Ý Nghĩa Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `msno` | `STRING` | Foreign Key, `NOT NULL` | Mã người dùng nghe nhạc |
| `date` | `INT64` | Format: `YYYYMMDD` | Ngày ghi nhận nhật ký |
| `num_25` | `INT64` | Non-negative ($\ge 0$) | Số bài hát nghe dưới 25% độ dài |
| `num_50` | `INT64` | Non-negative ($\ge 0$) | Số bài hát nghe từ 25% đến 50% |
| `num_75` | `INT64` | Non-negative ($\ge 0$) | Số bài hát nghe từ 50% đến 75% |
| `num_985` | `INT64` | Non-negative ($\ge 0$) | Số bài hát nghe từ 75% đến 98.5% |
| `num_100` | `INT64` | Non-negative ($\ge 0$) | Số bài hát nghe trọn vẹn ($\ge 98.5%$) |
| `num_unq` | `INT64` | Non-negative ($\ge 0$) | Số lượng bài hát duy nhất đã nghe |
| `total_secs` | `FLOAT64` | Non-negative ($\ge 0$) | Tổng số giây nghe nhạc trong ngày |

### 2.4. Bảng 4: `churn_label` (Nhãn mục tiêu rời bỏ)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Ý Nghĩa Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| `msno` | `STRING` | Foreign Key, `NOT NULL` | Mã người dùng được gán nhãn |
| `is_churn` | `INT32` | Values: `0` hoặc `1` | Trạng thái rời bỏ dịch vụ trong kỳ cutoff |

---

## 3. SLA Chất Lượng Dữ Liệu & Quy Tắc Tiền Xử Lý (Data Quality SLA)
1. **Tính Toàn Vẹn Thực Thể (Entity Integrity):** `msno` tuyệt đối không được chứa giá trị `NULL`, rỗng hoặc ký tự khoảng trắng.
2. **Khử Outlier Tuổi (`bd`):** Các giá trị $bd < 10$ hoặc $bd > 90$ được chuẩn hóa thành `NULL` hoặc thay thế bằng trung vị (Median Imputation).
3. **Chống Rò Rỉ Dữ Liệu (Anti-Leakage):** Toàn bộ đặc trưng giao dịch và nghe nhạc được tổng hợp nghiêm ngặt trước ngày Cutoff của từng kỳ nhãn tương ứng.
4. **Nhất Quán Lưu Trữ (Storage Format):** 100% dữ liệu xuất ra lưu trữ tại `data/processed/` dưới định dạng **Apache Parquet nén Snappy**, xử lý out-of-core streaming giới hạn bộ nhớ chặt chẽ (Bounded Memory <= 2 GB).

---

## 4. Ánh Xạ Với Hợp Đồng Giao Diện API (FastAPI Schema Parity)
- Khế ước suy luận API tại [src/api/schemas.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/src/api/schemas.py) và [data/processed/openapi.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/data/processed/openapi.json) nhận đầu vào tương thích với 13 đặc trưng đã trích xuất từ 4 bảng trên.
- Endpoint phục vụ: `POST /predict`, `POST /predict/batch`, và `GET /predict/online/{customer_id}` tích hợp Feast Feature Store.
