# Hướng Dẫn Thực Nghiệm Big Data Cloud Benchmark (>4GB)

> **Phân hệ:** Big Data Out-of-Core Processing & I/O Benchmark  
> **Quy mô dữ liệu:** 5.28 GB / 42,448,764 bản ghi thương mại điện tử thực tế  
> **Mục tiêu kỹ thuật:** Đo đạc và đối chuẩn hiệu năng I/O (Throughput, RAM peak, thời gian xử lý) giữa CSV tuần tự và Parquet Snappy phân tích  

---

## 1. Mục Tiêu & Cơ Sở Khoa Học Của Thực Nghiệm Quy Mô Lớn (>4GB Scalability Benchmark)

Nhằm chứng minh năng lực mở rộng (Scalability) và tối ưu hóa tài nguyên phần cứng của hệ thống xử lý dữ liệu lớn, thực nghiệm đo đạc và đối sánh tốc độ đọc/ghi, dung lượng lưu trữ và mức tiêu thụ bộ nhớ RAM trên tập dữ liệu quy mô vượt ngưỡng 4GB.

Thay vì sinh dữ liệu giả tạo (synthetic data), thực nghiệm sử dụng tập dữ liệu hành vi người dùng thực tế quy mô lớn từ Kaggle:
- **Tên tập dữ liệu:** [eCommerce behavior data from multi category store (REES46)](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store)
- **Tệp thực nghiệm:** `2019-Oct.csv`
- **Dung lượng thô:** **5.28 GB** (vượt chuẩn > 4GB)
- **Số lượng bản ghi thực tế:** **42,448,764 dòng** hành vi người dùng (view, cart, purchase, price, user_id, category).

---

## 2. Cấu Trúc Thư Mục Notebooks

```
notebooks/
├── rees46_bigdata_cloud_benchmark.ipynb   # Jupyter Notebook kiểm chuẩn Out-of-Core DuckDB sang Parquet Snappy
├── kernel-metadata.json                  # Metadata đẩy notebook trực tiếp lên Kaggle qua CLI
└── README.md                             # Hướng dẫn chi tiết quy trình thực thi
```

---

## 3. Quy Trình Chạy Thực Nghiệm Trên Kaggle Cloud Engine

Do máy tính cá nhân bị giới hạn băng thông mạng và RAM khi tải file 5.28 GB, thực nghiệm được thiết kế để chạy trực tiếp trên môi trường Cloud Container của Kaggle (Google Cloud Platform compute node):

### Cách 1: Đẩy trực tiếp bằng Kaggle CLI
```bash
# Cấu hình API key của Kaggle (tại ~/.kaggle/kaggle.json)
cd notebooks
kaggle kernels push
```

### Cách 2: Tải lên giao diện web Kaggle Notebooks
1. Truy cập [Kaggle Kernels](https://www.kaggle.com/code) -> Chọn **New Notebook**.
2. Tại thanh bên phải (Input), bấm **+ Add Data** -> Tìm kiếm dataset: `mkechinov/ecommerce-behavior-data-from-multi-category-store`.
3. Tải tệp `notebooks/rees46_bigdata_cloud_benchmark.ipynb` lên làm mã nguồn thực thi.
4. Bấm **Run All** để thực thi toàn bộ 5 bước đo đạc.

---

## 4. Các Bước Thực Nghiệm Trong Notebook

1. **Khởi tạo và kiểm tra dung lượng thô:** Đọc tệp `/kaggle/input/.../2019-Oct.csv` xác thực kích thước 5.28 GB.
2. **Cấu hình Out-of-Core Streaming:** DuckDB giới hạn RAM ở mức 2GB (`PRAGMA memory_limit = '2GB'`), chứng minh thuật toán O(1) memory, không gây tràn bộ nhớ (OOM).
3. **Chuyển đổi sang Apache Parquet Snappy:** Ghi theo khối sang định dạng cột nén Snappy. Đo đạc thời gian nén và tỷ lệ tiết kiệm dung lượng đĩa (> 70%).
4. **Đối chuẩn I/O Phân tích (Aggregation Query):**
   - Quét truy vấn tổng hợp trên CSV thô.
   - Quét truy vấn tương tự trên Parquet Snappy.
   - Ghi nhận tốc độ tăng tốc (Speedup factor) > 10x - 30x.
5. **Xuất kết quả JSON chuẩn hóa:** Tự động tạo tệp `bigdata_io_benchmark_results.json` để đồng bộ vào báo cáo khoa học.

---

## 5. Phân Định Minh Bạch: Local vs Cloud

- **Môi trường Local (Hiện tại):** Chạy trên tập dữ liệu churn thực tế 440,833 dòng (`data/raw/`, ~25.5 MB), đối chuẩn Parquet vs CSV vs SQLite trong `data/processed/io_benchmark_results.json`.
- **Môi trường Cloud (Giai đoạn /boost):** Thực thi trọn vẹn notebook trên Kaggle/Azure compute để đối chuẩn tập 5.28 GB mà không dùng bất kỳ dữ liệu nhân tạo nào.
