"""
Module giám sát Data Drift và Model Drift (Mục Giám sát Drift Bài tập 11).
Sử dụng kiểm định thống kê Kolmogorov-Smirnov (KS-test), PSI và Evidently AI.
Tuân thủ Invariant 01 (Clean Architecture) và Invariant 02 (< 400 dòng).
"""
import os
import sys
import json
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

try:
    from evidently import Report
    from evidently.presets import DataDriftPreset
    EVIDENTLY_AVAILABLE = True
except Exception:
    EVIDENTLY_AVAILABLE = False

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
REF_PARQUET = os.path.join(BASE_DIR, "data", "processed", "train_features.parquet")
INFERENCE_DB = os.path.join(BASE_DIR, "data", "inference_logs.db")
OUTPUT_DRIFT_JSON = os.path.join(BASE_DIR, "data", "processed", "drift_metrics.json")
OUTPUT_DRIFT_HTML = os.path.join(BASE_DIR, "docs", "drift_report.html")

FEATURE_COLS = [
    "age", "gender_encoded", "tenure", "usage_frequency", "support_calls",
    "payment_delay", "subscription_type_encoded", "contract_length_encoded",
    "total_spend", "last_interaction", "support_calls_per_tenure",
    "spend_per_tenure", "delay_ratio"
]


def calculate_psi(expected: np.ndarray, actual: np.ndarray, num_buckets: int = 10) -> float:
    """
    Tính chỉ số Population Stability Index (PSI) chuẩn khoa học.
    Sử dụng phân vị của phân phối cơ sở (Expected - Training baseline) để chia bin,
    kết hợp mở rộng vô cực và Laplace smoothing để tránh chia cho 0 và log(0).
    """
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    percentiles = np.linspace(0, 100, num_buckets + 1)
    breakpoints = np.percentile(expected, percentiles)
    breakpoints = np.unique(breakpoints)
    if len(breakpoints) < 2:
        return 0.0

    # Mở rộng biên để bao trùm mọi giá trị ngoại lai của actual
    breakpoints[0] = -np.inf
    breakpoints[-1] = np.inf

    exp_counts, _ = np.histogram(expected, bins=breakpoints)
    act_counts, _ = np.histogram(actual, bins=breakpoints)

    k = len(breakpoints) - 1
    exp_pct = (exp_counts + 1) / (len(expected) + k)
    act_pct = (act_counts + 1) / (len(actual) + k)

    psi_val = np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct))
    return float(np.round(psi_val, 4))


def run_drift_analysis(current_df: pd.DataFrame = None, p_val_threshold: float = 0.05,
                       simulate_drift: bool = False) -> dict:
    """
    Thực hiện phân tích Data Drift giữa dữ liệu huấn luyện cơ sở (Train baseline)
    và dữ liệu suy luận Production (Inference logs từ SQLite hoặc Production test stream).
    """
    import sqlite3
    ref_df = pd.read_parquet(REF_PARQUET)

    # Đọc dữ liệu từ SQLite inference logs nếu có
    if current_df is None and os.path.exists(INFERENCE_DB):
        try:
            conn = sqlite3.connect(INFERENCE_DB)
            cur = conn.cursor()
            cur.execute("SELECT features_json FROM inference_logs ORDER BY id DESC LIMIT 5000")
            rows = cur.fetchall()
            conn.close()
            if len(rows) >= 10:
                data_list = [json.loads(r[0]) for r in rows]
                current_df = pd.DataFrame(data_list, columns=FEATURE_COLS)
        except Exception:
            pass

    # Nếu chưa có đủ log suy luận thực tế, lấy mẫu từ tập Test đại diện cho Production stream
    if current_df is None:
        test_df = pd.read_parquet(os.path.join(BASE_DIR, "data", "processed", "test_features.parquet"))
        current_df = test_df.sample(n=min(len(test_df), 10000), random_state=42)[FEATURE_COLS].copy()

    if simulate_drift:
        current_df = current_df.copy()
        current_df["payment_delay"] = current_df["payment_delay"] * 2.2 + 5.0
        current_df["support_calls"] = current_df["support_calls"] * 2.0 + 3.0

    drift_report = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "reference_samples": len(ref_df),
        "current_samples": len(current_df),
        "features": {},
        "drifted_features_count": 0,
        "total_features": len(FEATURE_COLS),
        "dataset_drift_detected": False
    }

    drifted_count = 0

    for col in FEATURE_COLS:
        if col in ref_df.columns and col in current_df.columns:
            ref_vals = ref_df[col].dropna().values
            cur_vals = current_df[col].dropna().values

            # Kolmogorov-Smirnov Test
            ks_res = ks_2samp(ref_vals, cur_vals)
            p_val = float(ks_res.pvalue)
            stat = float(ks_res.statistic)

            # PSI Metric
            psi = calculate_psi(ref_vals, cur_vals)

            is_drifted = (p_val < p_val_threshold) or (psi > 0.25)
            if is_drifted:
                drifted_count += 1

            drift_report["features"][col] = {
                "ks_statistic": round(stat, 4),
                "p_value": round(p_val, 5),
                "psi_score": psi,
                "drift_detected": bool(is_drifted),
                "drift_level": "High" if psi > 0.25 else ("Moderate" if psi > 0.1 else "Stable")
            }

    drift_report["drifted_features_count"] = drifted_count
    drift_share = drifted_count / len(FEATURE_COLS)
    drift_report["drift_share"] = round(drift_share, 4)
    # Nếu trên 33% đặc trưng bị trôi dạt -> Cảnh báo Dataset Drift
    drift_report["dataset_drift_detected"] = bool(drift_share > 0.33)

    # Lưu JSON
    os.makedirs(os.path.dirname(OUTPUT_DRIFT_JSON), exist_ok=True)
    with open(OUTPUT_DRIFT_JSON, "w", encoding="utf-8") as f:
        json.dump(drift_report, f, indent=2, ensure_ascii=False)

    # Tạo file báo cáo HTML trực quan
    generate_html_report(drift_report, ref_df=ref_df, current_df=current_df)

    return drift_report


def generate_html_report(report: dict, ref_df: pd.DataFrame = None, current_df: pd.DataFrame = None):
    """Tạo báo cáo HTML theo dõi Drift bằng Evidently AI với fallback giao diện Stitch."""
    os.makedirs(os.path.dirname(OUTPUT_DRIFT_HTML), exist_ok=True)
    if EVIDENTLY_AVAILABLE and ref_df is not None and current_df is not None:
        try:
            r = Report([DataDriftPreset()])
            ref_sub = ref_df[FEATURE_COLS].sample(n=min(len(ref_df), 3000), random_state=42)
            cur_sub = current_df[FEATURE_COLS].sample(n=min(len(current_df), 3000), random_state=42)
            snapshot = r.run(reference_data=ref_sub, current_data=cur_sub)
            snapshot.save_html(OUTPUT_DRIFT_HTML)
            print(f"[+] Đã tạo báo cáo Evidently AI HTML: {OUTPUT_DRIFT_HTML}")
            return
        except Exception as e:
            print(f"[-] Fallback giao diện Stitch do: {e}")

    status_badge = (
        '<span style="background:#EF4444;color:#FFF;padding:4px 12px;border-radius:20px;font-weight:bold;">PHÁT HIỆN DRIFT</span>'
        if report["dataset_drift_detected"]
        else '<span style="background:#10B981;color:#FFF;padding:4px 12px;border-radius:20px;font-weight:bold;">DỮ LIỆU ỔN ĐỊNH</span>'
    )

    rows_html = ""
    for f_name, f_data in report["features"].items():
        badge_color = "#10B981" if f_data["drift_level"] == "Stable" else ("#F59E0B" if f_data["drift_level"] == "Moderate" else "#EF4444")
        rows_html += f"""
        <tr style="border-bottom: 1px solid #334155;">
            <td style="padding:10px;font-weight:600;color:#F8FAFC;">{f_name}</td>
            <td style="padding:10px;color:#94A3B8;">{f_data['ks_statistic']}</td>
            <td style="padding:10px;color:#94A3B8;">{f_data['p_value']}</td>
            <td style="padding:10px;color:#94A3B8;">{f_data['psi_score']}</td>
            <td style="padding:10px;"><span style="color:{badge_color};font-weight:600;">{f_data['drift_level']}</span></td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>ChurnGuard MLOps - Báo Cáo Data Drift</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0A192F; color: #F8FAFC; padding: 24px; }}
        .container {{ max-width: 960px; margin: auto; background: #112240; padding: 28px; border-radius: 14px; border: 1px solid #233554; }}
        h1 {{ color: #F8FAFC; margin-bottom: 8px; }}
        .kpi {{ display: flex; gap: 16px; margin: 20px 0; }}
        .card {{ flex: 1; background: #1E3A5F; padding: 16px; border-radius: 8px; text-align: center; }}
        .card .num {{ font-size: 24px; font-weight: bold; color: #F59E0B; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
        th {{ background: #0F2942; color: #38BDF8; padding: 12px; text-align: left; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="container">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h1>Báo Cáo Giám Sát Data Drift</h1>
            {status_badge}
        </div>
        <p style="color:#94A3B8;">Thời điểm đo: {report['timestamp']} | Reference Samples: {report['reference_samples']} | Current Samples: {report['current_samples']}</p>
        
        <div class="kpi">
            <div class="card"><div class="num">{report['drifted_features_count']} / {report['total_features']}</div><div style="color:#94A3B8;font-size:12px;">ĐẶC TRƯNG BỊ DRIFT</div></div>
            <div class="card"><div class="num">{report['drift_share'] * 100:.1f}%</div><div style="color:#94A3B8;font-size:12px;">TỶ LỆ TRÔI DẠT</div></div>
            <div class="card"><div class="num">KS-Test + PSI</div><div style="color:#94A3B8;font-size:12px;">PHƯƠNG PHÁP KIỂM ĐỊNH</div></div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>TÊN ĐẶC TRƯNG</th>
                    <th>KS STATISTIC</th>
                    <th>P-VALUE</th>
                    <th>PSI SCORE</th>
                    <th>TRẠNG THÁI</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
</body>
</html>"""

    with open(OUTPUT_DRIFT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[+] Đã tạo báo cáo HTML Drift: {OUTPUT_DRIFT_HTML}")


if __name__ == "__main__":
    rep = run_drift_analysis()
    print("\n================== KẾT QUẢ KIỂM ĐỊNH DATA DRIFT ==================")
    print(f"Tổng số đặc trưng kiểm định: {rep['total_features']}")
    print(f"Số đặc trưng bị Drift: {rep['drifted_features_count']}")
    print(f"Tỷ lệ Drift: {rep['drift_share'] * 100:.2f}%")
    print(f"Trạng thái Dataset Drift: {'CÓ DRIFT!' if rep['dataset_drift_detected'] else 'KHÔNG DRIFT (ỔN ĐỊNH)'}")
    print(f"[+] Kết quả đã lưu vào: {OUTPUT_DRIFT_JSON}")
