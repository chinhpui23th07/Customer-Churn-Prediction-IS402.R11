# Khung nội dung báo cáo KKBox — chỉ điền số đo full

Tài liệu nguồn để soạn Word và slides theo mẫu KLTN của lớp. Các ô `[CẦN ĐO]` chưa có bằng chứng và **không được điền bằng metric pilot, REES46 hoặc Kaggle**. Danh mục ảnh/câu demo ở [kịch bản rubric](RUBRIC_DEMO_PLAN_2026-11-04.md).

## Tóm tắt

Đề tài xây dựng pipeline MLOps dự đoán khách hàng KKBox ngừng gia hạn thuê bao từ dữ liệu hành vi lịch sử. Nguồn Subscriber Retention Intelligence có bốn bảng Parquet, 32 file và tổng 7.522.254.856 byte theo manifest footer. Nhãn `is_churn` đã có trong dữ liệu nguồn. Pipeline tạo feature theo hai ngày chốt 31/01/2017 và 28/02/2017, huấn luyện/kiểm thử theo thời gian, quản lý version dữ liệu và model, sau đó cung cấp API/Web dự đoán. Kết quả xử lý toàn bộ dữ liệu, chất lượng model và chi phí Azure sẽ được bổ sung sau full run có audit và log.

## Chương 1. Bài toán và dữ liệu

**Bài toán:** phân loại nhị phân `is_churn` (1 = churn, 0 = tiếp tục) cho khách hàng dịch vụ thuê bao nhạc KKBox. Đây là churn thuê bao nội dung số, không phải churn viễn thông. API nhận `subscriber_key` dạng chuỗi và `as_of_date`; trả xác suất, nhãn dự đoán, mức rủi ro, phiên bản model/feature. Demo phát lại các mốc lịch sử 2017.

| Bảng nguồn | Vai trò | Số dòng theo footer | Byte theo footer |
| --- | --- | ---: | ---: |
| `member` | Thông tin thành viên | 6.769.473 | 60.491.935 |
| `subscription_transaction` | Lịch sử giao dịch | 22.975.416 | 463.554.548 |
| `listening_day` | Hành vi nghe theo ngày | 410.502.905 | 6.982.487.551 |
| `churn_label` | Nhãn hai kỳ | 1.963.891 | 15.720.822 |
| **Tổng** | 32 Parquet | **442.211.685** | **7.522.254.856** |

Số trên là **metadata nguồn**, không thay cho số file/byte Spark đã xử lý. Sau full run, thêm bảng kiểm tra SHA-256, byte, số dòng thực đọc và dẫn log. Nhãn tháng 02 có 992.931 khách hàng, 63.471 churn; tháng 03 có 970.960 khách hàng, 87.330 churn. Nêu nguồn revision `a0f48c28e392e9a60d4d6fc62f1bbf3d848277d3`.

## Chương 2. Cơ sở lý thuyết

1. **Lưu trữ:** Parquet dạng cột, schema/footer, Zstandard của nguồn; phân biệt object storage Blob và disk VM. DVC giữ metadata trong Git và object trong remote. Mô tả vì sao `subscriber_key` uint64 được gửi qua JSON dưới dạng chuỗi.
2. **Xử lý:** Spark đọc/join/tổng hợp theo khách hàng và cutoff; quy tắc loại sự kiện tương lai; Feast offline/online; Logistic Regression và XGBoost; PR-AUC, ROC-AUC, precision, recall, F1 và confusion matrix. Nêu PR-AUC cần đi cùng tỷ lệ churn nền.
3. **Vòng đời:** MLflow run/model version/alias `champion`; DVC stages; CI synthetic và full runner; drift tháng 02 → tháng 03 theo PSI/KS/missingness. Không gọi so sánh lịch sử là monitoring production liên tục.
4. **Cloud:** điền bảng resource thực tế sau khi cấp phát: VM/disk (IaaS), Blob (managed storage), GitHub Actions (SaaS). Các thư viện chạy trên VM không phải PaaS Azure. Không khai FaaS nếu không dùng.

## Chương 3. Thiết kế và hiện thực

**Sơ đồ cần đưa vào:** 4 Parquet → Blob/raw → Spark ETL trên VM → feature snapshots → train/MLflow/Feast → FastAPI → Web; GitHub Actions và DVC điều phối, drift kiểm tra kỳ sau.

| Kỳ | Cutoff feature | Vai trò | Quy tắc chống leakage |
| --- | --- | --- | --- |
| Tháng 02/2017 | 31/01/2017 | Fit và validation theo hash khách hàng | Giao dịch/nghe sau cutoff không vào feature |
| Tháng 03/2017 | 28/02/2017 | Final test và demo replay | Chỉ kiểm tra sau khi đã chọn model/threshold |

**Hợp đồng API:** trích [API contract](../contracts/api_contract.md); chụp request/response thực tế sau triển khai. Giao diện hiện tại ở `/demo` hiển thị trạng thái API, form ID/cutoff và kết quả model. Không đưa API key hoặc ID thật vào ảnh công khai.

## Chương 4. Thực nghiệm — chờ số đo thật

### 4.1 Cấu hình môi trường

| Môi trường | CPU | RAM | Disk | Region | Phiên bản Spark/Python | Commit/DVC |
| --- | ---: | ---: | --- | --- | --- | --- |
| Local | [CẦN ĐO] | [CẦN ĐO] | [CẦN ĐO] | Việt Nam | [CẦN GHI] | [CẦN GHI] |
| Azure | [CẦN ĐO] | [CẦN ĐO] | [CẦN ĐO] | [CẦN GHI] | [CẦN GHI] | [CẦN GHI] |

### 4.2 Dữ liệu >4 GB và ETL

| Chỉ số | Giá trị | Bằng chứng |
| --- | ---: | --- |
| File nguồn đã tải/đọc | [CẦN FULL RUN] | Download report + ETL audit |
| Byte nguồn đã đọc | [CẦN FULL RUN] | SHA/manifest + Spark log |
| Dòng đầu vào theo bảng | [CẦN FULL RUN] | Footer + Spark audit |
| Snapshot tháng 02/03 | [CẦN FULL RUN] | ETL audit |
| Thời gian ETL, peak RAM | [CẦN ĐO] | Runner/Spark log |

### 4.3 Tốc độ I/O, local-cloud và region

Đọc filesystem đo bằng `scripts/kkbox_benchmark_read.py` trên **cùng tập file**, ba lần, ghi cold/warm cache. Đo thời gian Spark ETL riêng. Đo Blob download/upload riêng; không cộng các chặng khác nhau vào một throughput. So local/cloud khi workload và cấu hình được công bố. `scripts/kkbox_latency_probe.py` đo cùng payload từ một client tới hai API cùng model version, ghi median/p95/p99 và lỗi.

| Phép đo | Local | Azure region 1 | Azure region 2 | Điều kiện so sánh |
| --- | ---: | ---: | ---: | --- |
| Đọc file MB/s | [CẦN ĐO] | [CẦN ĐO] | N/A | Cùng file, cache ghi rõ |
| ETL giây | [CẦN ĐO] | [CẦN ĐO] | N/A | Cùng cohort/input |
| API median/p95 ms | N/A | [CẦN ĐO] | [CẦN ĐO] | Cùng client/payload/model |
| Scan tối ưu trước/sau | [CẦN ĐO] | [CẦN ĐO] | N/A | Bytes scanned + thời gian |

### 4.4 Model full

| Model | Validation PR-AUC | Validation ROC-AUC | Ghi chú |
| --- | ---: | ---: | --- |
| Logistic Regression | [CẦN FULL RUN] | [CẦN FULL RUN] | |
| XGBoost | [CẦN FULL RUN] | [CẦN FULL RUN] | |

Model thắng được chọn bằng validation PR-AUC trước khi xem final test. Bảng test tháng 03 phải có prevalence, PR-AUC, ROC-AUC, precision, recall, F1, confusion matrix, threshold, model version và MLflow run ID. Hình so model/PR curve/confusion matrix/drift được tạo từ JSON full bằng `scripts/kkbox_make_figures.py`; script từ chối pilot theo mặc định.

### 4.5 Chi phí và quota

| Resource | Region/SKU | Thời gian/GB-tháng | Ước tính USD | Actual USD |
| --- | --- | ---: | ---: | ---: |
| VM + managed disk | [CẦN GHI] | [CẦN GHI] | [CẦN GHI] | [CẦN GHI] |
| Blob + giao dịch | [CẦN GHI] | [CẦN GHI] | [CẦN GHI] | [CẦN GHI] |
| Network/public IP | [CẦN GHI] | [CẦN GHI] | [CẦN GHI] | [CẦN GHI] |

Azure Budget chỉ cảnh báo; ghi actual cost từ Cost Analysis và thời điểm deallocate/xóa. Ảnh tài khoản/credit để riêng và che thông tin định danh trước khi đưa vào báo cáo.

## Chương 5. Kết luận và giới hạn

Chỉ viết kết luận định lượng sau khi đối chiếu full audit, model report, URL API/Web và actual cost. Nêu giới hạn: nguồn lịch sử 2017; chỉ hai kỳ nhãn; demo là historical replay; hai region latency phản ánh điều kiện mạng/client đo; drift lịch sử không thay cho giám sát production liên tục. Hướng phát triển có thể là dữ liệu kỳ mới, giám sát online và xác thực Web phù hợp trước khi mở công khai.

## Phụ lục và tài liệu tham khảo

- Gắn `evidence_id` cho từng hình/bảng, trỏ tới GitHub Actions run ID, MLflow run ID, DVC lock và report JSON.
- [Dataset card KKBox](https://huggingface.co/datasets/vaibhavkhurana/subscriber-retention-intelligence), [quyết định dữ liệu](KKBOX_DECISIONS_2026-11-03.md), [API contract](../contracts/api_contract.md), [kịch bản rubric](RUBRIC_DEMO_PLAN_2026-11-04.md).
- Các tài liệu dịch vụ/thuật toán phải trích từ trang chính thức tương ứng; ghi ngày truy cập trong bản Word.
