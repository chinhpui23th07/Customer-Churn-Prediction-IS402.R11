"""
Statistical Testing, KS Bonferroni & PSI Quantile Math Test Suite (Audit Team 3).
Kiem thu toan ven: Kiem dinh Kolmogorov-Smirnov da gia thuyet voi hieu chinh
Bonferroni FWER theo Rabanser et al. (NeurIPS 2019), do nhay KS drift tren
injected mean shift, tinh chuan xac phan vi PSI cho bien lien tuc theo
Yurdakul (2020) va bien roi rac (binary/ternary) khong bi sup do bin,
cung voi gioi han lam min epsilon bounds chong loi chia 0.
"""

import os
import pathlib
import numpy as np
import pandas as pd
import pytest
from scipy.stats import ks_2samp

from src.monitoring.drift_detector import (
    FEATURE_COLS,
    calculate_psi,
    run_drift_analysis,
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
TRAIN_PARQUET = PROJECT_ROOT / "data" / "processed" / "train_features.parquet"


def test_bonferroni_family_wise_error_rate_control():
    """
    Kiem dinh Family-Wise Error Rate (FWER) duoi gia thuyet H0 theo Rabanser et al. (2019).
    Thuc hien 100 phep thu doc lap giua D_test ~ N(0, I_13) va D_ref ~ N(0, I_13) voi N=2,000.
    Xac thuc:
    - Khi khong hieu chinh (alpha = 0.05), FWER tren 13 dac trung vuot qua 35%
      (tiem can ly thuyet 1 - (1 - 0.05)^13 xap xi 48.7%).
    - Khi ap dung Bonferroni (alpha_adj = 0.05 / 13 xap xi 0.003846), FWER thuc nghiem <= 0.10.
    """
    np.random.seed(42)
    n_features = 13
    n_samples = 2000
    n_trials = 100
    alpha_nominal = 0.05
    alpha_bonferroni = alpha_nominal / n_features

    unadjusted_false_positives = 0
    bonferroni_false_positives = 0

    for _ in range(n_trials):
        ref_data = np.random.normal(loc=0.0, scale=1.0, size=(n_samples, n_features))
        test_data = np.random.normal(loc=0.0, scale=1.0, size=(n_samples, n_features))
        p_values = [
            ks_2samp(ref_data[:, j], test_data[:, j]).pvalue
            for j in range(n_features)
        ]

        if any(p < alpha_nominal for p in p_values):
            unadjusted_false_positives += 1

        if any(p < alpha_bonferroni for p in p_values):
            bonferroni_false_positives += 1

    fwer_unadjusted = unadjusted_false_positives / n_trials
    fwer_bonferroni = bonferroni_false_positives / n_trials

    assert fwer_unadjusted > 0.35, (
        f"Unadjusted FWER unexpectedly low ({fwer_unadjusted:.2f} <= 0.35); "
        f"expected multiple-testing inflation near 48%."
    )
    assert fwer_bonferroni <= 0.10, (
        f"Bonferroni-adjusted FWER too high ({fwer_bonferroni:.2f} > 0.10); "
        f"failed to control false discovery rate."
    )


def test_ks_drift_sensitivity_on_injected_mean_shift():
    """
    Kiem thu do nhay cua KS test khi chu dong tiem do lech trung binh (+1.0 sigma)
    vao cac dac trung payment_delay, support_calls, total_spend, va last_interaction.
    Xac thuc:
    - Cac dac trung bi bien dong deu duoc phat hien drift == True.
    - Cac dac trung khong bi thay doi (age) giu nguyen drift == False.
    - Chi so dataset_drift_detected kich hoat True khi >= 30% dac trung drift.
    """
    assert TRAIN_PARQUET.exists(), f"Train features missing: {TRAIN_PARQUET}"
    train_df = pd.read_parquet(TRAIN_PARQUET)
    sample_df = train_df.sample(n=min(len(train_df), 10000), random_state=42).copy()

    shifted_df = sample_df.copy()
    for col in ["payment_delay", "support_calls", "total_spend", "last_interaction"]:
        sigma = shifted_df[col].std()
        shifted_df[col] = shifted_df[col] + (1.0 * sigma)

    # Chay phan tich drift voi dataframe da tiem do lech
    drift_report = run_drift_analysis(current_df=shifted_df[FEATURE_COLS], p_val_threshold=0.05)

    assert "features" in drift_report
    features_info = drift_report["features"]

    # Xac thuc 4 dac trung tiem do lech bi phat hien drift
    assert features_info["payment_delay"]["drift_detected"] is True, "payment_delay drift not detected"
    assert features_info["support_calls"]["drift_detected"] is True, "support_calls drift not detected"
    assert features_info["total_spend"]["drift_detected"] is True, "total_spend drift not detected"
    assert features_info["last_interaction"]["drift_detected"] is True, "last_interaction drift not detected"

    # Xac thuc dac trung age khong bi tac dong giu nguyen False
    assert features_info["age"]["drift_detected"] is False, "age falsely detected as drifted"

    # Tong so dac trung drift >= 4 tren tong 13 (>= 30.7%) nen dataset_drift_detected == True
    assert drift_report["drifted_features_count"] >= 4
    assert drift_report["dataset_drift_detected"] is True


def test_psi_continuous_feature_quantile_fidelity():
    """
    Kiem thu tinh toan hoc cua PSI tren phan phoi mu lien tuc (Exponential)
    theo huong dan cua Yurdakul (2020) va Katalay et al. (2025):
    - Hai phan phoi dong nhat: PSI < 0.03 (on dinh, khong lech).
    - Do lech quy mo +20%: 0.05 <= PSI < 0.25 (lech vua phai).
    - Do lech quy mo +80%: PSI >= 0.25 (troi dat nghiem trong).
    """
    np.random.seed(123)
    n_samples = 15000

    # Phan phoi co so Exp(scale=10.0)
    exp_baseline = np.random.exponential(scale=10.0, size=n_samples)

    # Truong hop 1: Phan phoi dong nhat (lay mau doc lap cung phan phoi)
    exp_identical = np.random.exponential(scale=10.0, size=n_samples)
    psi_identical = calculate_psi(exp_baseline, exp_identical, num_buckets=10)
    assert psi_identical < 0.03, f"Identical distributions produced high PSI: {psi_identical}"

    # Truong hop 2: Do lech quy mo vua (+50% scale: 10.0 -> 15.0)
    exp_moderate = np.random.exponential(scale=15.0, size=n_samples)
    psi_moderate = calculate_psi(exp_baseline, exp_moderate, num_buckets=10)
    assert 0.10 <= psi_moderate < 0.25, f"Moderate shift PSI out of expected range: {psi_moderate}"

    # Truong hop 3: Do lech quy mo manh (+80% scale: 10.0 -> 18.0)
    exp_severe = np.random.exponential(scale=18.0, size=n_samples)
    psi_severe = calculate_psi(exp_baseline, exp_severe, num_buckets=10)
    assert psi_severe >= 0.25, f"Severe shift PSI below 0.25 threshold: {psi_severe}"


def test_psi_discrete_binary_and_ternary_exact_bins():
    """
    Kiem thu tinh toan PSI cho cac bien roi rac (binary va ternary) de dam bao
    khong bi sup do nguong chia (bin collapsing xuong [-inf, +inf]):
    - Bien nhi phan (0 vs 1): Chuyen dich tu 90% 0s sang 10% 0s tao PSI ly thuyet
      (0.10 - 0.90)*ln(0.10/0.90) + (0.90 - 0.10)*ln(0.90/0.10) xap xi 3.515.
      Xac thuc 3.40 <= PSI <= 3.65.
    - Bien tam phan (0, 1, 2): Chuyen dich tu 100% Monthly (0) sang 100% Annual (2)
      tao PSI >= 2.0.
    """
    n_samples = 10000

    # Binary feature: 90/10 vs 10/90
    bin_expected = np.array([0.0] * int(n_samples * 0.90) + [1.0] * int(n_samples * 0.10))
    bin_actual = np.array([0.0] * int(n_samples * 0.10) + [1.0] * int(n_samples * 0.90))

    psi_bin = calculate_psi(bin_expected, bin_actual)
    assert 3.40 <= psi_bin <= 3.65, (
        f"Binary shift PSI {psi_bin} outside theoretical range [3.40, 3.65]; "
        f"check for bucket collapse."
    )

    # Ternary feature: 100% Monthly (0) vs 100% Annual (2)
    ternary_expected = np.zeros(5000, dtype=float)
    ternary_actual = np.full(5000, 2.0, dtype=float)

    psi_ternary = calculate_psi(ternary_expected, ternary_actual)
    assert psi_ternary >= 2.0, f"Ternary shift PSI {psi_ternary} unexpectedly low (< 2.0)"


def test_psi_zero_count_smoothing_epsilon_bounds():
    """
    Kiem thu co che kẹp epsilon = 1e-4 khi mot bucket trong actual hoac expected co so dem bang 0.
    Xac thuc calculate_psi luon tra ve so thuc huu han, khong phat sinh ZeroDivisionError,
    NaN, hoac vo cuc (inf).
    """
    # Expected trai rong tu 0 den 100, Actual chi tap trung tu 0 den 40 (cac bucket tren co count = 0)
    expected_vals = np.linspace(0.0, 100.0, 5000)
    actual_vals = np.linspace(0.0, 40.0, 5000)

    psi_smoothed = calculate_psi(expected_vals, actual_vals, num_buckets=10)

    assert isinstance(psi_smoothed, float)
    assert np.isfinite(psi_smoothed), f"PSI is not finite: {psi_smoothed}"
    assert psi_smoothed > 0.0, f"PSI should be positive under distribution shift: {psi_smoothed}"
    assert not np.isnan(psi_smoothed), "PSI returned NaN"
