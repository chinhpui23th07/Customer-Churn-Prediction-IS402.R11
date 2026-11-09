"""
Unit & Integration Test Suite cho KKBox ETL Pipeline (src/data/kkbox_etl.py).
Kiem thu toan ven:
- Luoc do PyArrow & PySpark StructType cho 4 bang quan he va tap dac trung hop nhat.
- Kha nang sinh du lieu mau synthetic Parquet Snappy.
- Thuc thi out-of-core DuckDB streaming ETL.
- Kha nang thich ung schemas: Anh xa tu dong cot Hugging Face (subscriber_key, city_code...)
  sang cot chuan (msno, city...) voi zero data leakage.
- Co che phong thu graceful fallback khi thieu bang giao dich hoac nhat ky nghe nhac.
"""
import os
import pathlib
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
import numpy as np

from src.data.kkbox_etl import (
    KKBoxETLPipeline,
    get_pyarrow_schema,
    get_pyspark_schema,
    generate_synthetic_kkbox_raw,
    SCHEMAS,
    MEMBER_SCHEMA,
    TRANSACTION_SCHEMA,
    LISTENING_DAY_SCHEMA,
    CHURN_LABEL_SCHEMA,
    UNIFIED_FEATURE_SCHEMA
)


def test_kkbox_pyarrow_schemas():
    """Kiem tra cac luoc do PyArrow duoc dinh nghia chinh xac va day du."""
    for table_name in ["member", "subscription_transaction", "listening_day", "churn_label", "unified_features"]:
        schema = get_pyarrow_schema(table_name)
        assert isinstance(schema, pa.Schema)
        assert len(schema.names) > 0

    assert "msno" in MEMBER_SCHEMA.names
    assert "is_churn" in CHURN_LABEL_SCHEMA.names
    assert "actual_amount_paid" in TRANSACTION_SCHEMA.names
    assert "total_secs" in LISTENING_DAY_SCHEMA.names
    assert "gender_encoded" in UNIFIED_FEATURE_SCHEMA.names

    with pytest.raises(ValueError):
        get_pyarrow_schema("invalid_table_name")


def test_kkbox_pyspark_schema_mapping():
    """Kiem tra ham anh xa sang PySpark StructType hoac fallback dict."""
    spark_schema = get_pyspark_schema("member")
    assert spark_schema is not None
    if isinstance(spark_schema, dict):
        assert spark_schema["table"] == "member"
        assert len(spark_schema["fields"]) == len(MEMBER_SCHEMA.names)


def test_generate_synthetic_kkbox_raw(tmp_path):
    """Kiem tra ham sinh du lieu synthetic Parquet Snappy cho 4 bang."""
    raw_dir = str(tmp_path / "raw_synthetic")
    paths = generate_synthetic_kkbox_raw(raw_dir, num_members=50)

    for tbl, p in paths.items():
        assert os.path.exists(p), f"Tep {p} khong ton tai"
        assert p.endswith(".parquet")
        tbl_data = pq.read_table(p)
        assert tbl_data.num_rows > 0

    m_tbl = pq.read_table(paths["member"])
    assert "msno" in m_tbl.column_names
    assert m_tbl.num_rows == 50

    ch_tbl = pq.read_table(paths["churn_label"])
    assert "is_churn" in ch_tbl.column_names
    assert ch_tbl.num_rows == 50


def test_kkbox_etl_pipeline_synthetic_execution(tmp_path):
    """Kiem tra thuc thi pipeline DuckDB out-of-core tren tap du lieu synthetic."""
    raw_dir = str(tmp_path / "raw_data")
    proc_dir = str(tmp_path / "proc_data")
    generate_synthetic_kkbox_raw(raw_dir, num_members=100)

    pipe = KKBoxETLPipeline(raw_dir, proc_dir, memory_limit="1GB")
    out_file = str(tmp_path / "proc_data" / "features.parquet")
    stats = pipe.run_etl(output_file=out_file)

    assert os.path.exists(out_file)
    assert stats["row_count"] == 100
    assert 0.0 <= stats["churn_rate"] <= 1.0
    assert stats["file_size_mb"] > 0.0
    assert stats["throughput_rows_sec"] > 0.0

    tbl = pq.read_table(out_file)
    expected_cols = [
        "msno", "city", "bd", "gender_encoded", "registered_via",
        "trans_count", "avg_plan_days", "total_actual_paid",
        "auto_renew_ratio", "cancel_ratio", "discount_ratio",
        "listen_days_count", "total_listen_secs", "total_songs_played",
        "completion_ratio", "unique_song_ratio", "is_churn"
    ]
    for col in expected_cols:
        assert col in tbl.column_names, f"Thieu cot {col}"
    assert tbl.num_rows == 100

    df = tbl.to_pandas()
    assert df["trans_count"].mean() > 0, "trans_count phai co du lieu giao dich thuc"
    assert df["listen_days_count"].mean() > 0, "listen_days_count phai co du lieu nghe nhac"
    assert df["total_actual_paid"].mean() > 0, "total_actual_paid phai lon hon 0"
    assert df["total_songs_played"].mean() > 0, "total_songs_played phai lon hon 0"


def test_find_real_hf_snapshot():
    """Kiem tra ham tu dong phat hien snapshot Hugging Face thuc te."""
    from src.data.kkbox_etl import find_real_hf_snapshot
    snap = find_real_hf_snapshot()
    if snap is not None:
        assert os.path.exists(snap)
        assert os.path.isdir(snap)



def test_kkbox_etl_huggingface_schema_adaptation(tmp_path):
    """
    Kiem tra tinh thich ung cua ETL voi ten cot goc tu Hugging Face
    (subscriber_key, city_code, age_band_start, registration_method_code).
    """
    raw_dir = tmp_path / "hf_raw"
    m_dir = raw_dir / "member"
    ch_dir = raw_dir / "churn_label" / "window=2017-03"
    m_dir.mkdir(parents=True)
    ch_dir.mkdir(parents=True)

    # Tao bang member kieu Hugging Face
    sub_keys = [1000000000000001, 1000000000000002, 1000000000000003]
    m_df = pd.DataFrame({
        "subscriber_key": sub_keys,
        "city_code": [1, 5, 13],
        "age_band_start": [20, 30, 40],
        "gender": ["male", "female", None],
        "registration_method_code": [3, 7, 9]
    })
    m_df.to_parquet(m_dir / "data.parquet", index=False)

    # Tao bang churn_label kieu Hugging Face
    ch_df = pd.DataFrame({
        "subscriber_key": sub_keys,
        "label_window": ["train_v2", "train_v2", "train_v2"],
        "is_churn": [1, 0, 0],
        "window": ["2017-03", "2017-03", "2017-03"]
    })
    ch_df.to_parquet(ch_dir / "data.parquet", index=False)

    proc_dir = str(tmp_path / "proc_hf")
    pipe = KKBoxETLPipeline(str(raw_dir), proc_dir)
    out_parquet = str(pathlib.Path(proc_dir) / "hf_adapted.parquet")
    stats = pipe.run_etl(output_file=out_parquet)

    assert stats["row_count"] == 3
    assert stats["churn_count"] == 1
    tbl = pq.read_table(out_parquet)
    df = tbl.to_pandas()

    # Kiem tra subscriber_key da duoc chuyen doi an toan sang chuoi msno
    assert "msno" in df.columns
    assert set(df["msno"].tolist()) == {str(k) for k in sub_keys}
    assert df["city"].tolist() == [1, 5, 13]
    assert df["bd"].tolist() == [20, 30, 40]
    assert df["gender_encoded"].tolist() == [1, 0, -1]
    assert df["is_churn"].tolist() == [1, 0, 0]


def test_kkbox_etl_missing_tables_fallback(tmp_path):
    """
    Kiem tra fallback an toan khi chi co member va churn_label,
    thieu subscription_transaction va listening_day.
    """
    raw_dir = tmp_path / "partial_raw"
    m_dir = raw_dir / "member"
    ch_dir = raw_dir / "churn_label"
    m_dir.mkdir(parents=True)
    ch_dir.mkdir(parents=True)

    pd.DataFrame({"msno": ["user_1", "user_2"], "city": [1, 2]}).to_parquet(m_dir / "data.parquet", index=False)
    pd.DataFrame({"msno": ["user_1", "user_2"], "is_churn": [0, 1]}).to_parquet(ch_dir / "data.parquet", index=False)

    proc_dir = str(tmp_path / "proc_partial")
    pipe = KKBoxETLPipeline(str(raw_dir), proc_dir)
    out_file = str(pathlib.Path(proc_dir) / "partial.parquet")
    stats = pipe.run_etl(output_file=out_file)

    assert stats["row_count"] == 2
    tbl = pq.read_table(out_file)
    df = tbl.to_pandas()
    assert df["trans_count"].tolist() == [0, 0]
    assert df["listen_days_count"].tolist() == [0, 0]
    assert df["is_churn"].tolist() == [0, 1]
