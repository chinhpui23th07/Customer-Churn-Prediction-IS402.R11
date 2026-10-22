#!/usr/bin/env python
"""
Generate Static SHAP Visualizations for Model Explainability.
Module tao bieu do SHAP Beeswarm Summary Plot va Waterfall Attribution
cho Champion Model phuc vu bao cao hoc thuat va giam sat XAI.
Tuan thu Invariant 01, 02 (<= 400 dong) va chuan do hoa 300 DPI.
"""
import os
import sys
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "data", "models")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
IMAGES_DIR = os.path.join(BASE_DIR, "docs", "images")

CHAMPION_PATH = os.path.join(MODELS_DIR, "champion_model.joblib")
TEST_PARQUET = os.path.join(PROCESSED_DIR, "test_features.parquet")
SUMMARY_PLOT_PATH = os.path.join(IMAGES_DIR, "shap_summary_plot.png")
WATERFALL_PLOT_PATH = os.path.join(IMAGES_DIR, "shap_waterfall.png")


def setup_plot_style():
    """Thiet lap thong so do hoa phong cach Oceanic chuan UIT va bao cao."""
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "sans-serif"]
    plt.rcParams["axes.edgecolor"] = "#CBD5E1"
    plt.rcParams["axes.linewidth"] = 1.0
    plt.rcParams["figure.dpi"] = 300
    plt.rcParams["savefig.dpi"] = 300


def load_artifacts_and_data(sample_size: int = 2000):
    """Doc Champion Model va tap test thuc te de tinh toan SHAP."""
    if not os.path.exists(CHAMPION_PATH):
        raise FileNotFoundError(f"Khong tim thay Champion Model tai: {CHAMPION_PATH}")
    if not os.path.exists(TEST_PARQUET):
        raise FileNotFoundError(f"Khong tim thay tap test parquet tai: {TEST_PARQUET}")

    print(f"[*] Dang nap Champion Model tu: {CHAMPION_PATH}")
    artifact = joblib.load(CHAMPION_PATH)
    model = artifact["model"] if isinstance(artifact, dict) and "model" in artifact else artifact
    feature_names = artifact.get("feature_names", None) if isinstance(artifact, dict) else None

    print(f"[*] Dang doc tap du lieu test tu: {TEST_PARQUET}")
    df_test = pd.read_parquet(TEST_PARQUET)

    if feature_names is None:
        exclude_cols = {"customerid", "event_timestamp", "created_timestamp", "churn"}
        feature_names = [c for c in df_test.columns if c not in exclude_cols]

    print(f"[*] So luong dac trung ({len(feature_names)}): {feature_names}")

    # Lay mau tieu bieu de tinh toan nhanh va phan bo chuan xac
    if len(df_test) > sample_size:
        df_sample = df_test.sample(n=sample_size, random_state=42).reset_index(drop=True)
    else:
        df_sample = df_test.copy().reset_index(drop=True)

    X_sample = df_sample[feature_names]
    y_sample = df_sample["churn"].values if "churn" in df_sample.columns else None

    return model, feature_names, X_sample, y_sample, df_sample


def generate_shap_plots():
    """Tinh toan TreeExplainer va xuat 2 bieu do SHAP 300 DPI."""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    setup_plot_style()

    model, feature_names, X_sample, y_sample, df_sample = load_artifacts_and_data(sample_size=2000)

    print("[*] Khoi tao SHAP TreeExplainer tren Champion Model...")
    explainer = shap.TreeExplainer(model)

    print("[*] Tinh toan SHAP values cho 2,000 mau test...")
    shap_explanation = explainer(X_sample)

    # 1. Sinh bieu do SHAP Beeswarm Summary Plot
    print(f"[*] Dang ve Beeswarm Summary Plot tai: {SUMMARY_PLOT_PATH}")
    fig = plt.figure(figsize=(11, 7))
    shap.plots.beeswarm(shap_explanation, max_display=13, show=False)
    plt.title("SHAP Feature Importance & Impact Distribution (Champion Model)", fontsize=13, fontweight="bold", pad=16, color="#0F172A")
    plt.xlabel("SHAP value (impact on model churn output)", fontsize=11, fontweight="medium", color="#1E293B")
    plt.tight_layout()
    plt.savefig(SUMMARY_PLOT_PATH, dpi=300, bbox_inches="tight")
    plt.close("all")
    print(f"[+] Da tao thanh cong: {SUMMARY_PLOT_PATH}")

    # 2. Sinh bieu do SHAP Waterfall Plot cho khach hang co nguy co roi bo cao
    print("[*] Tim kiem khach hang tieu bieu co nguy co roi bo cao (High Churn Risk)...")
    # Tinh toan xac suat du doan
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X_sample)[:, 1]
    else:
        probs = y_sample

    # Chon khach hang co xac suat roi bo cao va dac trung bien dong ro ret
    high_risk_candidates = np.where(probs > 0.85)[0]
    if len(high_risk_candidates) > 0:
        rep_idx = int(high_risk_candidates[0])
    elif y_sample is not None and np.any(y_sample == 1):
        rep_idx = int(np.where(y_sample == 1)[0][0])
    else:
        rep_idx = 0

    cid = df_sample.iloc[rep_idx].get("customerid", rep_idx)
    prob_val = probs[rep_idx] if probs is not None else 1.0
    print(f"[*] Khach hang duoc chon: index={rep_idx}, customerid={cid}, churn_prob={prob_val:.4f}")

    print(f"[*] Dang ve Waterfall Plot tai: {WATERFALL_PLOT_PATH}")
    fig = plt.figure(figsize=(11, 6))
    shap.plots.waterfall(shap_explanation[rep_idx], max_display=10, show=False)
    plt.title(
        f"SHAP Waterfall Attribution - High Churn Risk (Cust #{cid}, P(churn)={prob_val*100:.1f}%)",
        fontsize=12,
        fontweight="bold",
        pad=16,
        color="#0F172A"
    )
    plt.tight_layout()
    plt.savefig(WATERFALL_PLOT_PATH, dpi=300, bbox_inches="tight")
    plt.close("all")
    print(f"[+] Da tao thanh cong: {WATERFALL_PLOT_PATH}")

    # Kiem tra xac thuc file da ton tai va co dung luong hop le
    for p in [SUMMARY_PLOT_PATH, WATERFALL_PLOT_PATH]:
        if os.path.exists(p) and os.path.getsize(p) > 10000:
            print(f"[VERIFIED] {p} - Size: {os.path.getsize(p):,} bytes")
        else:
            raise RuntimeError(f"Loi: File {p} khong duoc tao hoac kich thuoc qua nho!")


if __name__ == "__main__":
    try:
        generate_shap_plots()
        print("\n[SUCCESS] Hoan tat sinh toan bo bieu do SHAP tinh chat luong cao (300 DPI)!")
        sys.exit(0)
    except Exception as exc:
        print(f"\n[ERROR] That bai khi sinh bieu do SHAP: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
