# Chạy pipeline KKBox public-m12

## Trạng thái đã kiểm chứng ngày 03/11/2026

- Manifest `docs/experiments/kkbox_parquet_manifest.json` đọc footer của **32/32 file**, 7,522,254,856 byte, 442,211,685 dòng; revision nguồn `a0f48c28e392e9a60d4d6fc62f1bbf3d848277d3`.
- Nhãn chính thức: tháng 02 có 992,931 khách hàng (63,471 churn); tháng 03 có 970,960 khách hàng (87,330 churn). Không trùng khóa trong từng kỳ.
- Pilot tải **6/32 file, 885,659,602 byte**. PySpark chạy 1/1000 cohort: 1,000 snapshot tháng 02, 967 tháng 03; 12 feature, không trùng snapshot. Model/MLflow, Feast online SQLite, API và `/demo` đã được thử trên pilot. Đây chưa là kết quả xử lý >4 GB thực tế.
- `az account show` thấy subscription **Azure for Students** đang Enabled. Ngày 04/11 đã có ảnh số dư credit và tra giá niêm yết Southeast Asia; quota Compute/SKU chưa xác nhận. Chưa tạo tài nguyên trả phí. Xem [kịch bản rubric và bằng chứng](RUBRIC_DEMO_PLAN_2026-11-04.md).

## Chạy pilot lại

Trong repo, dùng Python 3.11 và môi trường riêng. Trên Ubuntu/Linux, đặt `PYTHONPATH=.` và Java 17 hoặc 21 cho Spark. Môi trường Windows cần Hadoop native để đọc cây Parquet bằng Spark; pilot ở đây đã chạy trên Ubuntu WSL.

```sh
python scripts/inspect_kkbox_source.py
python scripts/download_kkbox.py --scope pilot --report docs/experiments/kkbox_pilot_download_report.json
python scripts/validate_kkbox_labels.py
PYTHONPATH=. python -m src.kkbox.run_etl --sample-modulus 1000 --shuffle-partitions 4 --output data/kkbox_processed/pilot_features --audit docs/experiments/kkbox_pilot_etl_audit.json
PYTHONPATH=. python -m src.kkbox.train --features data/kkbox_processed/pilot_features --etl-audit docs/experiments/kkbox_pilot_etl_audit.json --mode pilot --report docs/experiments/kkbox_pilot_model_report.json
PYTHONPATH=. python -m src.kkbox.prepare_feast --features data/kkbox_processed/pilot_features --report docs/experiments/kkbox_feast_pilot_report.json

PYTHONPATH=. python -m src.kkbox.drift --features data/kkbox_processed/pilot_features --audit docs/experiments/kkbox_pilot_etl_audit.json --report docs/experiments/kkbox_pilot_drift_report.json
```

Pilot model **không** được đăng ký alias `champion`. Để thử API cục bộ, đặt `KKBOX_ALLOW_PILOT=1` và `KKBOX_API_KEY` bằng secret riêng, sau đó chạy `uvicorn src.kkbox.api:app --host 127.0.0.1 --port 8000`. Trang demo ở `/demo`; không ghi API key vào source hoặc screenshot.

Trên Windows, chạy `powershell -File scripts/run_kkbox_tests.ps1` để kiểm tra KKBox. Script tự dùng JDK từ `java.exe` đang chạy (tránh `JAVA_HOME` cũ trỏ tới thư mục không tồn tại), đặt Python venv và loopback cho Spark. `-SkipSpark` chỉ chạy API, integrity, figure và Web. Nếu sandbox chặn socket loopback, test Spark cần chạy trong terminal Windows có quyền cho Python/JVM giao tiếp nội bộ; pilot ETL đọc Parquet thực vẫn nên chạy trên Linux/WSL.

Giao diện KKBox mới là `/demo` của `src.kkbox.api`, tải CSS/JS từ `/demo/assets/`. Giao diện ChurnGuard ở `src/web/` và Dockerfile gốc thuộc pipeline Kaggle cũ, không dùng làm ảnh/chứng cứ KKBox. Trang demo có ô nhập API key chỉ dành cho demo nội bộ; trước khi mở công khai cần chốt cơ chế xác thực phù hợp, không đưa khóa cố định vào JavaScript.

Để tìm một ID có snapshot cho demo local, chạy `python scripts/kkbox_pick_demo_key.py --cutoff 2017-02-28` trên máy giữ dữ liệu pilot. Khi đã có full feature, thêm `--features data/kkbox_processed/features`. Chỉ dùng kết quả trong demo riêng, không commit khóa hoặc ảnh chụp hiển thị khóa. Để xem thử bố cục các hình báo cáo từ pilot, chạy `python scripts/kkbox_make_figures.py --etl-audit docs/experiments/kkbox_pilot_etl_audit.json --model-report docs/experiments/kkbox_pilot_model_report.json --drift-report docs/experiments/kkbox_pilot_drift_report.json --output-dir scratch/kkbox_figures_preview --allow-pilot`; hình có watermark và không phải bằng chứng cuối. Full train mới sẽ ghi điểm PR curve vào model report.

## Chạy toàn bộ trên Azure sau khi xác nhận chi phí

Giữ trần chi 50 USD và dự phòng 25 USD **chỉ khi số dư credit thực tế còn ít nhất 75 USD**. Ảnh ngày 04/11 cho thấy điều kiện này chưa đạt; dừng trước khi tạo tài nguyên trả phí cho tới khi chủ dự án quyết định lại hoặc số dư tăng. Trước khi chạy, kiểm tra quota, giá VM/Blob/egress theo region, ghi thời gian dự kiến và đặt cảnh báo chi phí. Tắt/deallocate VM ngay sau phiên xử lý. Azure Budget chỉ cảnh báo, không phải khóa cứng.

```sh
python scripts/download_kkbox.py --scope full
PYTHONPATH=. python -m src.kkbox.run_etl --sample-modulus 1 --master 'local[4]' --driver-memory 4g --shuffle-partitions 32
PYTHONPATH=. python -m src.kkbox.train --mode full
PYTHONPATH=. python -m src.kkbox.prepare_feast

PYTHONPATH=. python -m src.kkbox.drift --require-full
```

Lệnh ETL full từ chối chạy nếu thiếu file hoặc đường dẫn/byte/số dòng/schema không khớp manifest. Chỉ `--mode full` mới đăng ký model MLflow và gán alias `champion`. Các stage DVC tương ứng là `kkbox_download_full`, `kkbox_etl_full`, `kkbox_train_full`, `kkbox_feast_full`, `kkbox_drift_full`; pipeline Kaggle legacy vẫn còn trong cùng `dvc.yaml`, vì vậy gọi stage KKBox cụ thể khi chạy.

API full lấy model từ alias MLflow `KKBoxChurn@champion`, cùng ngưỡng dự đoán/rủi ro được gắn vào model version. Sau khi đổi alias để rollback, gọi `POST /v1/model/reload` với `x-api-key` để nạp phiên bản mới. Endpoint này không xuất hiện trong Swagger công khai.

Sau full run cần lưu: DVC lock/remote Azure Blob, SHA/byte của 32 file, số dòng trước/sau ETL, thời gian và cấu hình máy, metrics test tháng 03, phiên bản model, Feast online lookup, URL API/Web trên Azure, latency/đọc ghi, so sánh với local và chi phí thực tế. Không đưa Parquet nguồn hay bản ghi khách hàng vào GitHub.

## Kiểm tra mã tại máy ngày 04/11/2026

- `verify_source` so từng đường dẫn, byte, số dòng và schema footer Parquet với manifest trước khi tạo Spark session; pilot 6 file hiện khớp. `download_kkbox.py` ghi SHA-256 cho cả file mới tải và file đã có.
- `src/kkbox/drift.py` so sánh 12 feature ở tháng 02 và 03 bằng PSI, KS và tỷ lệ thiếu. Báo cáo pilot ở `docs/experiments/kkbox_pilot_drift_report.json` chỉ kiểm tra đường chạy; không suy ra drift production hay chất lượng model.
- `.github/workflows/kkbox_ci.yml` chạy test KKBox và kiểm tra DAG DVC trên GitHub Actions khi push nhánh feature hoặc mở PR. Workflow này dùng dữ liệu tổng hợp trong test, không tải dataset.
- `.github/workflows/kkbox_full_runner.yml` chỉ chạy khi chủ dự án chọn `execute_full=true` bằng tay và có runner Linux mang label `kkbox`; mặc định không chạy. Runner cần ít nhất 30 GiB trống. Workflow dùng `requirements-kkbox.txt`, chạy DVC full và chỉ upload báo cáo tổng hợp cùng `dvc.lock`; chưa có runner thật hoặc bằng chứng chạy full.
- Test Spark trên Windows cần Java 17 và socket loopback Python ↔ JVM. Sandbox của phiên làm việc chặn socket với `WinError 10013`; chạy test với quyền phù hợp đã pass trong 36,83 giây. Windows Spark vẫn cần Hadoop native để đọc cây Parquet thực; ETL pilot đã chạy trên Ubuntu WSL.
- Trước mọi thay đổi Azure, dừng để chủ dự án quyết định. Credit đã có ảnh do chủ dự án cung cấp; giá niêm yết Southeast Asia đã tra; quota Compute/SKU và self-hosted runner Azure chưa xác minh trong ngày 04/11.
