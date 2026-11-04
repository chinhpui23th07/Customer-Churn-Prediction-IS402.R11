# Bàn giao phần chuẩn bị local trước khi chạy Azure

Ngày kiểm tra: 04/11/2026. Tài liệu này mô tả **mã và kiểm tra local**, không phải bằng chứng full run trên Azure. Xem [kịch bản rubric](RUBRIC_DEMO_PLAN_2026-11-04.md) để biết ảnh/số liệu phải lấy sau mỗi bước cloud.

## Những phần đã chuẩn bị

| Hạng mục | Đầu ra local | Trạng thái |
| --- | --- | --- |
| Dataset contract | Manifest footer 32/32 file, 7.522.254.856 byte, hai kỳ nhãn có sẵn | Metadata nguồn, chưa xử lý full |
| Pipeline KKBox | Spark ETL, train/MLflow, Feast, API, DVC stages, drift | Pilot 6/32 file đã chạy; chưa full |
| Giao diện | `src/kkbox/web/index.html`, `style.css`, `app.js`, `favicon.svg` tại `/demo` | Local pilot đã thử HTTP 200 và 404 |
| Ảnh phân tích | `scripts/kkbox_make_figures.py`: so validation model, confusion matrix test, PR curve, drift PSI; stage `kkbox_figures_full` | Xem thử pilot có watermark; full bị chặn tới khi có report đủ 32 file |
| Demo ID | `scripts/kkbox_pick_demo_key.py` chọn một khóa từ feature snapshot local | Chạy được; không đưa khóa vào Git hoặc ảnh công khai |
| Test Windows | `scripts/run_kkbox_tests.ps1` dùng JDK thật và Python venv để tránh `JAVA_HOME` lỗi | Spark test riêng pass |
| Đo thực nghiệm | `scripts/kkbox_benchmark_read.py` đọc đúng file trong manifest và `scripts/kkbox_latency_probe.py` đo cùng payload tới nhiều endpoint | Đã viết và test logic local; chưa có số đo cloud/region |
| Runner tương lai | `requirements-kkbox-azure.txt` thêm DVC Azure extra; full workflow tạo hình và lưu artifact | Chưa có runner/cloud run |

## Kết quả kiểm tra cục bộ

- `node --check src/kkbox/web/app.js`: pass.
- Python `py_compile` cho API và bộ tạo hình: pass.
- Script test đầy đủ gồm API, integrity, figure gate, benchmark, Web và Spark cutoff: **10 passed trong 62,66 giây** khi dùng JDK 17 đúng đường dẫn và loopback.
- `dvc dag kkbox_figures_full`: pass; DAG nguồn → ETL → model/drift → figure.
- Bộ tạo hình pilot xuất bốn SVG vào `scratch/kkbox_figures_preview/`, có watermark; cả bốn parse được dưới dạng SVG hợp lệ. Pilot report cũ chưa có PR curve nên hình đó chỉ hiện thông báo. Code full train mới lưu điểm PR curve thật; đường tạo SVG với dữ liệu synthetic đã được kiểm tra, nhưng train full chưa chạy. Không dùng ảnh pilot làm kết quả cuối.
- Local FastAPI: `/demo`, `/demo/assets/style.css`, `/demo/assets/app.js`, `/health` đều HTTP 200. Trình duyệt tại kích thước hẹp hiển thị đúng bố cục; nhập ID không có snapshot hiện lỗi rõ ràng, ID có snapshot pilot hiển thị xác suất/rủi ro/cutoff/model/feature version. Đây là smoke test giao diện, không công bố metric pilot.
- Benchmark đọc smoke 1 file/7.948.492 byte ghi `complete_source=false`. Probe latency smoke với API localhost có 3/3 request thành công sau warm-up; chỉ xác nhận script hoạt động, **không** là so sánh hai region hoặc kết quả hiệu năng cloud.
- Lệnh DVC trong sandbox Windows báo access denied với `C:\ProgramData\iterative`; chạy trong terminal được cấp quyền thì DAG pass. Java `java.exe` thực ở Microsoft JDK 17, nhưng `JAVA_HOME` ban đầu trỏ đến một thư mục Adoptium không tồn tại. Script test mới tự sửa biến môi trường cho phiên chạy.

## Việc còn lại không được gọi là hoàn thành

- Chưa có 32 Parquet tải và xử lý trên Azure; chưa có report full, model registry `champion` full, DVC Blob remote, runner thật, API/Web URL cloud, benchmark I/O/region hay chi phí thực tế.
- Script `kkbox_benchmark_read.py` chỉ đo đọc **filesystem**, không chứng minh Spark ETL hoặc tốc độ Blob. Script latency chỉ tạo so sánh region hợp lệ khi hai endpoint trả cùng model/prediction và cùng client; chưa thể dùng trước khi có triển khai.
- Dockerfile và giao diện ChurnGuard cũ ở `src/web/` vẫn là pipeline Kaggle; **không dùng** để chụp minh chứng KKBox. Tài liệu triển khai cũ trong `deploy/azure/` cũng mô tả kiến trúc legacy, không chạy cho KKBox.
- Ô API key trong giao diện mới chỉ phù hợp demo nội bộ; trước khi mở Internet cần chốt bảo vệ endpoint và HTTPS, không nhúng key cố định vào JavaScript.
- Word/PPT và ảnh rubric cuối chưa tạo vì phải lấy kết quả full thật. Mọi hình pilot chỉ để kiểm tra bố cục.

## Các lệnh local để tái kiểm tra

```powershell
Set-Location D:\Project_CLoud\Customer-Churn-Prediction-IS402.R11
powershell -File scripts/run_kkbox_tests.ps1
node --check src/kkbox/web/app.js
.\.venv\Scripts\python.exe scripts/kkbox_pick_demo_key.py --cutoff 2017-02-28
```

Để mở Web pilot local, đặt `KKBOX_ALLOW_PILOT=1` và `KKBOX_API_KEY` bằng mã chỉ dùng tại máy, rồi chạy `uvicorn src.kkbox.api:app --host 127.0.0.1 --port 8000`; mở `http://127.0.0.1:8000/demo`. Không lưu/chia sẻ API key hoặc subscriber key trong tài liệu công khai.

## Ranh giới Azure

Ảnh riêng của chủ dự án cho thấy credit **dưới 75 USD**, chưa đạt điều kiện đã chốt trước khi tạo tài nguyên trả phí. Đã đọc giá niêm yết Southeast Asia và trạng thái provider; quota Compute/SKU chưa xác nhận. Không đăng ký provider, tạo budget/resource, chạy job, hay triển khai Azure trong phần chuẩn bị này. Chat tiếp theo cần chờ **quyết định mới của chủ dự án** trước mọi thay đổi Azure.
