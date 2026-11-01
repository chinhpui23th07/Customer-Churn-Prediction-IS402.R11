"""
Probability Calibration, Brier Score & SHAP Local Accuracy Test Suite (Audit Team 4).
Kiem thu toan ven: Hieu chuan xac suat mo hinh Champion va chi so Brier Score (< 0.05),
an toan khi danh gia tap du lieu don lop (single-class guard),
tien de Lundberg & Lee (NeurIPS 2017) SHAP Local Accuracy (Efficiency Axiom),
bao toan huong tac dong am cua dac trung (negative directional attribution),
co che fallback LinearExplainer tren Logistic Regression va tinh nhat quan
phan tich cohort error slicing.
"""

import os
import pathlib
import joblib
import numpy as np
import pandas as pd
import pytest
import shap
from sklearn.metrics import brier_score_loss, confusion_matrix

from src.api.main import _build_shap_explainer
from src.api.utils import FEATURE_COLS, compute_shap_attributions
from src.models.train_pipeline import evaluate_model_performance

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "data" / "models"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def test_champion_model_probability_calibration_and_brier_score():
    """
    Kiem thu xac suat du doan va tinh hieu chuan (Calibration) cua mo hinh Champion:
    - Brier Score tren tap test 66,332 mau phai nho hon 0.05.
    - Xac suat du doan chia thanh cac khoang phan vi tang dan dong dieu voi ty le
      roi bo thuc nghiem (Monotonic Calibration).
    """
    champion_path = MODELS_DIR / "champion_model.joblib"
    test_parquet = PROCESSED_DIR / "test_features.parquet"

    assert champion_path.exists(), f"Champion model not found at: {champion_path}"
    assert test_parquet.exists(), f"Test parquet not found at: {test_parquet}"

    artifact = joblib.load(champion_path)
    model = artifact["model"] if isinstance(artifact, dict) else artifact

    test_df = pd.read_parquet(test_parquet)
    y_true = test_df["churn"].values.astype(int)
    probs = model.predict_proba(test_df[FEATURE_COLS])[:, 1]

    # Tinh Brier Score: 1/N * sum (p_i - y_i)^2
    bs = brier_score_loss(y_true, probs)
    assert bs < 0.05, f"Champion Brier score too high: {bs:.6f} >= 0.05"

    # Phan nhom xac suat de kiem tra do don dieu: [0.0, 0.2), [0.2, 0.4), [0.8, 1.0]
    low_mask = (probs >= 0.0) & (probs < 0.20)
    mid_mask = (probs >= 0.20) & (probs < 0.40)
    high_mask = (probs >= 0.80) & (probs <= 1.0)

    low_rate = float(np.mean(y_true[low_mask])) if np.sum(low_mask) > 0 else 0.0
    mid_rate = float(np.mean(y_true[mid_mask])) if np.sum(mid_mask) > 0 else 0.0
    high_rate = float(np.mean(y_true[high_mask])) if np.sum(high_mask) > 0 else 0.0

    assert low_rate < 0.05, f"Low probability bucket has unexpectedly high churn rate: {low_rate:.4f}"
    assert low_rate < mid_rate < high_rate, (
        f"Empirical churn rate not monotonic across probability buckets: "
        f"low={low_rate:.4f}, mid={mid_rate:.4f}, high={high_rate:.4f}"
    )


def test_evaluate_model_performance_single_class_guard():
    """
    Kiem thu co che bao ve chong ngoai le khi danh gia tap du lieu don lop (all 0s hoac all 1s).
    Scikit-learn roc_auc_score thong thuong se raise ValueError: Only one class present.
    evaluate_model_performance phai bat ngoai le nay va gan an toan roc_auc = 0.5.
    """
    n_samples = 100

    # Kich ban 1: Tap nhan toan 0 (khong co khach hang roi bo)
    y_true_zeros = np.zeros(n_samples, dtype=int)
    y_pred_zeros = np.zeros(n_samples, dtype=int)
    y_prob_zeros = np.full(n_samples, 0.05, dtype=float)

    metrics_zeros = evaluate_model_performance("single_class_zeros", y_true_zeros, y_pred_zeros, y_prob_zeros)
    assert metrics_zeros["roc_auc"] == 0.5, f"Expected roc_auc 0.5 for all-zero class, got {metrics_zeros['roc_auc']}"
    assert metrics_zeros["accuracy"] == 1.0
    assert not np.isnan(metrics_zeros["roc_auc"])

    # Kich ban 2: Tap nhan toan 1 (tat ca khach hang roi bo)
    y_true_ones = np.ones(n_samples, dtype=int)
    y_pred_ones = np.ones(n_samples, dtype=int)
    y_prob_ones = np.full(n_samples, 0.95, dtype=float)

    metrics_ones = evaluate_model_performance("single_class_ones", y_true_ones, y_pred_ones, y_prob_ones)
    assert metrics_ones["roc_auc"] == 0.5, f"Expected roc_auc 0.5 for all-one class, got {metrics_ones['roc_auc']}"
    assert metrics_ones["accuracy"] == 1.0
    assert not np.isnan(metrics_ones["roc_auc"])


def test_shap_efficiency_axiom_local_accuracy():
    """
    Kiem thu tien de hieu qua cuc bo (Local Accuracy / Efficiency Axiom)
    theo Lundberg & Lee (NeurIPS 2017, Equation 1):
        f(x) = phi_0 + sum_{j=1}^M phi_j(x)
    Voi 10 ho so khach hang da dang tu test set, do lech tuyet doi
    giua tong SHAP values + phi_0 va model output margin phai nho hon 1e-4.
    """
    champion_path = MODELS_DIR / "champion_model.joblib"
    test_parquet = PROCESSED_DIR / "test_features.parquet"

    artifact = joblib.load(champion_path)
    model = artifact["model"] if isinstance(artifact, dict) else artifact

    test_df = pd.read_parquet(test_parquet)
    # Chon 10 ho so khach hang da dang tren cac chi so
    sample_indices = [0, 50, 200, 1000, 5000, 10000, 20000, 35000, 50000, 65000]
    sample_df = test_df.iloc[sample_indices][FEATURE_COLS]

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample_df)
    expected_value = float(explainer.expected_value)
    output_margins = model.predict(sample_df, output_margin=True)

    for i in range(len(sample_indices)):
        local_sum = expected_value + float(np.sum(shap_values[i]))
        target_margin = float(output_margins[i])
        diff = abs(local_sum - target_margin)
        assert diff < 1e-4, (
            f"SHAP Efficiency Axiom violated at sample {i}: "
            f"local_sum={local_sum:.6f}, margin={target_margin:.6f}, diff={diff:.6e}"
        )


def test_shap_negative_directional_attribution_preservation():
    """
    Kiem thu bao toan huong tac dong am cua cac dac trung giu chan (retention drivers).
    Khach hang trung thanh (Tenure cao, SupportCalls=0, PaymentDelay=0, Contract=Annual):
    - Cac dac trung support_calls, payment_delay, va tenure phai co SHAP value < 0
      (thuc day giam xac suat roi bo).
    - Chuoi tom tat khong chua dinh dang dau xung dot ('+-').
    """
    champion_path = MODELS_DIR / "champion_model.joblib"
    artifact = joblib.load(champion_path)
    model = artifact["model"] if isinstance(artifact, dict) else artifact

    explainer = shap.TreeExplainer(model)

    # Vector khach hang trung thanh: 35 tuoi, Nu, tenure 60 thang, 0 cuoc goi, 0 ngay tre, Annual, chi tieu 900
    loyal_vector = [
        35.0, 0, 60.0, 25.0, 0.0, 0.0, 2, 2,
        900.0, 15.0, 0.0 / 60.0, 900.0 / 60.0, 0.0 / 15.0
    ]
    x_input = np.array([loyal_vector])

    factors, summary = compute_shap_attributions(explainer, x_input, model=model)

    assert factors["support_calls"] < 0.0, f"support_calls attribution should be negative: {factors['support_calls']}"
    assert factors["payment_delay"] < 0.0, f"payment_delay attribution should be negative: {factors['payment_delay']}"
    assert factors["tenure"] < 0.0, f"tenure attribution should be negative: {factors['tenure']}"

    assert "+-" not in summary, f"Found contradictory sign formatting in explanation summary: {summary}"


def test_shap_linear_explainer_fallback_on_logistic_regression():
    """
    Kiem thu co che khoi tao tu dong fallback sang shap.LinearExplainer
    khi mo hinh la LogisticRegression thay vi Tree model.
    Xac thuc attributions tinh toan thanh cong 13 dac trung va huu han.
    """
    lr_path = MODELS_DIR / "logistic_regression.joblib"
    assert lr_path.exists(), f"Logistic regression model missing: {lr_path}"

    lr_artifact = joblib.load(lr_path)
    lr_model = lr_artifact["model"] if isinstance(lr_artifact, dict) else lr_artifact

    explainer = _build_shap_explainer(lr_model)
    assert isinstance(explainer, shap.LinearExplainer), (
        f"Expected shap.LinearExplainer for logistic regression, got {type(explainer)}"
    )

    sample_vec = np.zeros((1, len(FEATURE_COLS)))
    factors, summary = compute_shap_attributions(explainer, sample_vec, model=lr_model)

    assert len(factors) == len(FEATURE_COLS), f"Expected {len(FEATURE_COLS)} factors, got {len(factors)}"
    for col, val in factors.items():
        assert np.isfinite(val), f"Factor '{col}' is non-finite: {val}"


def test_model_diagnostics_cohort_slice_consistency():
    """
    Kiem thu tinh nhat quan cua phep phan tich cat lop (error cohort slicing)
    theo Contract Length (Monthly, Quarterly, Annual):
    - Tong so mau cua 3 cohort bang chinh xac tong so mau tap test (66,332).
    - Ma tran nham lan tong TP, FP, FN, TN phai bang tong cac thanh phan tren 3 cohort.
    """
    champion_path = MODELS_DIR / "champion_model.joblib"
    test_parquet = PROCESSED_DIR / "test_features.parquet"

    artifact = joblib.load(champion_path)
    model = artifact["model"] if isinstance(artifact, dict) else artifact

    test_df = pd.read_parquet(test_parquet)
    y_test = test_df["churn"].values.astype(int)
    preds = model.predict(test_df[FEATURE_COLS]).astype(int)

    cm_total = confusion_matrix(y_test, preds, labels=[0, 1])

    c_monthly = test_df["contract_length_encoded"] == 0
    c_quarterly = test_df["contract_length_encoded"] == 1
    c_annual = test_df["contract_length_encoded"] == 2

    assert int(np.sum(c_monthly)) + int(np.sum(c_quarterly)) + int(np.sum(c_annual)) == len(test_df)
    assert len(test_df) == 66332

    cm_m = confusion_matrix(y_test[c_monthly], preds[c_monthly], labels=[0, 1])
    cm_q = confusion_matrix(y_test[c_quarterly], preds[c_quarterly], labels=[0, 1])
    cm_a = confusion_matrix(y_test[c_annual], preds[c_annual], labels=[0, 1])

    cm_cohort_sum = cm_m + cm_q + cm_a
    assert np.array_equal(cm_total, cm_cohort_sum), (
        f"Cohort confusion matrices do not sum to total:\nTotal:\n{cm_total}\nCohort Sum:\n{cm_cohort_sum}"
    )
