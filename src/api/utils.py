"""
Module tiện ích hỗ trợ cho API Serving: Logging, SHAP attributions, Database và Khuyến nghị.
"""
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import hmac
import json
import sqlite3
import numpy as np
import pandas as pd
import shap
from typing import Optional, Tuple, Dict, List, Any
from fastapi import HTTPException, Header
from src.api.database import ensure_inference_schema
from src.resilience.retry_policy import RetryPolicy

_DB_RETRY = RetryPolicy(name="db_write_retry", max_attempts=3, initial_backoff=0.05, backoff_factor=2.0)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INFERENCE_DB = os.path.join(BASE_DIR, "data", "inference_logs.db")
API_KEY_SECRET = os.getenv("API_KEY") or ("" if os.getenv("APP_ENV") == "production" else "mlops-churn-secret-2026")

FEATURE_COLS = [
    "age", "gender_encoded", "tenure", "usage_frequency", "support_calls",
    "payment_delay", "subscription_type_encoded", "contract_length_encoded",
    "total_spend", "last_interaction", "support_calls_per_tenure",
    "spend_per_tenure", "delay_ratio"
]


def init_inference_db():
    """Khởi tạo bảng lưu trữ lịch sử inference phục vụ giám sát Data Drift và A/B Testing."""
    os.makedirs(os.path.dirname(str(INFERENCE_DB)), exist_ok=True)
    conn = sqlite3.connect(str(INFERENCE_DB), timeout=10.0)
    try:
        cur = conn.cursor()
        for p in ("PRAGMA journal_mode=WAL;", "PRAGMA synchronous=NORMAL;", "PRAGMA busy_timeout=5000;"):
            cur.execute(p)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inference_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                customer_id INTEGER,
                churn_prediction INTEGER,
                churn_probability REAL,
                features_json TEXT,
                model_version TEXT DEFAULT 'v2.0.0-champion',
                latency_ms REAL DEFAULT 0.0
            )
        """)
        conn.commit()
        ensure_inference_schema(conn)
    finally:
        conn.close()


def log_inference_prediction(
    customer_id: int,
    features: list,
    pred: int,
    prob: float,
    model_version: str = "v2.0.0-champion",
    latency_ms: float = 0.0,
):
    """Ghi nhận dự đoán vào SQLite inference database với WAL mode và RetryPolicy."""
    def _write():
        conn = None
        try:
            conn = sqlite3.connect(str(INFERENCE_DB), timeout=10.0)
            cur = conn.cursor()
            for p in ("PRAGMA journal_mode=WAL;", "PRAGMA synchronous=NORMAL;", "PRAGMA busy_timeout=5000;"):
                cur.execute(p)
            ensure_inference_schema(conn)
            cur.execute(
                "INSERT INTO inference_logs (customer_id, churn_prediction, churn_probability, features_json, model_version, latency_ms) VALUES (?, ?, ?, ?, ?, ?)",
                (customer_id, pred, prob, json.dumps(features), model_version, float(latency_ms)),
            )
            conn.commit()
        finally:
            if conn is not None:
                conn.close()
    try:
        _DB_RETRY.execute(_write)
    except Exception as e:
        print(f"[-] Lỗi ghi nhận inference log: {e}")


def log_batch_inference_predictions(records: list):
    """Ghi nhận hàng loạt dự đoán vào SQLite trong một transaction duy nhất với WAL mode và RetryPolicy."""
    if not records:
        return
    def _write_batch():
        conn = None
        try:
            conn = sqlite3.connect(str(INFERENCE_DB), timeout=10.0)
            cur = conn.cursor()
            for p in ("PRAGMA journal_mode=WAL;", "PRAGMA synchronous=NORMAL;", "PRAGMA busy_timeout=5000;"):
                cur.execute(p)
            ensure_inference_schema(conn)
            cur.executemany(
                "INSERT INTO inference_logs (customer_id, churn_prediction, churn_probability, features_json, model_version, latency_ms) VALUES (?, ?, ?, ?, ?, ?)",
                [(r[0], r[1], r[2], json.dumps(r[3]), r[4] if len(r) > 4 else "v2.0.0-champion", float(r[5]) if len(r) > 5 else 0.0) for r in records],
            )
            conn.commit()
        finally:
            if conn is not None:
                conn.close()
    try:
        _DB_RETRY.execute(_write_batch)
    except Exception as e:
        print(f"[-] Lỗi ghi nhận batch inference logs: {e}")


def fetch_recent_predictions(limit: int = 100) -> List[Dict[str, Any]]:
    """Truy vấn các bản ghi suy luận gần nhất từ SQLite với WAL mode và try...finally."""
    if not os.path.exists(INFERENCE_DB):
        return []
    conn = None
    try:
        conn = sqlite3.connect(str(INFERENCE_DB), timeout=10.0)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("SELECT id, timestamp, customer_id, churn_prediction, churn_probability, model_version FROM inference_logs ORDER BY id DESC LIMIT ?", (int(limit),))
        return [{"id": r[0], "timestamp": r[1], "customer_id": r[2], "churn_prediction": r[3], "churn_probability": r[4], "model_version": r[5]} for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        if conn is not None:
            conn.close()


def verify_api_key(
    x_api_key: Optional[str] = Header(None),
):
    """Verify API Key strictly using constant-time comparison and production fail-closed guard."""
    env_key = os.getenv("API_KEY", "").strip()
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if env_key:
        configured_secret = env_key
    elif app_env == "production":
        configured_secret = ""
    else:
        configured_secret = API_KEY_SECRET
    if not configured_secret:
        raise HTTPException(
            status_code=503,
            detail="API Key chưa được cấu hình trên máy chủ (APP_ENV=production yêu cầu biến môi trường API_KEY).",
        )
    if x_api_key and hmac.compare_digest(x_api_key, configured_secret):
        return x_api_key
    raise HTTPException(status_code=401, detail="Thiếu hoặc sai API Key! Vui lòng cung cấp header 'X-API-Key' hợp lệ.")



def prepare_feature_vector_from_input(inp) -> np.ndarray:
    """Chuyển đổi CustomerInput sang vector đặc trưng 13 chiều với chặn chia cho 0 an toàn."""
    g_map, s_map, c_map = {"Female": 0, "Male": 1}, {"Basic": 0, "Standard": 1, "Premium": 2}, {"Monthly": 0, "Quarterly": 1, "Annual": 2}
    gender_enc = g_map.get(str(inp.gender).strip().capitalize(), 0)
    sub_enc = s_map.get(str(inp.subscription_type).strip().capitalize(), 0)
    con_enc = c_map.get(str(inp.contract_length).strip().capitalize(), 0)

    support_calls_per_tenure = inp.support_calls / max(inp.tenure, 1.0)
    spend_per_tenure = inp.total_spend / max(inp.tenure, 1.0)
    delay_ratio = inp.payment_delay / max(inp.last_interaction, 1.0)

    return np.array([[
        inp.age, gender_enc, inp.tenure, inp.usage_frequency, inp.support_calls,
        inp.payment_delay, sub_enc, con_enc, inp.total_spend, inp.last_interaction,
        support_calls_per_tenure, spend_per_tenure, delay_ratio
    ]])


def extract_raw_feature_vector(inp) -> np.ndarray:
    """Alias tương thích cho prepare_feature_vector_from_input."""
    return prepare_feature_vector_from_input(inp)


from src.models.explain import compute_shap_attributions  # noqa: F401,E402


from src.economics.retention_optimizer import (
    compute_optimal_retention_threshold,
    compute_expected_retention_profit,
    generate_recommendation,
    segment_customers_by_uplift,
)


def evaluate_retention_decision(prob: float, total_spend: float, cate_uplift: Optional[float] = None) -> Dict[str, Any]:
    """Compute e-Profits expected retention profit, optimal threshold, and CATE uplift quadrant."""
    clv = max(float(total_spend), 0.0)
    opt_thresh = compute_optimal_retention_threshold(residual_clv=clv)
    exp_profit = compute_expected_retention_profit(prob=prob, residual_clv=clv)
    uplift_est = float(cate_uplift) if cate_uplift is not None else round(0.25 * float(prob), 4)
    quadrant = segment_customers_by_uplift(uplift=uplift_est, baseline_churn=prob)
    return {
        "optimal_threshold": round(opt_thresh, 4),
        "expected_profit": round(exp_profit, 2),
        "uplift_quadrant": quadrant,
    }


def run_model_inference(
    clf, raw_vec: np.ndarray, scaler, use_scaled: bool, customer: Optional[Any] = None
) -> Tuple[np.ndarray, int, float, str]:
    """Thực thi suy luận mô hình và phân tầng mức độ rủi ro chuẩn (0.40 / 0.70)."""
    x_input = scaler.transform(raw_vec) if use_scaled and scaler is not None else raw_vec
    if hasattr(clf, "feature_names_in_"):
        x_eval = pd.DataFrame(x_input, columns=clf.feature_names_in_)
    else:
        x_eval = x_input
    pred_class = int(clf.predict(x_eval)[0])
    prob = float(clf.predict_proba(x_eval)[0][1]) if hasattr(clf, "predict_proba") else float(pred_class)
    risk_tier = "High Risk" if prob >= 0.70 else ("Medium Risk" if prob >= 0.40 else "Low Risk")
    if customer is not None:
        decision = evaluate_retention_decision(prob=prob, total_spend=float(getattr(customer, "total_spend", 500.0)))
        _ = generate_recommendation(
            prob=prob,
            calls=float(getattr(customer, "support_calls", 0.0)),
            delay=float(getattr(customer, "payment_delay", 0.0)),
            total_spend=float(getattr(customer, "total_spend", 500.0)),
            contract_length=str(getattr(customer, "contract_length", "Monthly")),
            tenure=float(getattr(customer, "tenure", 12.0)),
            quadrant=decision["uplift_quadrant"] if prob < 0.70 else None,
        )
    return x_input, pred_class, prob, risk_tier


def check_feast_online_status(online_store_db: str) -> str:
    """Kiểm tra chính xác trạng thái kết nối Feast Online Store (Redis vs SQLite)."""
    from src.features.feature_store import get_redis_client
    sqlite_ok = os.path.exists(online_store_db)
    redis_ok = False
    try:
        r = get_redis_client()
        if r is not None:
            redis_ok = bool(r.ping())
    except Exception:
        redis_ok = False

    if redis_ok and sqlite_ok:
        return "CONNECTED (Redis Cache & SQLite)"
    elif sqlite_ok:
        return "CONNECTED (SQLite Only - Redis Offline)"
    return "CONNECTED (Redis Cache Only)" if redis_ok else "NOT_FOUND"
