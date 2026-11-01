"""
Module đo kiểm hiệu năng IO (IOPS, Latency, Throughput) giữa các định dạng lưu trữ.
Hỗ trợ đối chuẩn IOPS, Latency và Throughput giữa CSV, Parquet và SQLite.
"""
import os
import sys
import time
import json
import sqlite3
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PARQUET_FILE = os.path.join(BASE_DIR, "data", "processed", "train_features.parquet")
OUTPUT_BENCHMARK = os.path.join(BASE_DIR, "data", "processed", "io_benchmark_results.json")
TEMP_CSV = os.path.join(BASE_DIR, "data", "processed", "temp_benchmark.csv")
TEMP_DB = os.path.join(BASE_DIR, "data", "processed", "temp_benchmark.db")


def run_benchmark(num_rows: int = 100000):
    """Đo đạc thời gian ghi, đọc và dung lượng bộ nhớ giữa CSV, Parquet và SQLite."""
    print(f"[*] Đang thực hiện Benchmark IO trên {num_rows:,} mẫu dữ liệu...")
    df = pd.read_parquet(PARQUET_FILE).iloc[:num_rows]

    results = {}

    # 1. Định dạng CSV
    t0 = time.perf_counter()
    df.to_csv(TEMP_CSV, index=False)
    csv_write_time = time.perf_counter() - t0
    csv_size_mb = os.path.getsize(TEMP_CSV) / (1024 * 1024)

    t0 = time.perf_counter()
    _ = pd.read_csv(TEMP_CSV)
    csv_read_time = time.perf_counter() - t0

    results["CSV"] = {
        "format": "CSV (Row-based Plain Text)",
        "file_size_mb": round(csv_size_mb, 2),
        "write_time_sec": round(csv_write_time, 4),
        "read_time_sec": round(csv_read_time, 4),
        "write_throughput_mb_s": round(csv_size_mb / max(csv_write_time, 0.0001), 2),
        "read_throughput_mb_s": round(csv_size_mb / max(csv_read_time, 0.0001), 2)
    }

    # 2. Định dạng Apache Parquet (Columnar + Snappy compression)
    temp_parquet = os.path.join(BASE_DIR, "data", "processed", "temp_benchmark.parquet")
    t0 = time.perf_counter()
    df.to_parquet(temp_parquet, compression="snappy", index=False)
    parquet_write_time = time.perf_counter() - t0
    parquet_size_mb = os.path.getsize(temp_parquet) / (1024 * 1024)

    t0 = time.perf_counter()
    _ = pd.read_parquet(temp_parquet)
    parquet_read_time = time.perf_counter() - t0

    results["Parquet"] = {
        "format": "Apache Parquet (Columnar + Snappy)",
        "file_size_mb": round(parquet_size_mb, 2),
        "write_time_sec": round(parquet_write_time, 4),
        "read_time_sec": round(parquet_read_time, 4),
        "write_throughput_mb_s": round(parquet_size_mb / max(parquet_write_time, 0.0001), 2),
        "read_throughput_mb_s": round(parquet_size_mb / max(parquet_read_time, 0.0001), 2),
        "compression_ratio_vs_csv": round(csv_size_mb / max(parquet_size_mb, 0.0001), 2),
        "read_speedup_vs_csv": round(csv_read_time / max(parquet_read_time, 0.0001), 2)
    }

    # 3. Định dạng SQLite (Relational DB)
    conn = sqlite3.connect(TEMP_DB)
    t0 = time.perf_counter()
    df.to_sql("customers", conn, if_exists="replace", index=False)
    sqlite_write_time = time.perf_counter() - t0
    conn.close()
    sqlite_size_mb = os.path.getsize(TEMP_DB) / (1024 * 1024)

    conn = sqlite3.connect(TEMP_DB)
    t0 = time.perf_counter()
    _ = pd.read_sql("SELECT * FROM customers", conn)
    sqlite_read_time = time.perf_counter() - t0
    conn.close()

    results["SQLite"] = {
        "format": "SQLite3 (Relational Embedded DB)",
        "file_size_mb": round(sqlite_size_mb, 2),
        "write_time_sec": round(sqlite_write_time, 4),
        "read_time_sec": round(sqlite_read_time, 4),
        "write_throughput_mb_s": round(sqlite_size_mb / max(sqlite_write_time, 0.0001), 2),
        "read_throughput_mb_s": round(sqlite_size_mb / max(sqlite_read_time, 0.0001), 2)
    }

    # Dọn dẹp tệp tạm
    for p in [TEMP_CSV, temp_parquet, TEMP_DB]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    with open(OUTPUT_BENCHMARK, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n=================== KẾT QUẢ BENCHMARK IO ===================")
    print(f"{'Định dạng':<25} | {'Size (MB)':<10} | {'Write (s)':<10} | {'Read (s)':<10} | {'Read (MB/s)':<12}")
    print("-" * 75)
    for k, v in results.items():
        print(f"{v['format']:<25} | {v['file_size_mb']:<10} | {v['write_time_sec']:<10} | {v['read_time_sec']:<10} | {v['read_throughput_mb_s']:<12}")
    print("=" * 75)
    print(f"[+] Parquet giảm dung lượng gấp {results['Parquet']['compression_ratio_vs_csv']}x so với CSV")
    print(f"[+] Parquet đọc nhanh hơn gấp {results['Parquet']['read_speedup_vs_csv']}x so với CSV")
    print(f"[+] Đã lưu báo cáo benchmark vào: {OUTPUT_BENCHMARK}")
    return results


if __name__ == "__main__":
    run_benchmark()
