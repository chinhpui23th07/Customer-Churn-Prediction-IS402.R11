"""
Module quản lý Feature Store sử dụng Feast.
Đáp ứng yêu cầu Bài tập 11: Feature Store với Feast (Offline/Online store).
Tuân thủ Invariant 01 và Invariant 02 (< 400 dòng).
"""
import os
import sys
from datetime import datetime, timezone
import pandas as pd
from feast import (
    Entity,
    Field,
    FeatureStore,
    FeatureView,
    FileSource,
    ValueType
)
from feast.types import Float32, Int64

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FEAST_REPO_DIR = os.path.join(BASE_DIR, "data", "feast_repo")
FEAST_PARQUET_SOURCE = os.path.join(FEAST_REPO_DIR, "churn_features.parquet")
PROCESSED_TRAIN_FILE = os.path.join(BASE_DIR, "data", "processed", "train_features.parquet")

# Định nghĩa Feast Entity
customer_entity = Entity(
    name="customer_id",
    value_type=ValueType.INT64,
    join_keys=["customerid"],
    description="Mã định danh khách hàng duy nhất"
)

# Nguồn dữ liệu Offline Parquet cho Feast
file_source = FileSource(
    name="churn_parquet_source",
    path=FEAST_PARQUET_SOURCE.replace("\\", "/"),
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp"
)

# Định nghĩa Feature View
customer_feature_view = FeatureView(
    name="customer_churn_features",
    entities=[customer_entity],
    ttl=None,
    schema=[
        Field(name="age", dtype=Float32),
        Field(name="gender_encoded", dtype=Int64),
        Field(name="tenure", dtype=Float32),
        Field(name="usage_frequency", dtype=Float32),
        Field(name="support_calls", dtype=Float32),
        Field(name="payment_delay", dtype=Float32),
        Field(name="subscription_type_encoded", dtype=Int64),
        Field(name="contract_length_encoded", dtype=Int64),
        Field(name="total_spend", dtype=Float32),
        Field(name="last_interaction", dtype=Float32),
        Field(name="support_calls_per_tenure", dtype=Float32),
        Field(name="spend_per_tenure", dtype=Float32),
        Field(name="delay_ratio", dtype=Float32)
    ],
    online=True,
    source=file_source
)


def prepare_feast_data(sample_size: int = 100000):
    """Chuẩn bị dữ liệu đầu vào cho Feast Offline Store với timestamp hợp lệ."""
    os.makedirs(FEAST_REPO_DIR, exist_ok=True)
    df = pd.read_parquet(PROCESSED_TRAIN_FILE)
    if sample_size and len(df) > sample_size:
        df = df.iloc[:sample_size].copy()
    else:
        df = df.copy()

    now = datetime.now(timezone.utc)
    if "event_timestamp" not in df.columns:
        df["event_timestamp"] = now - pd.to_timedelta(df["tenure"] * 30, unit="D")
    if "created_timestamp" not in df.columns:
        df["created_timestamp"] = now

    for col in ["age", "tenure", "usage_frequency", "support_calls", "payment_delay",
                "total_spend", "last_interaction", "support_calls_per_tenure",
                "spend_per_tenure", "delay_ratio"]:
        df[col] = df[col].astype("float32")

    for col in ["customerid", "gender_encoded", "subscription_type_encoded", "contract_length_encoded"]:
        df[col] = df[col].astype("int64")

    df.to_parquet(FEAST_PARQUET_SOURCE, index=False)
    print(f"[+] Đã tạo tệp Feast Offline Source: {FEAST_PARQUET_SOURCE} ({len(df):,} mẫu)")


_FEATURE_STORE_INSTANCE = None


def get_feature_store() -> FeatureStore:
    """Trả về phiên bản Feast FeatureStore Singleton tối ưu tài nguyên."""
    global _FEATURE_STORE_INSTANCE
    if _FEATURE_STORE_INSTANCE is None:
        _FEATURE_STORE_INSTANCE = FeatureStore(repo_path=FEAST_REPO_DIR)
    return _FEATURE_STORE_INSTANCE


def setup_feast_store():
    """Khởi tạo và apply metadata vào Feast Registry & Online Store."""
    prepare_feast_data()
    store = get_feature_store()
    print("[*] Đang apply Entity và FeatureView vào Feast Registry...")
    store.apply([customer_entity, customer_feature_view])
    print("[*] Đang materialize dữ liệu sang Feast Online Store (SQLite)...")
    end_date = datetime.now(timezone.utc)
    start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    store.materialize(start_date=start_date, end_date=end_date)
    print("[+] Materialize thành công! Online Store đã sẵn sàng phục vụ real-time.")
    return store


def query_online_features(customer_ids: list[int]) -> dict:
    """Truy xuất đặc trưng online cho phục vụ dự đoán thời gian thực (Serving)."""
    store = get_feature_store()
    feature_names = [
        "customer_churn_features:age",
        "customer_churn_features:gender_encoded",
        "customer_churn_features:tenure",
        "customer_churn_features:usage_frequency",
        "customer_churn_features:support_calls",
        "customer_churn_features:payment_delay",
        "customer_churn_features:subscription_type_encoded",
        "customer_churn_features:contract_length_encoded",
        "customer_churn_features:total_spend",
        "customer_churn_features:last_interaction",
        "customer_churn_features:support_calls_per_tenure",
        "customer_churn_features:spend_per_tenure",
        "customer_churn_features:delay_ratio"
    ]
    entity_rows = [{"customerid": cid} for cid in customer_ids]
    response = store.get_online_features(features=feature_names, entity_rows=entity_rows)
    return response.to_dict()


if __name__ == "__main__":
    store = setup_feast_store()
    test_cids = [1, 2, 3]
    features = query_online_features(test_cids)
    print("\n[*] Thử nghiệm truy vấn Online Features từ Feast cho Customer IDs 1, 2, 3:")
    print(features)
