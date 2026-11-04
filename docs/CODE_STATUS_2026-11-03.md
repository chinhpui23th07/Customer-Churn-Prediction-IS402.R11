# Code hiện tại so với mục tiêu KKBox (03/11/2026)

Checkout local đã đồng bộ lên GitHub `master` `591225b`. Bảng dưới mô tả pipeline **legacy Kaggle** trước khi các module KKBox mới được tích hợp; chưa chạy lại training, API hoặc Azure trong phiên này.

| Phần | Đã có trong code | Còn thiếu để đạt mục tiêu mới |
| --- | --- | --- |
| Dữ liệu/DVC | `src/data/download_dataset.py` tải hai CSV Kaggle; `dvc.yaml` nối download → preprocess → quality → Feast → train → evaluate/drift | Thay nguồn bằng 4 bảng KKBox Parquet 7.52 GB; DVC/Blob manifest và bằng chứng chạy >4 GB chưa có |
| ETL | `src/data/preprocess.py` làm sạch CSV bằng Pandas, tạo split ngẫu nhiên; có metadata/báo cáo | ETL phân tán hoặc đọc theo partition, join theo `subscriber_key`, cutoff Feb/Mar và kiểm tra leakage |
| Feast | `src/features/feature_store.py` định nghĩa FeatureView cho 13 feature Kaggle; offline Parquet, online SQLite; Redis là cache tùy chọn | FeatureView KKBox theo contract, snapshot theo cutoff, historical retrieval và materialize đúng thời điểm; nếu dùng Redis làm online store thì phải cấu hình Feast thật |
| Model/MLflow | `src/models/train_pipeline.py` có LR/RF/XGBoost/LightGBM, metrics, MLflow; file báo cáo hiện chọn XGBoost ROC-AUC 0.9989 trên bộ cũ | Huấn luyện lại hoàn toàn trên KKBox; temporal test tháng 03; kiểm tra leakage, model registry alias `champion` và deployment gate |
| API/Web | FastAPI có `/predict`, `/predict/customer/{customer_id}`, batch, health; `src/web/app.js` gọi API | Chuyển schema sang ID chuỗi 64 bit + cutoff và 12 feature mới; nối model/Feast KKBox; triển khai và chứng minh URL Azure thật |
| Drift | Có `src/monitoring/drift_detector.py` và report | Replay theo hai kỳ KKBox, feature distribution thật; không gọi là performance drift khi chưa có ground truth |
| CI/CD/Azure | Có workflow, Dockerfile, Terraform/ARM/deploy script | Chứng minh self-hosted runner và cloud deploy thực tế. Workflow local có nhãn self-hosted, nhưng GitHub `master` mới nhất đã đổi `mlops_ci.yml` sang `ubuntu-latest`. CD chỉ build/smoke Docker, chưa chạy `az` deploy. Cần chọn lại runner theo rubric sau đồng bộ |

**Điểm dễ gây hiểu nhầm:** báo cáo XGBoost 0.9989, ảnh, MLflow artifacts và API hiện tại đều thuộc dữ liệu Kaggle cũ. Notebook REES46 đo I/O của dữ liệu khác; không chứng minh pipeline đầu ra Customer Churn >4 GB. Đặc tả trên GitHub hiện ghi Snappy và `msno` chuỗi cho bản HF, trái dataset card (Zstandard, khóa giả danh 64 bit); cần sửa sau khi kiểm tra schema mẫu.

**Thứ tự làm tiếp sau pilot:** (1) xác nhận credit/quota và báo giá Azure; (2) cấu hình DVC remote/Redis phù hợp ngân sách; (3) tải và chạy đủ 32 file trên Azure; (4) triển khai API/Web và lưu latency, đọc ghi, chi phí, model metrics làm bằng chứng. Không tính việc có file cấu hình là đã triển khai thành công.

## Cập nhật sau pilot ngày 03/11/2026

- Đã đồng bộ GitHub; kiểm tra footer/schema cả 32 file, tổng 7,522,254,856 byte và 442,211,685 dòng tại revision `a0f48c28e392e9a60d4d6fc62f1bbf3d848277d3`.
- Đã tải 6 file thật với 885,659,602 byte để pilot. Hai file nhãn có 1,963,891 dòng, khóa mỗi kỳ không trùng, nhãn chỉ 0/1.
- PySpark ETL pilot xử lý 1/1000 cohort nhãn, ghi 1.000 snapshot tháng 02 và 967 tháng 03; mất 124,616 giây trên Ubuntu WSL. Dữ liệu pilot thiếu một phần giao dịch và lịch sử log, không dùng để kết luận model quality.
- Đã train Logistic Regression và XGBoost, log vào MLflow; model pilot được chọn theo validation PR-AUC. Feast online SQLite ghi 1.967 snapshot và truy vấn đủ 12 feature.
- FastAPI và `/demo` đã qua HTTP smoke: dự đoán 200, không có ID 404, thiếu API key 401, sai schema 422. Điểm số khi lấy feature từ Parquet và Feast giống nhau trên cùng snapshot.
- **Chưa hoàn thành:** tải và chạy đủ 32 file trên Azure, DVC remote Azure thực sự, Redis online store, model full/registry alias, batch API, drift, cloud deploy, self-hosted runner và kiểm chứng chi phí thực tế.

Xem các file trong `docs/experiments/` để đối chiếu số liệu; không dùng ROC-AUC 0.9989 của Kaggle cũ hay metric pilot làm kết quả KKBox cuối.

## Cập nhật tại máy ngày 04/11/2026

- Đã xác định test Spark lần trước bị chặn socket loopback Python ↔ JVM trong sandbox (`WinError 10013`). Chạy Windows test với quyền phù hợp đã pass; đây không phải lỗi cutoff. Chưa chạy lại ETL pilot.
- ETL giờ xác nhận từng đường dẫn, byte, số dòng và schema Parquet theo manifest trước khi chạy; 6 file pilot khớp. Report tải dữ liệu ghi SHA-256 cho file đã có.
- Đã thêm drift replay tháng 02 → tháng 03 và stage DVC `kkbox_drift_full`. Report pilot chỉ là smoke test trên lịch sử nguồn thiếu, không dùng kết luận cuối.
- Đã thêm workflow CI riêng cho KKBox, workflow full chỉ kích hoạt thủ công trên runner có label `kkbox`, bộ dependency pin trong `requirements-kkbox.txt`, và kiểm tra cục bộ đường MLflow Registry alias `champion`. Chưa có self-hosted runner hoặc deployment Azure thực tế.
- Theo yêu cầu chủ dự án, dừng trước mọi thao tác với Azure. Credit/quota/giá chưa kiểm tra trong phiên này.
