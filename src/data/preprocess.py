"""
Module tiền xử lý dữ liệu, kiểm soát rò rỉ (Leakage Prevention) và kỹ thuật đặc trưng.
Tuân thủ Invariant 01 (Clean Architecture) và Invariant 02 (< 400 dòng).
"""
import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_TRAIN_FILE = os.path.join(BASE_DIR, "data", "raw", "customer_churn_dataset-training-master.csv")
RAW_TEST_FILE = os.path.join(BASE_DIR, "data", "raw", "customer_churn_dataset-testing-master.csv")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

FEATURE_NAMES = [
    "age", "gender_encoded", "tenure", "usage_frequency", "support_calls",
    "payment_delay", "subscription_type_encoded", "contract_length_encoded",
    "total_spend", "last_interaction", "support_calls_per_tenure",
    "spend_per_tenure", "delay_ratio"
]

CATEGORY_MAPPINGS = {
    "gender": {"Female": 0, "Male": 1},
    "subscription_type": {"Basic": 0, "Standard": 1, "Premium": 2},
    "contract_length": {"Monthly": 0, "Quarterly": 1, "Annual": 2}
}


def clean_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa tên cột, chuyển kiểu và loại bỏ bản ghi thiếu."""
    cleaned = df.copy()
    cleaned.columns = [c.strip().lower().replace(" ", "_") for c in cleaned.columns]
    
    cleaned = cleaned.dropna(subset=["customerid"])
    if "churn" in cleaned.columns:
        cleaned = cleaned.dropna(subset=["churn"])
        cleaned["churn"] = cleaned["churn"].astype(int)
        
    cleaned["customerid"] = cleaned["customerid"].astype(int)
    return cleaned


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo các biến đặc trưng với cơ chế phòng ngừa chia cho 0 và lookahead bias.
    Sử dụng np.maximum(..., 1.0) thay cho các hằng số ma thuật tùy ý.
    """
    data = df.copy()
    
    data["gender_encoded"] = data["gender"].map(CATEGORY_MAPPINGS["gender"]).fillna(0).astype(int)
    data["subscription_type_encoded"] = data["subscription_type"].map(
        CATEGORY_MAPPINGS["subscription_type"]
    ).fillna(0).astype(int)
    data["contract_length_encoded"] = data["contract_length"].map(
        CATEGORY_MAPPINGS["contract_length"]
    ).fillna(0).astype(int)
    
    # Kỹ thuật đặc trưng tương tác tỷ lệ với chặn an toàn mẫu số >= 1.0
    data["support_calls_per_tenure"] = data["support_calls"] / np.maximum(data["tenure"], 1.0)
    data["spend_per_tenure"] = data["total_spend"] / np.maximum(data["tenure"], 1.0)
    data["delay_ratio"] = data["payment_delay"] / np.maximum(data["last_interaction"], 1.0)
    
    return data


def analyze_dataset_bias(df: pd.DataFrame, output_path: str):
    """
    Phân tích định lượng độ lệch và quy luật sinh dữ liệu tổng hợp Kaggle.
    Ghi nhận hiện tượng tỷ lệ churn 100% của nhóm Contract Length = Monthly.
    """
    stats = {}
    if "contract_length" in df.columns and "churn" in df.columns:
        contract_stats = df.groupby("contract_length")["churn"].agg(
            total_customers="count",
            churned_customers="sum",
            churn_rate="mean"
        ).to_dict(orient="index")
        stats["contract_length_distribution"] = contract_stats

    if "churn" in df.columns:
        total = len(df)
        churn_total = int(df["churn"].sum())
        stats["overall"] = {
            "total_records": total,
            "churn_count": churn_total,
            "churn_rate": float(churn_total / total),
            "monthly_churn_perfect_signal_note": (
                "Kaggle synthetic generator sets Monthly contract churn to 100%. "
                "Models exploit this strong deterministic rule."
            )
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"[+] Đã lưu phân tích độ lệch dữ liệu tại: {output_path}")


def run_pipeline():
    """Thực thi pipeline tiền xử lý với kiểm soát chặt chẽ rò rỉ dữ liệu."""
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    print("[*] Nạp dữ liệu thô từ 2 tệp nguồn...")
    
    df_train_raw = pd.read_csv(RAW_TRAIN_FILE)
    df_test_raw = pd.read_csv(RAW_TEST_FILE) if os.path.exists(RAW_TEST_FILE) else pd.DataFrame()
    print(f"    - Bản ghi train raw: {len(df_train_raw):,}")
    print(f"    - Bản ghi test raw:  {len(df_test_raw):,}")
    
    cleaned_train = clean_raw_data(df_train_raw)
    cleaned_test = clean_raw_data(df_test_raw) if not df_test_raw.empty else pd.DataFrame()
    
    # Hợp nhất và loại bỏ trùng lặp CustomerID triệt để
    combined = pd.concat([cleaned_train, cleaned_test], ignore_index=True)
    initial_count = len(combined)
    combined = combined.drop_duplicates(subset=["customerid"], keep="first")
    dedup_count = len(combined)
    dropped_duplicates = initial_count - dedup_count
    print(f"[+] Hợp nhất và khử trùng CustomerID:")
    print(f"    - Tổng bản ghi trước khử trùng: {initial_count:,}")
    print(f"    - Trùng lặp bị loại bỏ:         {dropped_duplicates:,}")
    print(f"    - Số khách hàng duy nhất (Unique): {dedup_count:,}")
    
    # Phân tích độ lệch dữ liệu
    bias_path = os.path.join(PROCESSED_DIR, "dataset_bias_analysis.json")
    analyze_dataset_bias(combined, bias_path)
    
    # Trích xuất đặc trưng
    df_feat = engineer_features(combined)
    
    X = df_feat[FEATURE_NAMES]
    y = df_feat["churn"]
    ids = df_feat["customerid"]
    
    # Phân chia Stratified 70% Train, 15% Validation, 15% Test
    X_train_full, X_test, y_train_full, y_test, id_train_full, id_test = train_test_split(
        X, y, ids, test_size=0.15, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val, id_train, id_val = train_test_split(
        X_train_full, y_train_full, id_train_full, test_size=0.17647, random_state=42, stratify=y_train_full
    )  # 0.17647 của 85% xấp xỉ 15% tổng thể
    
    # Xác minh kiểm soát rò rỉ dữ liệu (Customer Leakage Check)
    train_ids_set = set(id_train)
    val_ids_set = set(id_val)
    test_ids_set = set(id_test)
    
    assert len(train_ids_set & test_ids_set) == 0, "LỖI: Rò rỉ CustomerID giữa Train và Test!"
    assert len(train_ids_set & val_ids_set) == 0, "LỖI: Rò rỉ CustomerID giữa Train và Val!"
    assert len(val_ids_set & test_ids_set) == 0, "LỖI: Rò rỉ CustomerID giữa Val và Test!"
    print(f"[OK] Xác thực kiểm soát rò rỉ: 0 khách hàng trùng giữa các tập Train, Val, Test.")
    
    print(f"[+] Phân chia tập dữ liệu chuẩn học thuật:")
    print(f"    - Train set: {len(X_train):,} hàng ({len(X_train)/len(combined)*100:.1f}%)")
    print(f"    - Val set:   {len(X_val):,} hàng ({len(X_val)/len(combined)*100:.1f}%)")
    print(f"    - Test set:  {len(X_test):,} hàng ({len(X_test)/len(combined)*100:.1f}%)")
    
    # Chuẩn hóa chỉ học từ tập Train (Không Data Snooping)
    scaler = StandardScaler()
    scaler.fit(X_train)
    joblib.dump(scaler, os.path.join(PROCESSED_DIR, "scaler.joblib"))
    
    # Metadata tổng hợp
    meta = {
        "feature_names": FEATURE_NAMES,
        "category_mappings": CATEGORY_MAPPINGS,
        "unique_customers_total": int(dedup_count),
        "train_samples": int(len(X_train)),
        "val_samples": int(len(X_val)),
        "test_samples": int(len(X_test)),
        "churn_rate_train": float(y_train.mean()),
        "churn_rate_test": float(y_test.mean()),
        "customer_isolation_verified": True
    }
    with open(os.path.join(PROCESSED_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        
    now_utc = pd.Timestamp.now(tz="UTC")
    timestamps = pd.DataFrame({
        "event_timestamp": now_utc - pd.to_timedelta(combined["tenure"] * 30, unit="D"),
        "created_timestamp": now_utc
    }, index=combined.index)

    train_df = pd.concat([id_train, timestamps.loc[id_train.index], X_train, y_train], axis=1)
    val_df = pd.concat([id_val, timestamps.loc[id_val.index], X_val, y_val], axis=1)
    test_df = pd.concat([id_test, timestamps.loc[id_test.index], X_test, y_test], axis=1)
    
    train_df.to_parquet(os.path.join(PROCESSED_DIR, "train_features.parquet"), index=False)
    val_df.to_parquet(os.path.join(PROCESSED_DIR, "val_features.parquet"), index=False)
    test_df.to_parquet(os.path.join(PROCESSED_DIR, "test_features.parquet"), index=False)
    
    print(f"[+] Đã lưu dữ liệu định dạng Parquet kèm event_timestamp vào {PROCESSED_DIR}")
    return meta


if __name__ == "__main__":
    run_pipeline()
