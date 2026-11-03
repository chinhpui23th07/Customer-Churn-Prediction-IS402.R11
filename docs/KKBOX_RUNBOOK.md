# Chạy pipeline KKBox public-m12

## Trạng thái đã kiểm chứng ngày 03/11/2026

- Manifest `docs/experiments/kkbox_parquet_manifest.json` đọc footer của **32/32 file**, 7,522,254,856 byte, 442,211,685 dòng; revision nguồn `a0f48c28e392e9a60d4d6fc62f1bbf3d848277d3`.
- Nhãn chính thức: tháng 02 có 992,931 khách hàng (63,471 churn); tháng 03 có 970,960 khách hàng (87,330 churn). Không trùng khóa trong từng kỳ.
- Pilot tải **6/32 file, 885,659,602 byte**. PySpark chạy 1/1000 cohort: 1,000 snapshot tháng 02, 967 tháng 03; 12 feature, không trùng snapshot. Model/MLflow, Feast online SQLite, API và `/demo` đã được thử trên pilot. Đây chưa là kết quả xử lý >4 GB thực tế.
- `az account show` thấy subscription **Azure for Students** đang Enabled. Số dư credit, quota và báo giá theo region chưa xác nhận. Chưa tạo tài nguyên trả phí.

## Chạy pilot lại

Trong repo, dùng Python 3.11 và môi trường riêng. Trên Ubuntu/Linux, đặt `PYTHONPATH=.` và Java 17 hoặc 21 cho Spark. Môi trường Windows cần Hadoop native để đọc cây Parquet bằng Spark; pilot ở đây đã chạy trên Ubuntu WSL.

```sh
python scripts/inspect_kkbox_source.py
python scripts/download_kkbox.py --scope pilot --report docs/experiments/kkbox_pilot_download_report.json
python scripts/validate_kkbox_labels.py
PYTHONPATH=. python -m src.kkbox.run_etl --sample-modulus 1000 --shuffle-partitions 4 --output data/kkbox_processed/pilot_features --audit docs/experiments/kkbox_pilot_etl_audit.json
PYTHONPATH=. python -m src.kkbox.train --features data/kkbox_processed/pilot_features --etl-audit docs/experiments/kkbox_pilot_etl_audit.json --mode pilot --report docs/experiments/kkbox_pilot_model_report.json
PYTHONPATH=. python -m src.kkbox.prepare_feast --features data/kkbox_processed/pilot_features --report docs/experiments/kkbox_feast_pilot_report.json
```

Pilot model **không** được đăng ký alias `champion`. Để thử API cục bộ, đặt `KKBOX_ALLOW_PILOT=1` và `KKBOX_API_KEY` bằng secret riêng, sau đó chạy `uvicorn src.kkbox.api:app --host 127.0.0.1 --port 8000`. Trang demo ở `/demo`; không ghi API key vào source hoặc screenshot.

## Chạy toàn bộ trên Azure sau khi xác nhận chi phí

Giữ trần chi 50 USD và dự phòng 25 USD nếu số dư credit thực tế còn ít nhất 75 USD. Trước khi chạy, kiểm tra quota, giá VM/Blob/egress theo region, ghi thời gian dự kiến và đặt cảnh báo chi phí. Tắt/deallocate VM ngay sau phiên xử lý. Azure Budget chỉ cảnh báo, không phải khóa cứng.

```sh
python scripts/download_kkbox.py --scope full
PYTHONPATH=. python -m src.kkbox.run_etl --sample-modulus 1 --master 'local[4]' --driver-memory 4g --shuffle-partitions 32
PYTHONPATH=. python -m src.kkbox.train --mode full
PYTHONPATH=. python -m src.kkbox.prepare_feast
```

Lệnh ETL full từ chối chạy nếu thiếu bất kỳ file nào hoặc tổng byte không đúng manifest. Chỉ `--mode full` mới đăng ký model MLflow và gán alias `champion`. Các stage DVC tương ứng là `kkbox_download_full`, `kkbox_etl_full`, `kkbox_train_full`, `kkbox_feast_full`; pipeline Kaggle legacy vẫn còn trong cùng `dvc.yaml`, vì vậy gọi stage KKBox cụ thể khi chạy.

API full lấy model từ alias MLflow `KKBoxChurn@champion`, cùng ngưỡng dự đoán/rủi ro được gắn vào model version. Sau khi đổi alias để rollback, gọi `POST /v1/model/reload` với `x-api-key` để nạp phiên bản mới. Endpoint này không xuất hiện trong Swagger công khai.

Sau full run cần lưu: DVC lock/remote Azure Blob, SHA/byte của 32 file, số dòng trước/sau ETL, thời gian và cấu hình máy, metrics test tháng 03, phiên bản model, Feast online lookup, URL API/Web trên Azure, latency/đọc ghi, so sánh với local và chi phí thực tế. Không đưa Parquet nguồn hay bản ghi khách hàng vào GitHub.
