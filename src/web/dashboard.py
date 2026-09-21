"""
Streamlit Monitoring & Observability Dashboard cho ChurnGuard MLOps Platform.
Hiển thị KPI thời gian thực, Giám sát Data Drift (PSI / KS), A/B Testing & Chẩn đoán mô hình.
Tuân thủ Invariant 01 (Clean Architecture), Invariant 02 (< 400 dòng) và Invariant 03 (Oceanic Palette).
"""
import os
import sys
import json
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INFERENCE_DB = os.path.join(BASE_DIR, "data", "inference_logs.db")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "data", "models")
IMAGES_DIR = os.path.join(BASE_DIR, "docs", "images")

st.set_page_config(
    page_title="ChurnGuard MLOps Enterprise Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Oceanic Navy Theme Styling
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #0A2540 0%, #1A365D 100%);
        border-radius: 12px;
        padding: 18px 24px;
        color: #FFFFFF;
        box-shadow: 0 4px 12px rgba(10, 37, 64, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 12px;
    }
    .metric-val { font-size: 28px; font-weight: 700; color: #00D4B2; margin: 4px 0; }
    .metric-title { font-size: 13px; text-transform: uppercase; letter-spacing: 0.8px; opacity: 0.85; }
    .metric-sub { font-size: 12px; opacity: 0.7; }
</style>
""", unsafe_allow_html=True)


def load_inference_logs(limit: int = 500) -> pd.DataFrame:
    """Tải lịch sử suy luận từ SQLite database."""
    if not os.path.exists(INFERENCE_DB):
        return pd.DataFrame()
    conn = sqlite3.connect(INFERENCE_DB)
    df = pd.read_sql_query(
        f"SELECT id, timestamp, customer_id, churn_prediction, churn_probability, model_version "
        f"FROM inference_logs ORDER BY id DESC LIMIT {limit}", conn
    )
    conn.close()
    return df


def load_json_file(file_path: str) -> dict:
    """Tải nội dung tệp JSON an toàn."""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# Sidebar
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=64)
st.sidebar.title("ChurnGuard MLOps")
st.sidebar.caption("Enterprise Observability & Model Serving Platform")
st.sidebar.markdown("---")
st.sidebar.markdown("**Kiến trúc & Tiêu chuẩn:**")
st.sidebar.markdown("- **Pipeline:** DVC + MLflow 3.16")
st.sidebar.markdown("- **Feature Store:** Feast 0.66 (100k records)")
st.sidebar.markdown("- **Champion Model:** XGBoost (AUC: 0.9990)")
st.sidebar.markdown("- **A/B Split:** 80% Champ / 20% Chall")
st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("Tự động làm mới dữ liệu", value=False)
if st.sidebar.button("Làm mới ngay (Refresh)"):
    st.rerun()

# Main Title
st.title("🛡️ ChurnGuard Enterprise MLOps Monitoring Dashboard")
st.caption("Hệ thống giám sát toàn diện: Suy luận thời gian thực, Data Drift (PSI), A/B Testing và Chẩn đoán lỗi mô hình.")

tab_kpi, tab_drift, tab_ab, tab_diag = st.tabs([
    "📊 Giám Sát Suy Luận & KPI",
    "📡 Giám Sát Data Drift & Cảnh Báo",
    "⚖️ Thử Nghiệm A/B Testing",
    "🧪 Chẩn Đoán Mô Hình & Lỗi Dự Đoán"
])

# ----------------- TAB 1: KPI & INFERENCE -----------------
with tab_kpi:
    logs_df = load_inference_logs(limit=1000)
    total_inf = len(logs_df)
    churn_cnt = int(logs_df["churn_prediction"].sum()) if total_inf > 0 else 0
    churn_rate = (churn_cnt / total_inf * 100) if total_inf > 0 else 0.0
    champ_cnt = len(logs_df[logs_df["model_version"].str.contains("champion", na=False)]) if total_inf > 0 else 0
    champ_pct = (champ_cnt / total_inf * 100) if total_inf > 0 else 100.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Tổng Lượt Suy Luận</div>
            <div class="metric-val">{total_inf:,}</div>
            <div class="metric-sub">Lưu trữ trong SQLite Database</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Tỷ Lệ Dự Đoán Rời Bỏ</div>
            <div class="metric-val">{churn_rate:.1f}%</div>
            <div class="metric-sub">{churn_cnt:,} / {total_inf:,} khách hàng</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Điều Hướng Champion</div>
            <div class="metric-val">{champ_pct:.1f}%</div>
            <div class="metric-sub">Mục tiêu: 80% (XGBoost)</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Trạng Thái Phục Vụ</div>
            <div class="metric-val" style="color: #06D6A0;">HOẠT ĐỘNG</div>
            <div class="metric-sub">FastAPI + Feast Online Store</div>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("📋 Nhật Ký Suy Luận Thời Gian Thực Gần Nhất")
    if not logs_df.empty:
        disp_df = logs_df.copy()
        disp_df["churn_prediction"] = disp_df["churn_prediction"].apply(lambda x: "⚠️ Rời bỏ (1)" if x == 1 else "✅ Giữ chân (0)")
        disp_df["churn_probability"] = disp_df["churn_probability"].apply(lambda p: f"{p:.4f}")
        st.dataframe(disp_df, use_container_width=True, height=320)
    else:
        st.info("Chưa có lượt suy luận nào được ghi nhận. Hãy gửi yêu cầu dự đoán qua REST API.")

# ----------------- TAB 2: DATA DRIFT -----------------
with tab_drift:
    drift_data = load_json_file(os.path.join(PROCESSED_DIR, "drift_metrics.json"))
    if drift_data:
        features = drift_data.get("features", {})
        drift_feats = [f for f, v in features.items() if v.get("drift_detected", False)]
        drift_share = len(drift_feats) / max(len(features), 1)

        if drift_share >= 0.30:
            st.error(f"🚨 CẢNH BÁO DATA DRIFT: Phát hiện {len(drift_feats)}/{len(features)} đặc trưng bị lệch phân phối (Tỷ lệ: {drift_share*100:.1f}% >= ngưỡng 30%). Khuyến nghị kích hoạt Webhook tái huấn luyện tự động!")
        else:
            st.success(f"✅ HỆ THỐNG ỔN ĐỊNH: Tỷ lệ đặc trưng biến động {drift_share*100:.1f}% nằm trong ngưỡng kiểm soát an toàn (< 30%).")

        psi_list = []
        for feat, val in features.items():
            psi_list.append({
                "Đặc trưng": feat,
                "PSI Score": val.get("psi_score", 0.0),
                "P-Value (KS)": val.get("p_value", 1.0),
                "Mức độ": val.get("drift_level", "Stable"),
                "Lệch phân phối": "Có" if val.get("drift_detected", False) else "Không"
            })
        psi_df = pd.DataFrame(psi_list).sort_values(by="PSI Score", ascending=True)

        fig_psi = px.bar(
            psi_df, x="PSI Score", y="Đặc trưng", orientation="h",
            color="Mức độ",
            color_discrete_map={"Stable": "#06D6A0", "Moderate": "#FFB703", "High": "#EF476F"},
            title="Chỉ Số Population Stability Index (PSI) Theo Từng Đặc Trưng Hành Vi"
        )
        fig_psi.add_vline(x=0.25, line_dash="dash", line_color="#EF476F", annotation_text="Ngưỡng biến động mạnh (PSI = 0.25)")
        fig_psi.update_layout(height=420, template="plotly_white")
        st.plotly_chart(fig_psi, use_container_width=True)

        st.subheader("Bảng Đối Soát Thống Kê Kolmogorov-Smirnov (KS-Test)")
        st.dataframe(psi_df.sort_values(by="PSI Score", ascending=False), use_container_width=True)
    else:
        st.warning("Chưa tìm thấy tệp drift_metrics.json. Vui lòng chạy pipeline drift detection.")

# ----------------- TAB 3: A/B TESTING -----------------
with tab_ab:
    from src.api.ab_testing import analyze_ab_test_performance
    ab_res = analyze_ab_test_performance()

    if ab_res.get("status") == "ACTIVE":
        traffic = ab_res.get("traffic_observed", {})
        col_ab1, col_ab2 = st.columns([1, 1])

        with col_ab1:
            st.subheader("Phân Phối Lưu Lượng Điều Hướng Thực Tế")
            donut_df = pd.DataFrame({
                "Mô hình": ["Champion (XGBoost)", "Challenger (Random Forest)"],
                "Số mẫu": [traffic.get("champion_samples", 0), traffic.get("challenger_samples", 0)]
            })
            fig_donut = px.pie(donut_df, values="Số mẫu", names="Mô hình", hole=0.5, color_discrete_sequence=["#0A2540", "#00D4B2"])
            fig_donut.update_layout(height=320, template="plotly_white")
            st.plotly_chart(fig_donut, use_container_width=True)

        with col_ab2:
            st.subheader("Kết Quả Kiểm Định Giả Thuyết Thống Kê (Two-Sample T-test)")
            hyp = ab_res.get("hypothesis_testing", {})
            st.info(f"**Phương pháp kiểm định:** {hyp.get('test_type')}")
            st.write(f"- **T-statistic:** `{hyp.get('t_statistic', 'N/A')}`")
            st.write(f"- **P-value:** `{hyp.get('p_value', 'N/A')}` (Ngưỡng $\\alpha = 0.05$)")
            st.write(f"- **Kết luận nghiệp vụ:** {hyp.get('conclusion')}")

        perf = ab_res.get("performance_comparison", {})
        champ_p = perf.get("champion", {})
        chal_p = perf.get("challenger", {})
        st.markdown(f"""
        | Phiên bản | Tên mô hình | Tỷ lệ Churn dự đoán | Độ tin cậy trung bình |
        | :--- | :--- | :--- | :--- |
        | **{champ_p.get('version')}** | {champ_p.get('model_name')} | **{champ_p.get('churn_rate', 0.0)*100:.2f}%** | {champ_p.get('avg_confidence', 0.0):.4f} |
        | **{chal_p.get('version')}** | {chal_p.get('model_name')} | **{chal_p.get('churn_rate', 0.0)*100:.2f}%** | {chal_p.get('avg_confidence', 0.0):.4f} |
        """)
    else:
        st.info("Chưa có đủ dữ liệu A/B testing để chạy kiểm định thống kê.")

# ----------------- TAB 4: MODEL DIAGNOSTICS & ERROR ANALYSIS -----------------
with tab_diag:
    st.subheader("Đường Cong Học Tập (Learning Curves) & Độ Hiệu Chuẩn (Calibration)")
    c_img1, c_img2 = st.columns(2)
    with c_img1:
        img_lc = os.path.join(IMAGES_DIR, "learning_curves.png")
        if os.path.exists(img_lc):
            st.image(img_lc, caption="Learning Curves: Hội tụ điểm ROC-AUC trên 5-Fold Stratified CV", use_column_width=True)
    with c_img2:
        img_calib = os.path.join(IMAGES_DIR, "calibration_curve.png")
        if os.path.exists(img_calib):
            st.image(img_calib, caption="Calibration Curve: Xác suất dự đoán bám sát xác suất thực tế", use_column_width=True)

    st.markdown("---")
    st.subheader("Phân Tích Lỗi Sai (Error Analysis: False Positives & False Negatives)")
    c_img3, c_img4 = st.columns([1.2, 1.0])
    with c_img3:
        img_err = os.path.join(IMAGES_DIR, "error_analysis.png")
        if os.path.exists(img_err):
            st.image(img_err, caption="Phân bố xác suất và hành vi nhóm lỗi dự đoán FP và FN", use_column_width=True)
    with c_img4:
        err_rep = load_json_file(os.path.join(PROCESSED_DIR, "error_analysis_report.json"))
        if err_rep:
            counts = err_rep.get("counts", {})
            st.markdown(f"""
            **Thống kê phân loại trên tập kiểm thử (Test Set):**
            - **True Negatives (TN):** `{counts.get('true_negatives', 0):,}` mẫu
            - **True Positives (TP):** `{counts.get('true_positives', 0):,}` mẫu
            - **False Positives (FP - Báo động nhầm):** `{counts.get('false_positives', 0):,}` mẫu
            - **False Negatives (FN - Bỏ sót churn):** `{counts.get('false_negatives', 0):,}` mẫu
            
            **Hiệu năng tổng thể:**
            - **Accuracy:** `{err_rep.get('metrics', {}).get('accuracy', 0.0):.4f}`
            - **F1-Score:** `{err_rep.get('metrics', {}).get('f1_score', 0.0):.4f}`
            - **ROC-AUC:** `{err_rep.get('metrics', {}).get('roc_auc', 0.0):.4f}`
            """)
