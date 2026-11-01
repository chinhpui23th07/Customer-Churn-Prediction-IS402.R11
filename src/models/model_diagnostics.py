"""
Module chẩn đoán mô hình nâng cao (Model Diagnostics & Error Analysis).
Sinh biểu đồ Learning Curves, Calibration Curves và Phân tích chi tiết False Positives / False Negatives.
"""
import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import learning_curve
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    confusion_matrix, accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "data", "models")
IMAGES_DIR = os.path.join(BASE_DIR, "docs", "images")
CHAMPION_MODEL_PATH = os.path.join(MODELS_DIR, "champion_model.joblib")
TEST_PARQUET = os.path.join(PROCESSED_DIR, "test_features.parquet")
TRAIN_PARQUET = os.path.join(PROCESSED_DIR, "train_features.parquet")
OUTPUT_ERROR_JSON = os.path.join(PROCESSED_DIR, "error_analysis_report.json")

FEATURE_COLS = [
    "age", "gender_encoded", "tenure", "usage_frequency", "support_calls",
    "payment_delay", "subscription_type_encoded", "contract_length_encoded",
    "total_spend", "last_interaction", "support_calls_per_tenure",
    "spend_per_tenure", "delay_ratio"
]


def setup_plot_style():
    """Thiết lập đồ họa phong cách Oceanic chuyên nghiệp."""
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "sans-serif"]
    plt.rcParams["axes.edgecolor"] = "#CBD5E1"
    plt.rcParams["axes.linewidth"] = 1.0


def generate_learning_curves(model, X_train, y_train, output_path: str, max_samples: int = 25000):
    """Tính toán và vẽ Learning Curves (Đường cong học tập biểu diễn quy mô dữ liệu vs ROC-AUC)."""
    print("[*] Đang sinh biểu đồ Learning Curves...")
    setup_plot_style()
    if len(X_train) > max_samples:
        idx = np.random.RandomState(42).choice(len(X_train), max_samples, replace=False)
        X_sub = X_train.iloc[idx]
        y_sub = y_train.iloc[idx]
    else:
        X_sub = X_train
        y_sub = y_train

    train_sizes, train_scores, val_scores = learning_curve(
        estimator=model,
        X=X_sub,
        y=y_sub,
        train_sizes=np.linspace(0.15, 1.0, 5),
        cv=3,
        scoring="roc_auc",
        n_jobs=-1
    )

    tr_mean = np.mean(train_scores, axis=1)
    tr_std = np.std(train_scores, axis=1)
    val_mean = np.mean(val_scores, axis=1)
    val_std = np.std(val_scores, axis=1)

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    ax.plot(train_sizes, tr_mean, "o-", color="#0F766E", label="Training Score (ROC-AUC)", linewidth=2)
    ax.fill_between(train_sizes, tr_mean - tr_std, tr_mean + tr_std, alpha=0.15, color="#0F766E")

    ax.plot(train_sizes, val_mean, "s--", color="#F59E0B", label="Cross-Validation Score", linewidth=2)
    ax.fill_between(train_sizes, val_mean - val_std, val_mean + val_std, alpha=0.15, color="#F59E0B")

    ax.set_title("Đường Cong Học Tập Mô Hình (Learning Curves - XGBoost Champion)", fontsize=12, fontweight="bold", pad=12, color="#0A192F")
    ax.set_xlabel("Số Lượng Mẫu Huấn Luyện (Training Samples)", fontsize=10, fontweight="600")
    ax.set_ylabel("Điểm Số ROC-AUC", fontsize=10, fontweight="600")
    ax.set_ylim(0.95, 1.005)
    ax.legend(loc="lower right", frameon=True, facecolor="#F8FAFC")
    ax.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"[+] Đã lưu Learning Curves tại: {output_path}")


def generate_calibration_curve(y_true, y_prob, output_path: str):
    """Tính toán và vẽ đường chuẩn hóa xác suất (Probability Calibration Curve)."""
    print("[*] Đang sinh biểu đồ Calibration Curve...")
    setup_plot_style()
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)

    fig, ax = plt.subplots(figsize=(7, 6), dpi=300)
    ax.plot([0, 1], [0, 1], "k--", label="Hiệu chuẩn lý tưởng (Perfectly Calibrated)", alpha=0.6)
    ax.plot(prob_pred, prob_true, "s-", color="#2563EB", label="XGBoost Champion", linewidth=2.2, markersize=6)

    ax.set_title("Đường Hiệu Chuẩn Xác Suất (Reliability Calibration Curve)", fontsize=12, fontweight="bold", pad=12, color="#0A192F")
    ax.set_xlabel("Xác Suất Dự Đoán Trung Bình (Mean Predicted Probability)", fontsize=10, fontweight="600")
    ax.set_ylabel("Tần Suất Thực Tế (Fraction of Positives)", fontsize=10, fontweight="600")
    ax.legend(loc="upper left", frameon=True, facecolor="#F8FAFC")
    ax.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"[+] Đã lưu Calibration Curve tại: {output_path}")


def run_error_analysis(model, X_test, y_test, output_json: str, output_img: str) -> dict:
    """Phân tích chuyên sâu các ca dự đoán sai (False Positives và False Negatives)."""
    print("[*] Đang tiến hành phân tích lỗi chuyên sâu (Error Analysis)...")
    setup_plot_style()
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    fp_mask = (y_test == 0) & (y_pred == 1)
    fn_mask = (y_test == 1) & (y_pred == 0)
    tp_mask = (y_test == 1) & (y_pred == 1)
    tn_mask = (y_test == 0) & (y_pred == 0)

    tn_count = int(tn_mask.sum())
    fp_count = int(fp_mask.sum())
    fn_count = int(fn_mask.sum())
    tp_count = int(tp_mask.sum())

    fp_df = X_test[fp_mask]
    fn_df = X_test[fn_mask]

    acc = round(float(accuracy_score(y_test, y_pred)), 4) if len(y_test) > 0 else 0.0
    prec = round(float(precision_score(y_test, y_pred, zero_division=0)), 4) if len(y_test) > 0 else 0.0
    rec = round(float(recall_score(y_test, y_pred, zero_division=0)), 4) if len(y_test) > 0 else 0.0
    f1 = round(float(f1_score(y_test, y_pred, zero_division=0)), 4) if len(y_test) > 0 else 0.0
    roc_auc = round(float(roc_auc_score(y_test, y_prob)), 4) if len(np.unique(y_test)) >= 2 else 0.5

    analysis = {
        "confusion_breakdown": {
            "true_negatives": tn_count,
            "false_positives": fp_count,
            "false_negatives": fn_count,
            "true_positives": tp_count
        },
        "counts": {
            "true_negative": tn_count,
            "false_positive": fp_count,
            "false_negative": fn_count,
            "true_positive": tp_count,
            "true_negatives": tn_count,
            "false_positives": fp_count,
            "false_negatives": fn_count,
            "true_positives": tp_count
        },
        "metrics": {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "roc_auc": roc_auc
        },
        "false_positives_profile": {
            "count": fp_count,
            "avg_support_calls": round(float(fp_df["support_calls"].mean()), 2) if fp_count > 0 else 0.0,
            "avg_payment_delay": round(float(fp_df["payment_delay"].mean()), 2) if fp_count > 0 else 0.0,
            "avg_total_spend": round(float(fp_df["total_spend"].mean()), 2) if fp_count > 0 else 0.0,
            "risk_driver_note": "Khách hàng duy trì dịch vụ nhưng bị nhầm do số ngày trễ thanh toán hoặc cuộc gọi hỗ trợ tăng đột biến."
        },
        "false_negatives_profile": {
            "count": fn_count,
            "avg_support_calls": round(float(fn_df["support_calls"].mean()), 2) if fn_count > 0 else 0.0,
            "avg_payment_delay": round(float(fn_df["payment_delay"].mean()), 2) if fn_count > 0 else 0.0,
            "avg_total_spend": round(float(fn_df["total_spend"].mean()), 2) if fn_count > 0 else 0.0,
            "risk_driver_note": "Khách hàng rời bỏ nhưng có ít cuộc gọi hỗ trợ, rời bỏ âm thầm mà không khiếu nại."
        }
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"[+] Báo cáo Error Analysis đã lưu tại: {output_json}")

    # Vẽ biểu đồ Error Breakdown
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=300)
    labels = ["False Positives (Báo Động Nhầm)", "False Negatives (Bỏ Sót Rủi Ro)"]
    counts = [fp_count, fn_count]
    colors = ["#F59E0B", "#EF4444"]

    ax1.bar(labels, counts, color=colors, edgecolor="#1E293B", width=0.5)
    for i, c in enumerate(counts):
        ax1.annotate(str(c), xy=(i, c), xytext=(0, 4), textcoords="offset points", ha="center", fontweight="bold")
    ax1.set_title("Số Lượng Ca Dự Đoán Sai (Classification Errors)", fontsize=11, fontweight="bold", color="#0A192F")
    ax1.set_ylabel("Số lượng mẫu (Samples)", fontsize=9, fontweight="600")
    ax1.grid(True, linestyle="--", alpha=0.5)

    prob_fp = y_prob[fp_mask] if fp_count > 0 else [0.5]
    prob_fn = y_prob[fn_mask] if fn_count > 0 else [0.5]
    ax2.boxplot([prob_fp, prob_fn], tick_labels=["FP Probabilities", "FN Probabilities"], patch_artist=True,
                boxprops=dict(facecolor="#93C5FD", color="#1E40AF"))
    ax2.set_title("Phân Bố Điểm Xác Suất Của Các Ca Sai", fontsize=11, fontweight="bold", color="#0A192F")
    ax2.set_ylabel("Xác Suất Dự Đoán (Probability)", fontsize=9, fontweight="600")
    ax2.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_img)
    plt.close()
    print(f"[+] Biểu đồ Error Analysis đã lưu tại: {output_img}")
    return analysis


def run_full_diagnostics():
    """Hàm điều phối chạy trọn vẹn quy trình chẩn đoán mô hình."""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    art = joblib.load(CHAMPION_MODEL_PATH)
    model = art["model"]

    test_df = pd.read_parquet(TEST_PARQUET)
    train_df = pd.read_parquet(TRAIN_PARQUET)

    X_train = train_df[FEATURE_COLS]
    y_train = train_df["churn"]
    X_test = test_df[FEATURE_COLS]
    y_test = test_df["churn"]

    y_prob = model.predict_proba(X_test)[:, 1]

    lc_path = os.path.join(IMAGES_DIR, "learning_curves.png")
    cal_path = os.path.join(IMAGES_DIR, "calibration_curve.png")
    err_img = os.path.join(IMAGES_DIR, "error_analysis.png")

    generate_learning_curves(model, X_train, y_train, lc_path)
    generate_calibration_curve(y_test, y_prob, cal_path)
    run_error_analysis(model, X_test, y_test, OUTPUT_ERROR_JSON, err_img)
    print("[+] Hoàn tất toàn bộ quy trình chẩn đoán mô hình!")


if __name__ == "__main__":
    run_full_diagnostics()
