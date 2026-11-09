# Chốt hướng triển khai Customer Churn (03/11/2026)

Tài liệu này chốt một hướng triển khai chung cho cả dự án. Bản checkout đã đồng bộ tới `591225b`. Metadata nguồn và hai file nhãn đã được kiểm tra; pipeline KKBox toàn bộ chưa chạy.

## 1. Dataset, nhãn và khóa

| Hạng mục | Quyết định |
| --- | --- |
| Nguồn chuẩn | Hugging Face `vaibhavkhurana/subscriber-retention-intelligence`, release `public-m12` |
| Quy mô nguồn | 32 Parquet nén Zstandard, 7,522,254,856 byte (~7.52 GB), 442,211,685 dòng ở bốn bảng; số liệu do dataset card công bố, cần đo lại sau khi tải |
| Bốn bảng | `member`, `subscription_transaction`, `listening_day`, `churn_label` |
| Bài toán | Dự đoán khách hàng KKBox ngừng gia hạn thuê bao nhạc trong kỳ nhãn; không gọi là churn viễn thông |
| Khóa liên kết | `subscriber_key` là khóa giả danh 64 bit của bản phát hành công khai. Chuyển sang **chuỗi thập phân** khi đi qua JSON, JavaScript, API và Feast; không ép sang signed int64 hoặc JS Number |
| Nhãn | `is_churn` nhị phân: 1 = churn, 0 = tiếp tục; lấy từ `churn_label`, không tự tạo nhãn từ log/giao dịch |
| Khóa một quan sát huấn luyện | (`subscriber_key`, `label_period`); cùng một khách hàng có thể xuất hiện ở hai kỳ |
| Dữ liệu cũ | Bộ Kaggle CSV ~25 MB và notebook REES46 chỉ còn là tư liệu/đối chứng, không được trộn vào kết quả KKBox |

**Đã xác nhận:** schema/footer của 32 file tại revision `a0f48c28e392e9a60d4d6fc62f1bbf3d848277d3` trong [manifest](experiments/kkbox_parquet_manifest.json); hai kỳ nhãn có thống kê trong [label quality](experiments/kkbox_label_quality.json). Cột nguồn `label_window` mang giá trị `train`/`train_v2`, được ánh xạ sang tháng 02/03. `msno` là khóa KKBox gốc nhưng bản công khai dùng `subscriber_key`. Còn phải đo khóa trùng, null, phạm vi ngày và phân phối feature trên pilot của ba bảng còn lại.

## 2. Mốc thời gian và chống rò rỉ

| Vai trò | Kỳ nhãn | Feature chỉ dùng thông tin đã biết đến hết ngày | Dùng để làm gì |
| --- | --- | --- | --- |
| Fit và validation | 2017-02 | 2017-01-31 | Chia khách hàng theo hash cố định để fit/validation trong tháng 02 |
| Final test và demo replay | 2017-03 | 2017-02-28 | Đánh giá cuối cùng trên tháng 03; demo dự đoán lịch sử ở cutoff này |

- Chỉ dùng giao dịch có `transaction_date <= cutoff` và log có ngày nghe `<= cutoff`. Ngày hết hạn trong tương lai có thể dùng **nếu đã được ghi trong giao dịch trước cutoff**.
- Nhãn, ngày quan sát kết quả, gia hạn sau cutoff, sự kiện tương lai và ID không được đưa vào feature vector.
- Chia train/validation theo khóa khách hàng trong kỳ tháng 02; giữ nguyên tháng 03 làm tập kiểm thử cuối. Báo cáo rõ validation cùng cutoff, chỉ final test mới là kiểm định thời gian tiếp theo.
- API demo là **historical replay** ở một trong hai cutoff trên, không tuyên bố dự đoán thời gian thực năm 2026 từ dữ liệu lịch sử 2017.
- Tham khảo quy tắc nhãn gốc: khách hàng có hạn trong tháng nhãn; churn nếu không gia hạn hợp lệ hoặc lần gia hạn đầu tiên sau hạn ít nhất 30 ngày. Pipeline dùng nhãn phát hành sẵn, không tính lại quy tắc này.

## 3. Đầu ra cần làm

Một pipeline duy nhất: 4 bảng Parquet >4 GB → kiểm tra schema và ETL có log số dòng/byte/thời gian → feature snapshot theo cutoff → train/validation tháng 02 → test tháng 03 → đăng ký model MLflow → Feast phục vụ feature → FastAPI → Web → drift theo replay. DVC theo dõi manifest và các artifact dẫn xuất; nguồn thô lưu ngoài Git và theo điều khoản nguồn. Notebook REES46 không được dùng làm minh chứng cho pipeline churn này.

Hợp đồng feature: [feature_contract.md](../contracts/feature_contract.md). Hợp đồng API: [api_contract.md](../contracts/api_contract.md).

## 4. Trần chi phí Azure

**Chốt trần chi thực tế: 50 USD cho toàn bộ đồ án**, với điều kiện credit còn tối thiểu 75 USD như thông tin hiện có; giữ **25 USD dự phòng**. Nếu credit thực tế thấp hơn, trần giảm xuống `max(0, credit còn lại - 25 USD)`. Không xem 75 USD là số dư đã xác nhận.

- Ngày 1: 0 USD tài nguyên trả phí; chỉ kiểm tra credit, quota và báo giá theo region/SKU thực tế.
- Trước khi tạo tài nguyên: ước tính giá cho VM/thời gian chạy, Blob, egress, Container Apps/Redis; chỉ chạy pilot nếu dự kiến chi còn nằm trong trần.
- Đặt cảnh báo ở 20, 35 và 45 USD; ghi chi phí thực tế sau mỗi phiên chạy. Cảnh báo Azure không tự tắt tài nguyên; tự dừng và deallocate VM khi không dùng. Dừng mọi tác vụ trả phí trước khi chạm 50 USD.
- Không mặc định chọn Azure Cache for Redis trả phí nếu local/VM Redis đáp ứng demo và chi phí tốt hơn.

Ngày 03/11/2026, Azure CLI cho thấy subscription **Azure for Students** ở trạng thái Enabled; **chưa xác nhận số dư credit** và chưa tạo tài nguyên tính phí. Hướng dẫn chạy và bằng chứng pilot: [KKBOX_RUNBOOK.md](KKBOX_RUNBOOK.md).

## 5. Điều kiện công bố dữ liệu

Dataset card ghi license `other` và điều khoản của nhà cung cấp nguồn vẫn áp dụng. Bản phát hành công khai được chủ dataset nói đã được duyệt cho dự án của họ; câu này **không tự động cấp phép** cho việc nhóm mình tái phát hành bản sao. Không commit raw Parquet, khóa nguồn, sample dòng, hoặc upload dataset vào repo công khai. Báo cáo chỉ công bố thống kê tổng hợp, manifest và hình minh chứng đã kiểm tra quyền sử dụng.

Nguồn: [dataset card](https://huggingface.co/datasets/vaibhavkhurana/subscriber-retention-intelligence), [source contract](https://github.com/vaibhavkhuranaaa/subscriber-retention-intelligence/blob/main/docs/data-contract.md), [churn model](https://github.com/vaibhavkhuranaaa/subscriber-retention-intelligence/blob/main/docs/churn-model.md).
