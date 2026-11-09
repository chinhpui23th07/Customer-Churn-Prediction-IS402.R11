"""
Unit & Integration Test Suite cho KKBox Training Pipeline va Continuous Probability Calibration.
Kiem tra:
- Luoc do du lieu KKBox thuc te va ep kieu DuckDB decimal128 sang float64.
- Huan luyen thuc nghiem voi LightGBM va HistGradientBoosting (zero mockup).
- Phan bo xac suat lien tuc va ty le tap trung khoang rui ro trung binh [0.40, 0.70) tai ~3.3-3.5%.
- Tinh toan ven cua tap tin bundle data/models/kkbox_champion_model.joblib.
- Giao tiep dong lenh CLI (--dry-run).
"""

import os
import subprocess
import sys
import tempfile
import joblib
import numpy as np
import pandas as pd
import pytest

from src.models.train_kkbox import (
    DEFAULT_DATA_PATH,
    DEFAULT_MODEL_PATH,
    KKBOX_BEHAVIORAL_FEATURES,
    TARGET_COL,
    create_model_estimator,
    evaluate_kkbox_predictions,
    load_kkbox_dataset,
    train_kkbox_champion,
)


def test_kkbox_parquet_schema_and_decimal_cast():
    """Kiem tra tap du lieu thuc te ton tai va xu ly dung kieu decimal128 cua DuckDB."""
    assert os.path.exists(DEFAULT_DATA_PATH), f"Tep {DEFAULT_DATA_PATH} khong ton tai."

    df = pd.read_parquet(DEFAULT_DATA_PATH)
    assert len(df) == 970960, f"So luong ban ghi phai la 970,960 nhung nhan duoc {len(df)}"
    assert TARGET_COL in df.columns
    assert "total_actual_paid" in df.columns

    churn_rate = float(df[TARGET_COL].mean())
    assert 0.088 <= churn_rate <= 0.092, f"Ty le churn thuc te phai xap xi 8.99% nhung nhan {churn_rate:.4f}"

    # Ep kieu DuckDB decimal128 sang float64
    df["total_actual_paid"] = df["total_actual_paid"].astype(float)
    assert np.issubdtype(df["total_actual_paid"].dtype, np.floating)
    assert not df["total_actual_paid"].isnull().all()


def test_kkbox_load_dataset_function():
    """Kiem tra ham load_kkbox_dataset voi phan chia Stratified train/test."""
    sample_n = 2000
    X_train, X_test, y_train, y_test, feats, meta = load_kkbox_dataset(
        sample_size=sample_n, test_size=0.25, random_state=42
    )

    assert len(X_train) == 1500
    assert len(X_test) == 500
    assert len(y_train) == 1500
    assert len(y_test) == 500
    assert feats == KKBOX_BEHAVIORAL_FEATURES
    assert meta["loaded_rows"] == sample_n
    assert meta["feature_count"] == 15

    # Kiem tra tat ca cac dac trung la kieu so (khong co kieu object)
    for col in feats:
        assert np.issubdtype(X_train[col].dtype, np.number), f"Cot {col} khong phai kieu so: {X_train[col].dtype}"


def test_kkbox_model_estimator_creation():
    """Kiem tra khoi tao cac loai mo hinh phan loai gradient boosting."""
    lgbm_model = create_model_estimator("lgbm", random_state=42, n_estimators=50)
    assert hasattr(lgbm_model, "fit")
    assert hasattr(lgbm_model, "predict_proba")

    hgb_model = create_model_estimator("hgb", random_state=42, n_estimators=50)
    assert hasattr(hgb_model, "fit")
    assert hasattr(hgb_model, "predict_proba")

    with pytest.raises(ValueError):
        create_model_estimator("unsupported_algorithm")


def test_kkbox_evaluation_metrics_logic():
    """Kiem tra ham evaluate_kkbox_predictions tinh toan dung cac chi so va phan bo rui ro."""
    y_true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 0, 1])
    y_probs = np.array([0.05, 0.12, 0.45, 0.55, 0.65, 0.72, 0.85, 0.90, 0.20, 0.60])

    eval_res = evaluate_kkbox_predictions(y_true, y_probs, threshold=0.5)
    assert "accuracy" in eval_res
    assert "roc_auc" in eval_res
    assert "brier_score" in eval_res
    assert "probability_distribution" in eval_res

    p_dist = eval_res["probability_distribution"]
    assert p_dist["total_evaluated"] == 10
    # Cac xac suat trong [0.40, 0.70): 0.45, 0.55, 0.65, 0.60 -> 4/10 = 0.40
    assert p_dist["mid_risk_count"] == 4
    assert p_dist["mid_risk_ratio"] == 0.40


def test_kkbox_training_fast_execution(tmp_path):
    """Huan luyen thuc nghiem nhanh tren tap mau nho va kiem tra bundle joblib hop le."""
    save_file = str(tmp_path / "test_kkbox_bundle.joblib")
    metrics_file = str(tmp_path / "test_metrics.json")

    bundle = train_kkbox_champion(
        sample_size=8000,
        model_type="lgbm",
        cv_folds=3,
        random_state=42,
        save_path=save_file,
        metrics_path=metrics_file,
    )

    assert os.path.exists(save_file)
    assert os.path.exists(metrics_file)

    assert bundle["name"] == "KKBox_LGBM_Champion"
    assert bundle["model"] is not None
    assert bundle["feature_names"] == KKBOX_BEHAVIORAL_FEATURES
    assert bundle["metrics"]["roc_auc"] >= 0.80
    assert bundle["cv_5fold"]["roc_auc_mean"] >= 0.80
    assert bundle["probability_distribution"]["mid_risk_ratio"] > 0.01


def test_kkbox_champion_model_file_integrity():
    """Kiem tra tap tin champion model data/models/kkbox_champion_model.joblib ton tai va dat tieu chuan."""
    assert os.path.exists(DEFAULT_MODEL_PATH), (
        f"Tap tin champion model chua ton tai tai: {DEFAULT_MODEL_PATH}. "
        "Vui long chay 'python -m src.models.train_kkbox' truoc."
    )

    bundle = joblib.load(DEFAULT_MODEL_PATH)
    assert isinstance(bundle, dict)
    assert "model" in bundle
    assert "feature_names" in bundle
    assert "metrics" in bundle
    assert "cv_5fold" in bundle
    assert "probability_distribution" in bundle

    assert len(bundle["feature_names"]) == 15
    assert bundle["target_col"] == TARGET_COL

    # Kiem tra chat luong mo hinh dat nguong quy dinh
    m = bundle["metrics"]
    assert m["roc_auc"] >= 0.85, f"Test ROC-AUC ({m['roc_auc']}) thap hon tieu chuan 0.85"
    assert m["brier_score"] <= 0.08, f"Brier score ({m['brier_score']}) qua cao, calibration kem"

    cv_m = bundle["cv_5fold"]
    if cv_m and "roc_auc_mean" in cv_m:
        assert cv_m["roc_auc_mean"] >= 0.85, f"CV ROC-AUC ({cv_m['roc_auc_mean']}) thap hon 0.85"


def test_kkbox_continuous_probability_distribution():
    """
    Kiem tra xac suat du doan la lien tuc va phan bo rui ro trung binh [0.40, 0.70)
    dat ~3.3-3.7%, khong bi ket cuc tri nhi phan nhu tap Kaggle synthetic.
    """
    bundle = joblib.load(DEFAULT_MODEL_PATH)
    p_dist = bundle["probability_distribution"]

    # Ty le trong khoang mid-risk [0.40, 0.70) phai dat ~3.3% - 3.7%
    mid_ratio = p_dist["mid_risk_ratio"]
    assert 0.025 <= mid_ratio <= 0.050, (
        f"Ty le mid-risk nam ngoai khoang mong doi ~3.3-3.7%: {mid_ratio * 100:.2f}%"
    )

    # Kiem tra mien gia tri xac suat trai dai tu gan 0 den gan 1
    assert p_dist["p_min"] < 0.05, f"Xac suat nho nhat qua cao: {p_dist['p_min']}"
    assert p_dist["p_max"] > 0.85, f"Xac suat lon nhat qua thap: {p_dist['p_max']}"

    # Ky vong xac suat gan bang ty le churn thuc te (8.99%)
    assert 0.07 <= p_dist["p_mean"] <= 0.12, (
        f"Gia tri xac suat trung binh lech khoi ty le churn 8.99%: {p_dist['p_mean']:.4f}"
    )


def test_kkbox_inference_single_and_batch():
    """Kiem tra kha nang suy luan don le va theo lo cua champion model."""
    bundle = joblib.load(DEFAULT_MODEL_PATH)
    model = bundle["model"]
    feature_names = bundle["feature_names"]

    # 1. Mau don le
    sample_single = pd.DataFrame([{
        "city": 1,
        "bd": 28,
        "gender_encoded": 1,
        "registered_via": 7,
        "trans_count": 5,
        "avg_plan_days": 30.0,
        "total_actual_paid": 745.0,
        "auto_renew_ratio": 0.80,
        "cancel_ratio": 0.0,
        "discount_ratio": 0.0,
        "listen_days_count": 20,
        "total_listen_secs": 45000.0,
        "total_songs_played": 180.0,
        "completion_ratio": 0.65,
        "unique_song_ratio": 0.85,
    }])[feature_names]

    prob_single = model.predict_proba(sample_single)
    assert prob_single.shape == (1, 2)
    assert 0.0 <= prob_single[0, 1] <= 1.0
    assert np.isclose(np.sum(prob_single[0]), 1.0)

    # 2. Mau theo lo
    batch_df = pd.concat([sample_single] * 10, ignore_index=True)
    probs_batch = model.predict_proba(batch_df)
    assert probs_batch.shape == (10, 2)
    assert np.allclose(np.sum(probs_batch, axis=1), 1.0)


def test_kkbox_cli_dry_run_execution():
    """Kiem tra CLI hoat dong chinh xac voi co --dry-run tra ve ma thoat 0."""
    cmd = [sys.executable, "-m", "src.models.train_kkbox", "--dry-run"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)

    assert res.returncode == 0, f"CLI dry-run that bai: {res.stderr}"
    assert "KKBox Pipeline Dry-Run" in res.stdout
    assert "Dry-run completed successfully" in res.stdout
