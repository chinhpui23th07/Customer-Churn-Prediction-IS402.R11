# Feature contract v0.1 — KKBox public-m12

**Đơn vị một dòng:** (`subscriber_key`, `as_of_date`). `subscriber_key` là chuỗi số thập phân bảo toàn giá trị `uint64` của Parquet. `as_of_date` là ngày dạng `YYYY-MM-DD`, chỉ nhận `2017-01-31` hoặc `2017-02-28` trong bản demo. Feast online dùng entity nội bộ `snapshot_key = subscriber_key + "|" + as_of_date` để không ghi đè hai snapshot của cùng khách hàng; API vẫn chỉ nhận hai trường riêng. `snapshot_key` không vào model. `label_period` và `is_churn` chỉ xuất hiện trong bảng huấn luyện/đánh giá, không nằm trong Feast online features.

**Khóa join nguồn:** `subscriber_key` (`uint64` trong Parquet, Spark đọc thành `decimal(20,0)` và xuất chuỗi). Cột giao dịch là `transaction_date`, cột log là `activity_date`, cột member là `registration_month`; nguồn nhãn dùng `label_window=train` cho tháng 02 và `train_v2` cho tháng 03. Mọi phép tổng hợp log/giao dịch phải lọc ngày sự kiện `<= as_of_date` **trước** group/join. Các cửa sổ 30/90 ngày bao gồm cả ngày cutoff. Với một khách hàng và cutoff, phải có đúng một feature row.

| Feature output | Kiểu | Quy tắc | Khi không có lịch sử |
| --- | --- | --- | --- |
| `txn_count_30d` | integer >= 0 | Số giao dịch trong 30 ngày trước và gồm cutoff | 0 |
| `paid_amount_30d` | float >= 0 | Tổng tiền đã trả theo đơn vị tiền của nguồn trong 30 ngày; **không ghi USD** | 0 |
| `cancel_count_90d` | integer >= 0 | Số giao dịch hủy trong 90 ngày | 0 |
| `days_since_last_txn` | integer >= 0 hoặc null | Khoảng cách từ cutoff tới giao dịch gần nhất đã quan sát | null |
| `last_auto_renew` | 0/1 hoặc null | Trạng thái tự gia hạn của giao dịch gần nhất đã quan sát | null |
| `days_until_expiry` | integer hoặc null | Ngày hết hạn trừ cutoff của giao dịch gần nhất đã biết; có thể âm | null |
| `active_days_30d` | integer >= 0 | Số ngày có hoạt động nghe nhạc trong 30 ngày | 0 |
| `listening_secs_30d` | float >= 0 | Tổng thời gian nghe trong 30 ngày, sau xử lý giá trị âm/bất thường có log | 0 |
| `days_since_last_listen` | integer >= 0 hoặc null | Khoảng cách từ cutoff tới ngày nghe cuối đã quan sát | null |
| `registration_tenure_days` | integer >= 0 hoặc null | Số ngày từ **tháng đăng ký** tới cutoff; độ chính xác theo tháng, ghi rõ xấp xỉ | null |
| `has_txn_history` | 0/1 | Có ít nhất một giao dịch trước cutoff | 0 |
| `has_listening_history` | 0/1 | Có ít nhất một ngày nghe trước cutoff | 0 |

Giao dịch cuối sắp theo `transaction_date DESC, event_key DESC` để tie-break ổn định. Model chỉ dùng 12 feature trên theo thứ tự cố định. Imputation và chuẩn hóa phải fit trên tập train tháng 02, lưu cùng model và dùng y hệt lúc serving. Có thể điều chỉnh danh sách sau pilot nếu kiểm tra chất lượng cho thấy cần thiết, nhưng phải version hợp đồng và kiểm tra lại train/serve parity.

**Cấm dùng làm feature:** `subscriber_key`, `is_churn`, `label_period`, thời điểm kết quả, giao dịch/log sau cutoff, thống kê tính bằng cả tháng nhãn, `age_band_start`, `gender`, `city_code` trong baseline. Nhân khẩu học có thể dùng cho phân tích bias tổng hợp riêng.

**Kiểm tra bắt buộc:** schema nguồn, số dòng trước/sau từng lọc, trùng (`subscriber_key`, `as_of_date`), số feature null, min/max ngày nguồn của mỗi snapshot, và phép kiểm tra `max(event_date) <= as_of_date`. Không chạy toàn bộ dữ liệu qua Pandas trong một lần.
