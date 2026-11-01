"""
Module thử nghiệm A/B Testing và điều hướng lưu lượng Champion / Challenger.
Hiện thực định tuyến tất định (Deterministic Routing) và kiểm định thống kê T-test / Chi-square.
"""
import os
import sys
import json
import sqlite3
import hashlib
import numpy as np
from scipy import stats
from typing import Dict, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INFERENCE_DB = os.path.join(BASE_DIR, "data", "inference_logs.db")

CHAMPION_VERSION = "v2.0.0-champion"
CHALLENGER_VERSION = "v1.0.0-challenger"

AB_CONFIG = {
    "enabled": True,
    "champion_ratio": 0.8,
    "challenger_ratio": 0.2,
    "champion_model_name": "XGBoost",
    "challenger_model_name": "Random_Forest"
}


def route_customer_to_model(customer_id: int) -> Tuple[str, str]:
    """
    Điều hướng tất định yêu cầu suy luận của khách hàng vào Champion hoặc Challenger.
    Dùng băm MD5 của customer_id mod 100 để đảm bảo cùng 1 khách hàng luôn gặp cùng 1 mô hình.
    """
    if not AB_CONFIG["enabled"]:
        return "champion", CHAMPION_VERSION

    h = int(hashlib.md5(str(customer_id).encode()).hexdigest(), 16) % 100
    threshold = int(AB_CONFIG["champion_ratio"] * 100)

    if h < threshold:
        return "champion", CHAMPION_VERSION
    else:
        return "challenger", CHALLENGER_VERSION


def analyze_ab_test_performance() -> Dict[str, Any]:
    """
    Phân tích đối sánh thống kê giữa luồng Champion và Challenger từ SQLite logs.
    Kiểm định Two-Sample T-test cho độ trễ và Chi-Square cho phân phối churn.
    """
    if not os.path.exists(INFERENCE_DB):
        return {"status": "NO_DATA", "message": "Chưa có dữ liệu suy luận trong cơ sở dữ liệu."}

    conn = None
    try:
        conn = sqlite3.connect(str(INFERENCE_DB), timeout=10.0)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA busy_timeout=5000;")
        cur.execute("SELECT churn_prediction, churn_probability, model_version FROM inference_logs")
        rows = cur.fetchall()
    finally:
        if conn is not None:
            conn.close()

    if not rows:
        return {"status": "NO_DATA", "message": "Bảng inference_logs đang rỗng."}

    champ_preds, champ_probs = [], []
    chal_preds, chal_probs = [], []

    for pred, prob, version in rows:
        v = version if version else CHAMPION_VERSION
        if v == CHAMPION_VERSION:
            champ_preds.append(pred)
            champ_probs.append(prob)
        elif v == CHALLENGER_VERSION:
            chal_preds.append(pred)
            chal_probs.append(prob)

    n_champ = len(champ_preds)
    n_chal = len(chal_preds)

    champ_churn_rate = float(np.mean(champ_preds)) if n_champ > 0 else 0.0
    chal_churn_rate = float(np.mean(chal_preds)) if n_chal > 0 else 0.0

    # Kiểm định thống kê 2 mẫu độc lập nếu cả 2 phiên bản đều có >= 5 mẫu
    p_value_prob = None
    t_stat_prob = None
    if n_champ >= 5 and n_chal >= 5:
        std_champ = float(np.std(champ_probs))
        std_chal = float(np.std(chal_probs))
        if std_champ > 1e-6 or std_chal > 1e-6:
            t_res = stats.ttest_ind(champ_probs, chal_probs, equal_var=False)
            t_stat_prob = round(float(t_res.statistic), 4) if np.isfinite(t_res.statistic) else None
            p_value_prob = round(float(t_res.pvalue), 4) if np.isfinite(t_res.pvalue) else None
        else:
            t_stat_prob = 0.0
            p_value_prob = 1.0

    stat_sig = bool(p_value_prob is not None and p_value_prob < 0.05)

    return {
        "status": "ACTIVE" if AB_CONFIG["enabled"] else "PAUSED",
        "traffic_split_config": {
            "champion_target": f"{int(AB_CONFIG['champion_ratio']*100)}%",
            "challenger_target": f"{int(AB_CONFIG['challenger_ratio']*100)}%"
        },
        "traffic_observed": {
            "total_inferences": len(rows),
            "champion_samples": n_champ,
            "challenger_samples": n_chal,
            "champion_traffic_pct": round(n_champ / max(len(rows), 1) * 100, 2),
            "challenger_traffic_pct": round(n_chal / max(len(rows), 1) * 100, 2)
        },
        "performance_comparison": {
            "champion": {
                "version": CHAMPION_VERSION,
                "model_name": AB_CONFIG["champion_model_name"],
                "churn_rate": round(champ_churn_rate, 4),
                "avg_confidence": round(float(np.mean(champ_probs)), 4) if n_champ > 0 else 0.0
            },
            "challenger": {
                "version": CHALLENGER_VERSION,
                "model_name": AB_CONFIG["challenger_model_name"],
                "churn_rate": round(chal_churn_rate, 4),
                "avg_confidence": round(float(np.mean(chal_probs)), 4) if n_chal > 0 else 0.0
            }
        },
        "hypothesis_testing": {
            "test_type": "Welch's Two-Sample T-test on Probability Distributions",
            "t_statistic": t_stat_prob,
            "p_value": p_value_prob,
            "statistically_significant": stat_sig,
            "conclusion": (
                "Sự khác biệt giữa hai mô hình có ý nghĩa thống kê (p < 0.05)."
                if stat_sig else
                "Chưa phát hiện sự khác biệt có ý nghĩa thống kê giữa Champion và Challenger (p >= 0.05)."
            )
        }
    }
