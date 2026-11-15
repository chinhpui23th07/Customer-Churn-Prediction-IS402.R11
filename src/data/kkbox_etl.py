"""
ETL Pipeline cho tập dữ liệu KKBox Customer Churn (Hugging Face).
Bộ dữ liệu: vaibhavkhurana/subscriber-retention-intelligence (7.52 GB, 32 Parquet Snappy).
Cung cấp lược đồ PyArrow/PySpark, xử lý out-of-core chunking với DuckDB và xuất Parquet.
"""
import os
import sys
import time
from typing import Dict, Any, Optional
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DATASET_ID = "vaibhavkhurana/subscriber-retention-intelligence"
NOMINAL_SIZE_BYTES = 7_522_254_856
TOTAL_PARQUET_FILES = 32
ENTITY_KEY = "msno"
TARGET_LABEL = "is_churn"
TABLE_NAMES = ["member", "subscription_transaction", "listening_day", "churn_label"]

def _f(name: str, dtype: pa.DataType, nullable: bool = True) -> pa.Field:
    return pa.field(name, dtype, nullable=nullable)

MEMBER_SCHEMA = pa.schema([
    _f("msno", pa.string(), False), _f("city", pa.int32()), _f("bd", pa.int32()),
    _f("gender", pa.string()), _f("registered_via", pa.int32()), _f("registration_init_time", pa.int64())
])

TRANSACTION_SCHEMA = pa.schema([
    _f("msno", pa.string(), False), _f("payment_method_id", pa.int32()), _f("payment_plan_days", pa.int32()),
    _f("plan_list_price", pa.float64()), _f("actual_amount_paid", pa.float64()), _f("is_auto_renew", pa.int32()),
    _f("transaction_date", pa.int64()), _f("membership_expire_date", pa.int64()), _f("is_cancel", pa.int32())
])

LISTENING_DAY_SCHEMA = pa.schema([
    _f("msno", pa.string(), False), _f("date", pa.int64()), _f("num_25", pa.int64()),
    _f("num_50", pa.int64()), _f("num_75", pa.int64()), _f("num_985", pa.int64()),
    _f("num_100", pa.int64()), _f("num_unq", pa.int64()), _f("total_secs", pa.float64())
])

CHURN_LABEL_SCHEMA = pa.schema([
    _f("msno", pa.string(), False), _f("is_churn", pa.int32(), False)
])

UNIFIED_FEATURE_SCHEMA = pa.schema([
    _f("msno", pa.string(), False), _f("city", pa.int32()), _f("bd", pa.int32()),
    _f("gender_encoded", pa.int32()), _f("registered_via", pa.int32()), _f("trans_count", pa.int64()),
    _f("avg_plan_days", pa.float64()), _f("total_actual_paid", pa.float64()), _f("auto_renew_ratio", pa.float64()),
    _f("cancel_ratio", pa.float64()), _f("discount_ratio", pa.float64()), _f("listen_days_count", pa.int64()),
    _f("total_listen_secs", pa.float64()), _f("total_songs_played", pa.int64()), _f("completion_ratio", pa.float64()),
    _f("unique_song_ratio", pa.float64()), _f("is_churn", pa.int32(), False)
])

SCHEMAS = {
    "member": MEMBER_SCHEMA,
    "subscription_transaction": TRANSACTION_SCHEMA,
    "listening_day": LISTENING_DAY_SCHEMA,
    "churn_label": CHURN_LABEL_SCHEMA,
    "unified_features": UNIFIED_FEATURE_SCHEMA
}


def get_pyarrow_schema(table_name: str) -> pa.Schema:
    """Truy xuất lược đồ PyArrow cho bảng tương ứng."""
    if table_name not in SCHEMAS:
        raise ValueError(f"Không tìm thấy bảng: {table_name}. Bảng hợp lệ: {list(SCHEMAS.keys())}")
    return SCHEMAS[table_name]


def get_pyspark_schema(table_name: str) -> Any:
    """Truy xuất cấu trúc PySpark StructType tương ứng nếu pyspark được cài đặt."""
    try:
        from pyspark.sql.types import StructType, StructField, StringType, IntegerType, LongType, DoubleType
        type_mapping = {
            pa.string(): StringType(),
            pa.int32(): IntegerType(),
            pa.int64(): LongType(),
            pa.float64(): DoubleType()
        }
        pa_schema = get_pyarrow_schema(table_name)
        fields = [
            StructField(f.name, type_mapping.get(f.type, StringType()), f.nullable)
            for f in pa_schema
        ]
        return StructType(fields)
    except ImportError:
        schema = get_pyarrow_schema(table_name)
        return {
            "table": table_name,
            "fields": [{"name": f.name, "type": str(f.type), "nullable": f.nullable} for f in schema]
        }


class KKBoxETLPipeline:
    """Pipeline trích xuất, biến đổi và nạp (ETL) out-of-core cho KKBox Dataset."""

    def __init__(self, raw_dir: str, processed_dir: str, memory_limit: str = "2GB"):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        self.memory_limit = memory_limit
        os.makedirs(self.processed_dir, exist_ok=True)

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        con = duckdb.connect(database=":memory:")
        con.execute(f"SET max_memory = '{self.memory_limit}'")
        con.execute("SET preserve_insertion_order = false")
        temp_dir = os.path.join(self.processed_dir, ".duckdb_temp").replace("\\", "/")
        os.makedirs(os.path.join(self.processed_dir, ".duckdb_temp"), exist_ok=True)
        con.execute(f"SET temp_directory = '{temp_dir}'")
        con.execute("SET max_temp_directory_size = '10GB'")
        return con

    def _inspect_columns(self, con: duckdb.DuckDBPyConnection, path_pattern: str) -> Dict[str, str]:
        try:
            res = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path_pattern}') LIMIT 0").fetchall()
            return {r[0].lower(): str(r[1]).upper() for r in res}
        except Exception as e:
            if "No files found" not in str(e) and "does not exist" not in str(e):
                print(f"[!] Warning inspect {path_pattern}: {e}")
            return {}

    @staticmethod
    def _cutoff_predicate(col_name: str, col_type: str, cutoff_date: str) -> str:
        cutoff_int = int(cutoff_date.replace("-", ""))
        if any(tok in col_type for tok in ("INT", "BIGINT", "SMALLINT", "TINYINT", "DECIMAL", "NUMERIC")):
            return f"CAST({col_name} AS BIGINT) <= {cutoff_int}"
        return f"CAST({col_name} AS DATE) <= DATE '{cutoff_date}'"

    def run_etl(
        self,
        output_file: Optional[str] = None,
        sample_limit: Optional[int] = None,
        label_period: str = "2017-03",
        label_window: Optional[str] = None,
        cutoff_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Thuc thi luong ETL out-of-core cutoff-safe tong hop dac trung va xuat Parquet Snappy."""
        start_time = time.time()
        window_map = {
            "2017-02": ("train", "2017-01-31"),
            "2017-03": ("train_v2", "2017-02-28"),
        }
        default_win, default_cutoff = window_map.get(label_period, ("train_v2", "2017-02-28"))
        resolved_window = label_window or default_win
        resolved_cutoff = cutoff_date or default_cutoff

        if output_file is None:
            output_file = os.path.join(self.processed_dir, "kkbox_churn_features.parquet")

        con = self._get_connection()
        m_path = os.path.join(self.raw_dir, "member", "**", "*.parquet").replace("\\", "/")
        tx_path = os.path.join(self.raw_dir, "subscription_transaction", "**", "*.parquet").replace("\\", "/")
        ld_path = os.path.join(self.raw_dir, "listening_day", "**", "*.parquet").replace("\\", "/")
        ch_path = os.path.join(self.raw_dir, "churn_label", "**", "*.parquet").replace("\\", "/")

        m_cols = self._inspect_columns(con, m_path)
        tx_cols = self._inspect_columns(con, tx_path)
        ld_cols = self._inspect_columns(con, ld_path)
        ch_cols = self._inspect_columns(con, ch_path)

        key_col = "subscriber_key" if "subscriber_key" in m_cols else ("msno" if "msno" in m_cols else "subscriber_key")
        c_expr = "COALESCE(city_code, 1)" if "city_code" in m_cols else ("COALESCE(city, 1)" if "city" in m_cols else "1")
        b_col = "age_band_start" if "age_band_start" in m_cols else ("bd" if "bd" in m_cols else None)
        b_expr = f"CASE WHEN {b_col} < 10 OR {b_col} > 95 THEN 30 ELSE COALESCE({b_col}, 30) END" if b_col else "30"
        g_expr = "CASE WHEN LOWER(COALESCE(gender, '')) = 'female' THEN 0 WHEN LOWER(COALESCE(gender, '')) = 'male' THEN 1 ELSE -1 END" if "gender" in m_cols else "-1"
        r_expr = "COALESCE(registration_method_code, 7)" if "registration_method_code" in m_cols else ("COALESCE(registered_via, 7)" if "registered_via" in m_cols else "7")

        m_cte = (
            f"SELECT CAST({key_col} AS VARCHAR) AS msno, {c_expr} AS city, {b_expr} AS bd, "
            f"{g_expr} AS gender_encoded, {r_expr} AS registered_via FROM read_parquet('{m_path}')"
        )
        ch_key = "subscriber_key" if "subscriber_key" in ch_cols else "msno"
        ch_where = f" WHERE label_window = '{resolved_window}'" if "label_window" in ch_cols else ""
        ch_cte = f"SELECT CAST({ch_key} AS VARCHAR) AS msno, is_churn FROM read_parquet('{ch_path}'){ch_where}"
        if tx_cols:
            tx_k = "subscriber_key" if "subscriber_key" in tx_cols else "msno"
            tx_where = (
                f" WHERE {self._cutoff_predicate('transaction_date', tx_cols['transaction_date'], resolved_cutoff)}"
                if "transaction_date" in tx_cols else ""
            )
            tx_cte = (
                f"SELECT CAST({tx_k} AS VARCHAR) AS msno, COUNT(*) AS trans_count, "
                f"AVG(payment_plan_days) AS avg_plan_days, SUM(actual_amount_paid) AS total_actual_paid, "
                f"AVG(CAST(is_auto_renew AS DOUBLE)) AS auto_renew_ratio, "
                f"AVG(CAST(is_cancel AS DOUBLE)) AS cancel_ratio, "
                f"(SUM(plan_list_price) - SUM(actual_amount_paid)) / NULLIF(SUM(plan_list_price), 0.0) "
                f"AS discount_ratio FROM read_parquet('{tx_path}'){tx_where} GROUP BY {tx_k}"
            )
        else:
            tx_cte = "SELECT CAST('' AS VARCHAR) AS msno, 0::BIGINT AS trans_count, 30.0::DOUBLE AS avg_plan_days, 0.0::DOUBLE AS total_actual_paid, 0.0::DOUBLE AS auto_renew_ratio, 0.0::DOUBLE AS cancel_ratio, 0.0::DOUBLE AS discount_ratio WHERE 1=0"
        if ld_cols:
            ld_k = "subscriber_key" if "subscriber_key" in ld_cols else "msno"
            d_col = "activity_date" if "activity_date" in ld_cols else "date"
            ld_where = (
                f" WHERE {self._cutoff_predicate(d_col, ld_cols[d_col], resolved_cutoff)}"
                if d_col in ld_cols else ""
            )
            ld_cte = (
                f"SELECT CAST({ld_k} AS VARCHAR) AS msno, COUNT(DISTINCT {d_col}) AS listen_days_count, "
                f"SUM(total_secs) AS total_listen_secs, "
                f"SUM(num_25 + num_50 + num_75 + num_985 + num_100) AS total_songs_played, "
                f"SUM(num_100) / NULLIF(SUM(num_25 + num_50 + num_75 + num_985 + num_100), 0.0) AS completion_ratio, "
                f"SUM(num_unq) / NULLIF(SUM(num_25 + num_50 + num_75 + num_985 + num_100), 0.0) AS unique_song_ratio "
                f"FROM read_parquet('{ld_path}'){ld_where} GROUP BY {ld_k}"
            )
        else:
            ld_cte = "SELECT CAST('' AS VARCHAR) AS msno, 0::BIGINT AS listen_days_count, 0.0::DOUBLE AS total_listen_secs, 0.0::DOUBLE AS total_songs_played, 0.0::DOUBLE AS completion_ratio, 0.0::DOUBLE AS unique_song_ratio WHERE 1=0"

        limit_clause = f"LIMIT {sample_limit}" if sample_limit else ""

        query = f"""
        CREATE OR REPLACE TABLE aggregated_features AS
        WITH members_cleaned AS ({m_cte}), tx_summary AS ({tx_cte}),
        listen_summary AS ({ld_cte}), churn_labels AS ({ch_cte})
        SELECT
            c.msno, m.city, m.bd, m.gender_encoded, m.registered_via,
            COALESCE(t.trans_count, 0) AS trans_count, COALESCE(t.avg_plan_days, 30.0) AS avg_plan_days,
            COALESCE(t.total_actual_paid, 0.0) AS total_actual_paid, COALESCE(t.auto_renew_ratio, 0.0) AS auto_renew_ratio,
            COALESCE(t.cancel_ratio, 0.0) AS cancel_ratio, COALESCE(t.discount_ratio, 0.0) AS discount_ratio,
            COALESCE(l.listen_days_count, 0) AS listen_days_count, COALESCE(l.total_listen_secs, 0.0) AS total_listen_secs,
            COALESCE(l.total_songs_played, 0) AS total_songs_played, COALESCE(l.completion_ratio, 0.0) AS completion_ratio,
            COALESCE(l.unique_song_ratio, 0.0) AS unique_song_ratio,
            '{label_period}' AS label_period, DATE '{resolved_cutoff}' AS as_of_date, c.is_churn
        FROM churn_labels c LEFT JOIN members_cleaned m ON c.msno = m.msno
        LEFT JOIN tx_summary t ON c.msno = t.msno LEFT JOIN listen_summary l ON c.msno = l.msno {limit_clause};
        """
        try:
            con.execute(query)
            out_sql = output_file.replace("\\", "/")
            con.execute(f"COPY aggregated_features TO '{out_sql}' (FORMAT PARQUET, CODEC 'SNAPPY')")
            row_count = con.execute("SELECT COUNT(*) FROM aggregated_features").fetchone()[0]
            churn_count = con.execute("SELECT SUM(is_churn) FROM aggregated_features").fetchone()[0]
            src_counts = [
                con.execute(f"SELECT COUNT(*) FROM read_parquet('{p}')").fetchone()[0]
                for p in ([m_path, ch_path] + ([tx_path] if tx_cols else []) + ([ld_path] if ld_cols else []))
            ]
            actual_source_rows = int(sum(src_counts))
        finally:
            con.close()

        elapsed = time.time() - start_time
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        target_entity_throughput = round(row_count / max(elapsed, 0.001), 1)
        source_throughput = round(actual_source_rows / max(elapsed, 0.001), 1)

        return {
            "output_file": output_file,
            "row_count": row_count,
            "source_rows_scanned": actual_source_rows,
            "churn_count": int(churn_count) if churn_count else 0,
            "churn_rate": round(float(churn_count / max(row_count, 1)), 4),
            "label_period": label_period,
            "label_window": resolved_window,
            "cutoff_date": resolved_cutoff,
            "file_size_mb": round(file_size_mb, 2),
            "elapsed_seconds": round(elapsed, 2),
            "throughput_rows_sec": target_entity_throughput,
            "target_entity_throughput_records_sec": target_entity_throughput,
            "source_scanning_throughput_rows_sec": source_throughput,
            "memory_execution_policy": "Bounded Memory Execution (<= 2 GB Buffer Manager) via Radix-Partitioned Out-of-Core Disk Spilling (temp_directory)"
        }


def generate_synthetic_kkbox_raw(target_dir: str, num_members: int = 200) -> Dict[str, str]:
    """Sinh tập dữ liệu mẫu Parquet Snappy cho 4 bảng phục vụ kiểm thử cục bộ và CI."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(42)
    os.makedirs(target_dir, exist_ok=True)
    m_dir = os.path.join(target_dir, "member")
    tx_dir = os.path.join(target_dir, "subscription_transaction")
    ld_dir = os.path.join(target_dir, "listening_day")
    ch_dir = os.path.join(target_dir, "churn_label", "window=2017-03")
    for d in [m_dir, tx_dir, ld_dir, ch_dir]:
        os.makedirs(d, exist_ok=True)

    msnos = [f"msno_{i:06d}" for i in range(num_members)]

    # 1. Member
    m_df = pd.DataFrame({
        "msno": msnos,
        "city": rng.integers(1, 23, size=num_members, dtype="int32"),
        "bd": rng.integers(15, 75, size=num_members, dtype="int32"),
        "gender": rng.choice(["male", "female", None], size=num_members),
        "registered_via": rng.choice([3, 4, 7, 9], size=num_members).astype("int32"),
        "registration_init_time": rng.integers(20120101, 20161231, size=num_members, dtype="int64")
    })
    m_file = os.path.join(m_dir, "data.parquet")
    m_df.to_parquet(m_file, engine="pyarrow", compression="snappy", schema=MEMBER_SCHEMA, index=False)

    # 2. Subscription Transaction
    n_tx = num_members * 3
    tx_msnos = rng.choice(msnos, size=n_tx)
    plans = rng.choice([30, 60, 90, 180, 360], size=n_tx).astype("int32")
    prices = (plans * 5.0).astype("float64")
    tx_df = pd.DataFrame({
        "msno": tx_msnos,
        "payment_method_id": rng.integers(1, 41, size=n_tx, dtype="int32"),
        "payment_plan_days": plans,
        "plan_list_price": prices,
        "actual_amount_paid": prices,
        "is_auto_renew": rng.choice([0, 1], size=n_tx, p=[0.2, 0.8]).astype("int32"),
        "transaction_date": rng.integers(20170101, 20170228, size=n_tx, dtype="int64"),
        "membership_expire_date": rng.integers(20170301, 20170630, size=n_tx, dtype="int64"),
        "is_cancel": rng.choice([0, 1], size=n_tx, p=[0.95, 0.05]).astype("int32")
    })
    tx_file = os.path.join(tx_dir, "data.parquet")
    tx_df.to_parquet(tx_file, engine="pyarrow", compression="snappy", schema=TRANSACTION_SCHEMA, index=False)

    # 3. Listening Day
    n_ld = num_members * 5
    ld_df = pd.DataFrame({
        "msno": rng.choice(msnos, size=n_ld),
        "date": rng.integers(20170201, 20170228, size=n_ld, dtype="int64"),
        "num_25": rng.integers(0, 20, size=n_ld, dtype="int64"),
        "num_50": rng.integers(0, 10, size=n_ld, dtype="int64"),
        "num_75": rng.integers(0, 5, size=n_ld, dtype="int64"),
        "num_985": rng.integers(0, 5, size=n_ld, dtype="int64"),
        "num_100": rng.integers(5, 50, size=n_ld, dtype="int64"),
        "num_unq": rng.integers(5, 60, size=n_ld, dtype="int64"),
        "total_secs": rng.uniform(300.0, 12000.0, size=n_ld).astype("float64")
    })
    ld_file = os.path.join(ld_dir, "data.parquet")
    ld_df.to_parquet(ld_file, engine="pyarrow", compression="snappy", schema=LISTENING_DAY_SCHEMA, index=False)

    # 4. Churn Label
    ch_df = pd.DataFrame({
        "msno": msnos,
        "is_churn": rng.choice([0, 1], size=num_members, p=[0.85, 0.15]).astype("int32")
    })
    ch_file = os.path.join(ch_dir, "data.parquet")
    ch_df.to_parquet(ch_file, engine="pyarrow", compression="snappy", schema=CHURN_LABEL_SCHEMA, index=False)

    return {
        "member": m_file,
        "subscription_transaction": tx_file,
        "listening_day": ld_file,
        "churn_label": ch_file
    }


def find_real_hf_snapshot() -> Optional[str]:
    """Tìm thư mục snapshot dữ liệu thật KKBox trong cache Hugging Face nếu có."""
    snap_base = os.path.expanduser("~/.cache/huggingface/hub/datasets--vaibhavkhurana--subscriber-retention-intelligence/snapshots")
    if os.path.exists(snap_base):
        for entry in os.listdir(snap_base):
            p = os.path.join(snap_base, entry)
            if os.path.isdir(p) and os.path.exists(os.path.join(p, "member")):
                return p
    return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KKBox ETL Pipeline")
    parser.add_argument("--mode", choices=["auto", "real", "synthetic"], default="auto")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proc = os.path.join(base, "data", "processed")
    real_snap = find_real_hf_snapshot()

    if args.mode in ("auto", "real") and real_snap:
        print(f"[*] Chay ETL tren dataset KKBox that tu HF snapshot: {real_snap}")
        pipe = KKBoxETLPipeline(real_snap, proc)
        out_f = os.path.join(proc, "real_hf_kkbox_full_window.parquet")
        stats = pipe.run_etl(output_file=out_f, sample_limit=args.limit)
    else:
        sample_raw = os.path.join(base, "data", "kkbox_sample_raw")
        print(f"[*] Chay ETL tren tap synthetic mau tai: {sample_raw}")
        generate_synthetic_kkbox_raw(sample_raw, num_members=500)
        pipe = KKBoxETLPipeline(sample_raw, proc)
        stats = pipe.run_etl()

    print("[+] Hoan tat ETL:")
    for k, v in stats.items():
        print(f"    - {k}: {v}")
