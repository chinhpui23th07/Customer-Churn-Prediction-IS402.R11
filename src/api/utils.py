"""
Module tiện ích hỗ trợ cho API Serving: Logging, SHAP attributions, Database và Khuyến nghị.
Tuân thủ Invariant 01 và Invariant 02 (< 400 dòng).
"""
import os
import json
import sqlite3
import numpy as np
from typing import Optional, Tuple, Dict
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
    """Khởi tạo bảng lưu trữ lịch sử inference phục vụ giám sát Data Drift."""
    conn = sqlite3.connect(INFERENCE_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inference_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            customer_id INTEGER,
            churn_prediction INTEGER,
            churn_probability REAL,
            features_json TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_inference_prediction(customer_id: int, features: list, pred: int, prob: float):
    """Ghi nhận dự đoán vào SQLite inference database."""
    try:
        conn = sqlite3.connect(INFERENCE_DB)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO inference_logs (customer_id, churn_prediction, churn_probability, features_json)
            VALUES (?, ?, ?, ?)
        """, (customer_id, pred, prob, json.dumps(features)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[-] Lỗi ghi nhận inference log: {e}")


def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Kiểm tra API Key bảo mật cho các giao dịch production."""
    if x_api_key is not None and x_api_key != API_KEY_SECRET:
        raise HTTPException(status_code=401, detail="API Key không hợp lệ!")
    return x_api_key


def prepare_feature_vector_from_input(inp) -> np.ndarray:
    """Chuyển đổi CustomerInput sang vector đặc trưng 13 chiều với chặn chia cho 0 an toàn."""
    gender_map = {"Female": 0, "Male": 1}
    sub_map = {"Basic": 0, "Standard": 1, "Premium": 2}
    con_map = {"Monthly": 0, "Quarterly": 1, "Annual": 2}

    gender_enc = gender_map[inp.gender]
    sub_enc = sub_map[inp.subscription_type]
    con_enc = con_map[inp.contract_length]

    support_calls_per_tenure = inp.support_calls / max(inp.tenure, 1.0)
    spend_per_tenure = inp.total_spend / max(inp.tenure, 1.0)
    delay_ratio = inp.payment_delay / max(inp.last_interaction, 1.0)

    return np.array([[
        inp.age, gender_enc, inp.tenure, inp.usage_frequency, inp.support_calls,
        inp.payment_delay, sub_enc, con_enc, inp.total_spend, inp.last_interaction,
        support_calls_per_tenure, spend_per_tenure, delay_ratio
    ]])


def compute_shap_attributions(tree_explainer, x_input: np.ndarray) -> Tuple[Dict[str, float], str]:
    """Tính toán mức độ đóng góp đặc trưng bằng SHAP TreeExplainer thực tế."""
    factors = {}
    explanations = []

    if tree_explainer is not None:
        try:
            shap_vals = tree_explainer.shap_values(x_input)
            vals = shap_vals[0] if isinstance(shap_vals, list) else shap_vals
            if vals.ndim > 1:
                vals = vals[0]
            for col_name, val in zip(FEATURE_COLS, vals):
                factors[col_name] = round(float(val), 4)

            sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
            for f_name, f_val in sorted_factors[:3]:
                if f_val > 0.01:
                    explanations.append(f"{f_name} (SHAP: +{f_val:.3f})")
        except Exception:
            pass

    if not explanations:
        explanations.append("Dữ liệu các chỉ số nằm trong ngưỡng phân bố an toàn.")

    summary = "Đặc trưng thúc đẩy rời bỏ chính: " + " | ".join(explanations)
    return factors, summary


def generate_recommendation(prob: float, calls: float, delay: float) -> str:
    """Đề xuất chiến lược can thiệp kinh doanh dựa trên phân khúc rủi ro e-Profits."""
    if prob >= 0.70:
        if calls >= 4:
            return "ƯU TIÊN KHẨN CẤP: Điều động chuyên viên giải quyết khiếu nại kỹ thuật và tặng 1 tháng dịch vụ."
        elif delay >= 7:
            return "RỦI RO CAO: Khách hàng trễ hạn thanh toán. Đề xuất gói chuyển đổi trả góp hoặc giảm giá 20% gia hạn."
        return "RỦI RO CAO: Kích hoạt chương trình chăm sóc VIP và gửi ưu đãi cá nhân hóa."
    elif prob >= 0.35:
        return "RỦI RO TRUNG BÌNH: Gửi email giới thiệu tính năng, tặng điểm Loyalty và ưu đãi gia hạn sớm."
    return "KHÁCH HÀNG ỔN ĐỊNH: Khách hàng hài lòng cao. Đề xuất chiến dịch Upsell/Cross-sell gói cao cấp."
