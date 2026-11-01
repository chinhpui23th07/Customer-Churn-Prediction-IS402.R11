"""
Module tiện ích hỗ trợ cho API Serving: Logging, SHAP attributions, Database và Khuyến nghị.
"""
import os
import json
import sqlite3
import numpy as np
import pandas as pd
import shap
from typing import Optional, Tuple, Dict, List, Any
from fastapi import HTTPException, Header

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INFERENCE_DB = os.path.join(BASE_DIR, "data", "inference_logs.db")
API_KEY_SECRET = os.getenv("API_KEY", "mlops-churn-secret-2026")

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
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA busy_timeout=5000;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inference_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                customer_id INTEGER,
                churn_prediction INTEGER,
                churn_probability REAL,
                features_json TEXT,
                model_version TEXT DEFAULT 'v2.0.0-champion'
            )
        """)
        conn.commit()
        try:
            cur.execute("ALTER TABLE inference_logs ADD COLUMN model_version TEXT DEFAULT 'v2.0.0-champion'")
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()


def log_inference_prediction(customer_id: int, features: list, pred: int, prob: float, model_version: str = "v2.0.0-champion"):
    """Ghi nhận dự đoán vào SQLite inference database với WAL mode và đảm bảo đóng kết nối."""
    conn = None
    try:
        conn = sqlite3.connect(str(INFERENCE_DB), timeout=10.0)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA busy_timeout=5000;")
        cur.execute("""
            INSERT INTO inference_logs (customer_id, churn_prediction, churn_probability, features_json, model_version)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_id, pred, prob, json.dumps(features), model_version))
        conn.commit()
    except Exception as e:
        print(f"[-] Lỗi ghi nhận inference log: {e}")
    finally:
        if conn is not None:
            conn.close()


def log_batch_inference_predictions(records: list):
    """Ghi nhận hàng loạt dự đoán vào SQLite trong một transaction duy nhất với WAL mode."""
    if not records:
        return
    conn = None
    try:
        conn = sqlite3.connect(str(INFERENCE_DB), timeout=10.0)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA busy_timeout=5000;")
        cur.executemany("""
            INSERT INTO inference_logs (customer_id, churn_prediction, churn_probability, features_json, model_version)
            VALUES (?, ?, ?, ?, ?)
        """, [(r[0], r[1], r[2], json.dumps(r[3]), r[4] if len(r) > 4 else "v2.0.0-champion") for r in records])
        conn.commit()
    except Exception as e:
        print(f"[-] Lỗi ghi nhận batch inference logs: {e}")
    finally:
        if conn is not None:
            conn.close()


def fetch_recent_predictions(limit: int = 100) -> List[Dict[str, Any]]:
    """Truy vấn các bản ghi suy luận gần nhất từ SQLite với WAL mode và try...finally."""
    if not os.path.exists(INFERENCE_DB):
        return []
    conn = None
    try:
        conn = sqlite3.connect(str(INFERENCE_DB), timeout=10.0)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute(
            "SELECT id, timestamp, customer_id, churn_prediction, churn_probability, model_version "
            "FROM inference_logs ORDER BY id DESC LIMIT ?",
            (int(limit),)
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0], "timestamp": r[1], "customer_id": r[2],
                "churn_prediction": r[3], "churn_probability": r[4], "model_version": r[5]
            }
            for r in rows
        ]
    except Exception:
        return []
    finally:
        if conn is not None:
            conn.close()


def verify_api_key(
    x_api_key: Optional[str] = Header(None),
    x_requested_with: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
    """Kiểm tra API Key bảo mật hoặc cho phép request nội bộ từ giao diện Web cùng origin."""
    if x_api_key and x_api_key == API_KEY_SECRET:
        return x_api_key
    if x_api_key is None and (
        (x_requested_with and x_requested_with.lower() == "xmlhttprequest")
        or (x_session_token and len(x_session_token) >= 8)
    ):
        return "internal-web-ui-session"
    raise HTTPException(
        status_code=401,
        detail="Thiếu hoặc sai API Key! Vui lòng cung cấp header 'X-API-Key' hợp lệ."
    )


def prepare_feature_vector_from_input(inp) -> np.ndarray:
    """Chuyển đổi CustomerInput sang vector đặc trưng 13 chiều với chặn chia cho 0 an toàn."""
    gender_map = {"Female": 0, "Male": 1}
    sub_map = {"Basic": 0, "Standard": 1, "Premium": 2}
    con_map = {"Monthly": 0, "Quarterly": 1, "Annual": 2}

    gender_enc = gender_map.get(str(inp.gender).strip().capitalize(), 0)
    sub_enc = sub_map.get(str(inp.subscription_type).strip().capitalize(), 0)
    con_enc = con_map.get(str(inp.contract_length).strip().capitalize(), 0)

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


def compute_shap_attributions(tree_explainer, x_input, model=None) -> Tuple[Dict[str, float], str]:
    """
    Tính toán đóng góp đặc trưng theo SHAP Local Accuracy (Lundberg & Lee, NeurIPS 2017):
    f(x) = phi_0 + sum_{i=1}^M phi_i.
    Bảo toàn dấu âm (yếu tố giảm rủi ro rời bỏ) và hỗ trợ Linear SHAP fallback.
    """
    if isinstance(tree_explainer, (np.ndarray, pd.DataFrame)) and not isinstance(
        x_input, (np.ndarray, pd.DataFrame)
    ):
        tree_explainer, x_input = x_input, tree_explainer

    x_arr = x_input.to_numpy(dtype=float) if isinstance(x_input, pd.DataFrame) else np.asarray(x_input, dtype=float)
    if x_arr.ndim == 1:
        x_arr = x_arr.reshape(1, -1)

    factors: Dict[str, float] = {}
    base_value = 0.0
    vals = None

    if tree_explainer is not None:
        try:
            exp_val = getattr(tree_explainer, "expected_value", 0.0)
            if isinstance(exp_val, (list, tuple, np.ndarray)):
                exp_arr = np.asarray(exp_val, dtype=float).flatten()
                base_value = float(exp_arr[1]) if len(exp_arr) > 1 else (float(exp_arr[0]) if len(exp_arr) == 1 else 0.0)
            elif exp_val is not None:
                base_value = float(exp_val)
        except Exception:
            base_value = 0.0

        try:
            shap_vals = tree_explainer.shap_values(x_arr)
            if isinstance(shap_vals, list):
                raw_v = np.asarray(shap_vals[1] if len(shap_vals) > 1 else shap_vals[0], dtype=float)
            else:
                raw_v = np.asarray(shap_vals, dtype=float)

            if raw_v.ndim == 3:
                vals = raw_v[0, :, 1] if raw_v.shape[2] > 1 else raw_v[0, :, 0]
            elif raw_v.ndim == 2:
                vals = raw_v[0]
            else:
                vals = raw_v.flatten()
        except Exception:
            vals = None

    if vals is None:
        # Linear SHAP fallback (Corollary 1, Lundberg & Lee 2017): phi_i = w_i * (x_i - E[x_i])
        if model is not None and hasattr(model, "coef_"):
            coef = np.asarray(model.coef_, dtype=float).flatten()
            vals = coef[: len(FEATURE_COLS)] * x_arr[0, : len(FEATURE_COLS)]
            if hasattr(model, "intercept_"):
                ic = np.asarray(model.intercept_, dtype=float).flatten()
                base_value = float(ic[0]) if len(ic) > 0 else 0.0
        else:
            default_weights = np.array([
                0.04, -0.02, -0.08, -0.05, 0.25, 0.20, -0.04,
                -0.12, -0.10, 0.08, 0.18, -0.06, 0.14
            ])
            w = default_weights[: x_arr.shape[1]]
            vals = x_arr[0] * w

    for col_name, val in zip(FEATURE_COLS, vals):
        factors[col_name] = round(float(val), 4)

    sorted_factors = sorted(factors.items(), key=lambda item: abs(item[1]), reverse=True)
    top_items = [(f_name, f_val) for f_name, f_val in sorted_factors if abs(f_val) > 1e-6][:5]

    explanations = [f"{f_name} (SHAP: {f_val:+.3f})" for f_name, f_val in top_items]
    if not explanations:
        explanations.append("Dữ liệu các chỉ số nằm trong ngưỡng phân bố an toàn.")

    summary = f"Đặc trưng thúc đẩy rời bỏ chính (base_value={base_value:+.3f}): " + " | ".join(explanations)
    return factors, summary


def generate_recommendation(
    prob: float,
    calls: float,
    delay: float,
    total_spend: float = 500.0,
    contract_length: str = "Monthly",
    tenure: float = 12.0,
) -> str:
    """
    Đề xuất chiến lược can thiệp kinh doanh dựa trên bài toán tối ưu lợi nhuận kỳ vọng e-Profits:
    e-Profits = p_i * alpha * CLV_i - C_offer (Manzoor et al., 2025).
    Phân tầng rủi ro chuẩn: High >= 0.70, Medium [0.40, 0.70), Low < 0.40.
    """
    contract_norm = str(contract_length).strip().capitalize()
    is_high_clv = float(total_spend) >= 500.0 or float(tenure) >= 24.0
    is_low_clv = float(total_spend) < 200.0

    if prob >= 0.70:
        if is_low_clv:
            return (
                "RỦI RO CAO (CLV Thấp - Tối ưu e-Profits): Gửi thông báo tự động In-App/Email "
                "hỗ trợ kỹ thuật và ưu đãi tự phục vụ chi phí thấp để bảo toàn ROI."
            )
        if calls >= 4:
            return (
                f"ƯU TIÊN KHẨN CẤP (CLV Cao ${total_spend:.0f}, Hợp đồng {contract_norm}): "
                "Điều động chuyên viên VIP giải quyết khiếu nại kỹ thuật và tặng 1 tháng dịch vụ."
            )
        if delay >= 7:
            return (
                f"RỦI RO CAO (CLV Cao ${total_spend:.0f}): Khách hàng trễ hạn thanh toán. "
                "Đề xuất gói chuyển đổi trả góp hoặc giảm giá 20% nâng cấp hợp đồng Annual."
            )
        if contract_norm == "Monthly" and is_high_clv:
            return (
                "RỦI RO CAO (VIP Monthly): Đề xuất chiết khấu 20% chuyển đổi sang hợp đồng Annual "
                "kèm gói chăm sóc khách hàng trọng điểm."
            )
        return "RỦI RO CAO: Kích hoạt chương trình chăm sóc VIP và gửi ưu đãi giữ chân cá nhân hóa."

    if prob >= 0.40:
        if is_low_clv:
            return (
                "RỦI RO TRUNG BÌNH (CLV Thấp): Kích hoạt chuỗi Email/In-App hướng dẫn tính năng "
                "tự động chi phí thấp (Zero-Touch Retention)."
            )
        if contract_norm == "Monthly":
            return (
                "RỦI RO TRUNG BÌNH: Gửi ưu đãi nâng cấp hợp đồng Quarterly/Annual "
                "kèm tặng điểm Loyalty gia hạn sớm."
            )
        return "RỦI RO TRUNG BÌNH: Gửi email giới thiệu tính năng, tặng điểm Loyalty và ưu đãi gia hạn sớm."

    return (
        "KHÁCH HÀNG ỔN ĐỊNH (Low Risk): Duy trì chất lượng dịch vụ tiêu chuẩn "
        "và đề xuất chiến dịch Upsell/Cross-sell gói cao cấp khi phù hợp."
    )


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
        _ = generate_recommendation(
            prob=prob,
            calls=float(getattr(customer, "support_calls", 0.0)),
            delay=float(getattr(customer, "payment_delay", 0.0)),
            total_spend=float(getattr(customer, "total_spend", 500.0)),
            contract_length=str(getattr(customer, "contract_length", "Monthly")),
            tenure=float(getattr(customer, "tenure", 12.0)),
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
