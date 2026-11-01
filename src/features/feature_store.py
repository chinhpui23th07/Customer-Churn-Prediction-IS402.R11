"""
Module quản lý Feature Store sử dụng Feast.
Quản lý vòng đời đặc trưng và phục vụ Feature Store (Feast Offline/Online Store).
"""
import os
import sys
import time
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from feast import (
    Entity,
    Field,
    FeatureStore,
    FeatureView,
    FileSource,
    ValueType
)
from feast.types import Float64, Int64

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FEAST_REPO_DIR = os.path.join(BASE_DIR, "data", "feast_repo")
FEAST_PARQUET_SOURCE = os.path.join(FEAST_REPO_DIR, "churn_features.parquet")
PROCESSED_TRAIN_FILE = os.path.join(BASE_DIR, "data", "processed", "train_features.parquet")
PROCESSED_VAL_FILE = os.path.join(BASE_DIR, "data", "processed", "val_features.parquet")
PROCESSED_TEST_FILE = os.path.join(BASE_DIR, "data", "processed", "test_features.parquet")

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

# Định nghĩa Feature View với độ chính xác Float64 chống mất mát dấu phẩy động
customer_feature_view = FeatureView(
    name="customer_churn_features",
    entities=[customer_entity],
    ttl=None,
    schema=[
        Field(name="age", dtype=Float64),
        Field(name="gender_encoded", dtype=Int64),
        Field(name="tenure", dtype=Float64),
        Field(name="usage_frequency", dtype=Float64),
        Field(name="support_calls", dtype=Float64),
        Field(name="payment_delay", dtype=Float64),
        Field(name="subscription_type_encoded", dtype=Int64),
        Field(name="contract_length_encoded", dtype=Int64),
        Field(name="total_spend", dtype=Float64),
        Field(name="last_interaction", dtype=Float64),
        Field(name="support_calls_per_tenure", dtype=Float64),
        Field(name="spend_per_tenure", dtype=Float64),
        Field(name="delay_ratio", dtype=Float64)
    ],
    online=True,
    source=file_source
)


def prepare_feast_data(sample_size: int = None):
    """
    Chuẩn bị dữ liệu đầu vào cho Feast Offline Store với timestamp hợp lệ.
    Hợp nhất toàn bộ 100% khách hàng duy nhất từ cả 3 tập train, val và test.
    """
    os.makedirs(FEAST_REPO_DIR, exist_ok=True)
    split_files = [PROCESSED_TRAIN_FILE, PROCESSED_VAL_FILE, PROCESSED_TEST_FILE]
    dfs = [pd.read_parquet(p) for p in split_files if os.path.exists(p)]
    if not dfs:
        raise FileNotFoundError(f"Không tìm thấy dữ liệu Parquet tại {PROCESSED_TRAIN_FILE}")

    df = pd.concat(dfs, ignore_index=True)
    df = df.drop_duplicates(subset=["customerid"], keep="first").reset_index(drop=True)

    if sample_size is not None and len(df) > sample_size:
        df = df.iloc[:sample_size].copy()
    else:
        df = df.copy()

    now = datetime.now(timezone.utc)
    rng = np.random.default_rng(42)
    if "event_timestamp" not in df.columns:
        jitter_sec = rng.integers(0, 3600, size=len(df))
        df["event_timestamp"] = (
            now
            - pd.to_timedelta(df["tenure"] * 30, unit="D")
            - pd.to_timedelta(jitter_sec, unit="s")
        )
    else:
        df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], utc=True)

    if "created_timestamp" not in df.columns:
        df["created_timestamp"] = now
    else:
        df["created_timestamp"] = pd.to_datetime(df["created_timestamp"], utc=True)

    for col in [
        "age", "tenure", "usage_frequency", "support_calls", "payment_delay",
        "total_spend", "last_interaction", "support_calls_per_tenure",
        "spend_per_tenure", "delay_ratio"
    ]:
        df[col] = df[col].astype("float64")

    for col in ["customerid", "gender_encoded", "subscription_type_encoded", "contract_length_encoded"]:
        df[col] = df[col].astype("int64")

    df.to_parquet(FEAST_PARQUET_SOURCE, index=False)
    print(f"[+] Đã tạo tệp Feast Offline Source: {FEAST_PARQUET_SOURCE} ({len(df):,} mẫu duy nhất)")


_FEATURE_STORE_INSTANCE = None
_REDIS_CLIENT = None
_REDIS_LAST_FAIL_TS = 0.0
_REDIS_RETRY_COOLDOWN_SEC = 30.0


def _init_redis_hot_cache():
    """Khởi tạo hoặc kết nối lại Redis Hot Cache với cơ chế cooldown chống khóa chết vĩnh viễn."""
    global _REDIS_CLIENT, _REDIS_LAST_FAIL_TS
    if _REDIS_CLIENT is not None and _REDIS_CLIENT is not False:
        try:
            _REDIS_CLIENT.ping()
            return _REDIS_CLIENT
        except Exception:
            _REDIS_CLIENT = None
            _REDIS_LAST_FAIL_TS = time.monotonic()

    now_mono = time.monotonic()
    if _REDIS_LAST_FAIL_TS > 0.0 and (now_mono - _REDIS_LAST_FAIL_TS) < _REDIS_RETRY_COOLDOWN_SEC:
        return None

    conn_str = os.getenv("AZURE_REDIS_CONNECTION_STRING") or os.getenv("REDIS_URL")
    if conn_str:
        try:
            import redis
            client = redis.from_url(
                conn_str,
                socket_timeout=0.2,
                socket_connect_timeout=0.2,
                decode_responses=True
            )
            client.ping()
            _REDIS_CLIENT = client
            _REDIS_LAST_FAIL_TS = 0.0
            return _REDIS_CLIENT
        except Exception:
            _REDIS_CLIENT = None
            _REDIS_LAST_FAIL_TS = now_mono

    redis_host = os.getenv("REDIS_HOST")
    if not redis_host:
        _REDIS_LAST_FAIL_TS = now_mono
        return None

    try:
        import redis
        port = int(os.getenv("REDIS_PORT", "6379"))
        pwd = os.getenv("AZURE_REDIS_PASSWORD") or os.getenv("REDIS_PASSWORD", None)
        ssl_env = os.getenv("REDIS_SSL")
        use_ssl = (ssl_env.lower() == "true") if ssl_env else (port == 6380)
        client = redis.Redis(
            host=redis_host,
            port=port,
            password=pwd,
            ssl=use_ssl,
            socket_timeout=0.2,
            socket_connect_timeout=0.2,
            decode_responses=True
        )
        client.ping()
        _REDIS_CLIENT = client
        _REDIS_LAST_FAIL_TS = 0.0
        return _REDIS_CLIENT
    except Exception:
        _REDIS_CLIENT = None
        _REDIS_LAST_FAIL_TS = now_mono
        return None


def get_redis_client():
    """Lấy kết nối Redis Cache cho Feast Online Store (Local / Azure Cache for Redis)."""
    return _init_redis_hot_cache()


def get_feature_store() -> FeatureStore:
    """Trả về phiên bản Feast FeatureStore Singleton tối ưu tài nguyên."""
    global _FEATURE_STORE_INSTANCE
    if _FEATURE_STORE_INSTANCE is None:
        _FEATURE_STORE_INSTANCE = FeatureStore(repo_path=FEAST_REPO_DIR)
        try:
            from feast.feature_view import FeatureViewState
            fv = _FEATURE_STORE_INSTANCE.get_feature_view("customer_churn_features")
            if hasattr(fv, "state") and fv.state != FeatureViewState.AVAILABLE_ONLINE:
                fv.state = FeatureViewState.AVAILABLE_ONLINE
                _FEATURE_STORE_INSTANCE.registry.apply_feature_view(
                    fv, project=_FEATURE_STORE_INSTANCE.project
                )
                _FEATURE_STORE_INSTANCE.registry.commit()
        except Exception:
            pass
    return _FEATURE_STORE_INSTANCE


def materialize_to_online_store(store: FeatureStore = None) -> FeatureStore:
    """Đồng bộ hóa dữ liệu từ Offline Store sang Online Store và làm mới Redis Hot Cache."""
    if store is None:
        store = get_feature_store()
    print("[*] Đang materialize dữ liệu sang Feast Online Store (SQLite/Redis)...")
    end_date = datetime.now(timezone.utc)
    start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    store.materialize(start_date=start_date, end_date=end_date)
    try:
        from feast.feature_view import FeatureViewState
        fv = store.get_feature_view("customer_churn_features")
        if hasattr(fv, "state") and fv.state != FeatureViewState.AVAILABLE_ONLINE:
            fv.state = FeatureViewState.AVAILABLE_ONLINE
            store.registry.apply_feature_view(fv, project=store.project)
            store.registry.commit()
    except Exception:
        pass

    redis_cli = _init_redis_hot_cache()
    if redis_cli is not None:
        try:
            stale_keys = list(redis_cli.scan_iter("churn_feat:*"))
            if stale_keys:
                redis_cli.delete(*stale_keys)
        except Exception:
            pass

    print("[+] Materialize thành công! Online Store đã sẵn sàng phục vụ real-time.")
    return store


def setup_feast_store():
    """Khởi tạo và apply metadata vào Feast Registry & Online Store."""
    prepare_feast_data()
    store = get_feature_store()
    print("[*] Đang apply Entity và FeatureView vào Feast Registry...")
    store.apply([customer_entity, customer_feature_view])
    return materialize_to_online_store(store)


def query_online_features(customer_ids: list[int]) -> dict:
    """Truy xuất đặc trưng online cho phục vụ dự đoán thời gian thực (Serving)."""
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

    redis_cli = get_redis_client()
    if redis_cli and len(customer_ids) == 1:
        cid = customer_ids[0]
        cache_key = f"churn_feat:{cid}"
        try:
            cached = redis_cli.hgetall(cache_key)
            if cached and len(cached) >= len(feature_names):
                result = {"customerid": [cid]}
                for fn in feature_names:
                    col = fn.split(":")[-1]
                    val = float(cached.get(col, 0.0))
                    result[fn] = [int(val) if "encoded" in col else val]
                return result
        except Exception:
            pass

    store = get_feature_store()
    entity_rows = [{"customerid": cid} for cid in customer_ids]
    response = store.get_online_features(features=feature_names, entity_rows=entity_rows)
    res_dict = response.to_dict()

    if redis_cli and len(customer_ids) == 1:
        cid = customer_ids[0]
        try:
            cache_payload = {}
            for fn in feature_names:
                col = fn.split(":")[-1]
                vals = res_dict.get(fn, [None])
                if vals and vals[0] is not None:
                    cache_payload[col] = str(vals[0])
            if cache_payload:
                redis_cli.hset(f"churn_feat:{cid}", mapping=cache_payload)
                redis_cli.expire(f"churn_feat:{cid}", 3600)
        except Exception:
            pass

    return res_dict


if __name__ == "__main__":
    store = setup_feast_store()
    test_cids = [1, 2, 3, 156624, 350098]
    features = query_online_features(test_cids)
    print("\n[*] Thử nghiệm truy vấn Online Features từ Feast cho Customer IDs 1, 2, 3, 156624, 350098:")
    print(features)
