"""
Script làm sạch và tái thiết lập dữ liệu suy luận (Inference Logs) thực tế.
Lấy mẫu từ test_features.parquet, dự đoán thực tế qua Champion & Challenger.
Đảm bảo phương sai thực tế, triệt tiêu lỗi suy biến thống kê (catastrophic cancellation).
Tuân thủ Invariant 01 và Invariant 02 (< 400 dòng).
"""
import os
import sys
import json
import sqlite3
import joblib
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DB_PATH = os.path.join(BASE_DIR, "data", "inference_logs.db")
TEST_PARQUET = os.path.join(BASE_DIR, "data", "processed", "test_features.parquet")
CHAMPION_MODEL_PATH = os.path.join(BASE_DIR, "data", "models", "champion_model.joblib")
CHALLENGER_MODEL_PATH = os.path.join(BASE_DIR, "data", "models", "random_forest.joblib")

from src.api.ab_testing import route_customer_to_model, CHAMPION_VERSION, CHALLENGER_VERSION, analyze_ab_test_performance
from src.api.utils import FEATURE_COLS


def reseed_logs(n_samples: int = 600):
    if not os.path.exists(TEST_PARQUET):
        print(f"[-] Không tìm thấy tệp {TEST_PARQUET}")
        return False

    df_test = pd.read_parquet(TEST_PARQUET)
    sample_df = df_test.sample(n=min(n_samples, len(df_test)), random_state=42).reset_index(drop=True)

    champ_art = joblib.load(CHAMPION_MODEL_PATH)
    champ_model = champ_art["model"]
    chal_model = joblib.load(CHALLENGER_MODEL_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS inference_logs")
    cur.execute("""
        CREATE TABLE inference_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            customer_id INTEGER,
            churn_prediction INTEGER,
            churn_probability REAL,
            features_json TEXT,
            model_version TEXT DEFAULT 'v2.0.0-champion'
        )
    """)

    records = []
    for idx, row in sample_df.iterrows():
        cid = int(row["customerid"]) if "customerid" in row else int(row.get("customer_id", 100000 + idx))
        route_type, ver_tag = route_customer_to_model(cid)

        feat_vals = [float(row[c]) for c in FEATURE_COLS]
        feat_df = pd.DataFrame([feat_vals], columns=FEATURE_COLS)

        if route_type == "challenger":
            clf = chal_model
            model_ver = CHALLENGER_VERSION
        else:
            clf = champ_model
            model_ver = CHAMPION_VERSION

        pred_cls = int(clf.predict(feat_df)[0])
        prob = float(clf.predict_proba(feat_df)[0][1]) if hasattr(clf, "predict_proba") else float(pred_cls)

        records.append((cid, pred_cls, round(prob, 4), json.dumps(feat_vals), model_ver))

    cur.executemany("""
        INSERT INTO inference_logs (customer_id, churn_prediction, churn_probability, features_json, model_version)
        VALUES (?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    conn.close()

    print(f"[+] Đã làm sạch và ghi mới {len(records)} bản ghi suy luận thực tế vào {DB_PATH}")
    stats_res = analyze_ab_test_performance()
    print(f"[+] Thống kê A/B Testing sau khi làm sạch: {stats_res.get('status')}")
    print(f"    - Tổng số mẫu: {stats_res.get('traffic_observed', {}).get('total_inferences')}")
    print(f"    - Champion samples: {stats_res.get('traffic_observed', {}).get('champion_samples')}")
    print(f"    - Challenger samples: {stats_res.get('traffic_observed', {}).get('challenger_samples')}")
    t_test_p = stats_res.get("hypothesis_testing", stats_res.get("hypothesis_test_welch_ttest", {})).get("p_value")
    print(f"    - T-test P-value: {t_test_p}")
    return True


if __name__ == "__main__":
    reseed_logs()
