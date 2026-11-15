"""
Test Suite for TreeSHAP Batch Prediction Conditional XAI (Milestone 4).
Verifies:
1. Explainer construction (_build_shap_explainer) for Tree and Linear models.
2. Single-sample SHAP attributions and linear fallback.
3. Batch fast-path zero overhead (explain=False returns None).
4. Conditional TreeSHAP batch attributions (explain=True with threshold).
5. API endpoints: /predict (online SHAP), /batch_predict fast-path, and /batch_predict conditional XAI.
6. Strict source line-cap compliance (<= 400 lines per file).
"""
import os
import pathlib
import time
import joblib
import numpy as np
import pytest
import shap
from fastapi.testclient import TestClient

from src.api.main import app, _build_shap_explainer
from src.models.explain import compute_shap_attributions, compute_batch_attributions, FEATURE_COLS

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "data" / "models"
AUTH_HEADERS = {"X-API-Key": "mlops-churn-secret-2026"}
client = TestClient(app)


def make_customer_dict(cid, age, gender, tenure, freq, calls, delay, sub, contract, spend, last):
    """Helper tao dictionary thong tin khach hang chuan schema CustomerInput."""
    return {
        "customer_id": cid, "age": age, "gender": gender, "tenure": tenure,
        "usage_frequency": freq, "support_calls": calls, "payment_delay": delay,
        "subscription_type": sub, "contract_length": contract,
        "total_spend": spend, "last_interaction": last
    }


@pytest.fixture(scope="module")
def champion_model():
    path = MODELS_DIR / "champion_model.joblib"
    assert path.exists(), f"Champion model not found at {path}"
    artifact = joblib.load(path)
    return artifact["model"] if isinstance(artifact, dict) else artifact


@pytest.fixture(scope="module")
def logistic_model():
    path = MODELS_DIR / "logistic_regression.joblib"
    assert path.exists(), f"Logistic regression model not found at {path}"
    artifact = joblib.load(path)
    return artifact["model"] if isinstance(artifact, dict) else artifact


def test_build_shap_explainer_tree_and_linear(champion_model, logistic_model):
    """Test explainer initialization for tree-based and linear models with fallback."""
    tree_explainer = _build_shap_explainer(champion_model)
    assert isinstance(tree_explainer, shap.TreeExplainer)

    linear_explainer = _build_shap_explainer(logistic_model)
    assert isinstance(linear_explainer, shap.LinearExplainer)

    invalid_explainer = _build_shap_explainer(object())
    assert invalid_explainer is None


def test_compute_shap_attributions_single_vector(champion_model):
    """Test single vector TreeSHAP attribution and summary formatting."""
    explainer = _build_shap_explainer(champion_model)
    sample_vec = np.array([[35.0, 0, 24.0, 15.0, 3.0, 5.0, 1, 0, 650.0, 12.0, 3.0 / 24.0, 650.0 / 24.0, 5.0 / 12.0]])
    factors, summary = compute_shap_attributions(explainer, sample_vec, model=champion_model)

    assert isinstance(factors, dict)
    assert len(factors) == len(FEATURE_COLS)
    for col in FEATURE_COLS:
        assert col in factors
        assert np.isfinite(factors[col])

    assert "base_value=" in summary
    assert "+-" not in summary
    assert "Đặc trưng thúc đẩy rời bỏ chính" in summary


def test_compute_shap_attributions_linear_fallback(logistic_model):
    """Test linear SHAP fallback on linear models."""
    sample_vec = np.zeros((1, len(FEATURE_COLS)))
    explainer = _build_shap_explainer(logistic_model)
    factors, summary = compute_shap_attributions(explainer, sample_vec, model=logistic_model)

    assert len(factors) == len(FEATURE_COLS)
    assert all(np.isfinite(v) for v in factors.values())
    assert len(summary) > 10


def test_batch_attributions_fast_path_zero_overhead(champion_model):
    """Test that explain=False returns None with virtually 0ms overhead."""
    explainer = _build_shap_explainer(champion_model)
    n_samples = 150
    feature_matrix = np.zeros((n_samples, len(FEATURE_COLS)))
    probs = np.full(n_samples, 0.85)

    t0 = time.perf_counter()
    result = compute_batch_attributions(
        model=champion_model, explainer=explainer, feature_matrix=feature_matrix,
        churn_probabilities=probs, explain=False, explain_threshold=0.70
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert result is None
    assert elapsed_ms < 5.0, f"Fast-path overhead too high: {elapsed_ms:.2f} ms"


def test_batch_attributions_conditional_thresholding(champion_model):
    """Test that explain=True only computes TreeSHAP for prob >= explain_threshold."""
    explainer = _build_shap_explainer(champion_model)
    sample_vec = [35.0, 0, 24.0, 15.0, 3.0, 5.0, 1, 0, 650.0, 12.0, 0.125, 27.08, 0.416]
    feature_matrix = np.tile(sample_vec, (4, 1))
    probs = [0.15, 0.45, 0.72, 0.90]

    results = compute_batch_attributions(
        model=champion_model, explainer=explainer, feature_matrix=feature_matrix,
        churn_probabilities=probs, explain=True, explain_threshold=0.70
    )

    assert isinstance(results, list)
    assert len(results) == 4
    assert results[0] == (None, None)
    assert results[1] == (None, None)

    factors_2, summary_2 = results[2]
    assert factors_2 is not None and isinstance(factors_2, dict)
    assert len(factors_2) == len(FEATURE_COLS)
    assert summary_2 is not None and "base_value=" in summary_2

    factors_3, summary_3 = results[3]
    assert factors_3 is not None and isinstance(factors_3, dict)
    assert len(factors_3) == len(FEATURE_COLS)
    assert summary_3 is not None and "base_value=" in summary_3


def test_api_predict_single_preserves_tree_shap():
    """Verify online single /predict endpoint preserves TreeSHAP with low latency."""
    payload = make_customer_dict(3001, 40.0, "Female", 12.0, 10.0, 4.0, 8.0, "Standard", "Monthly", 450.0, 15.0)
    client.post("/predict", json=payload, headers=AUTH_HEADERS)
    t0 = time.perf_counter()
    response = client.post("/predict", json=payload, headers=AUTH_HEADERS)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert response.status_code == 200
    data = response.json()
    assert data["feature_attributions"] is not None
    assert len(data["feature_attributions"]) == len(FEATURE_COLS)
    assert "explanation_summary" in data and len(data["explanation_summary"]) > 0
    assert data["latency_ms"] < 50.0
    assert elapsed_ms < 100.0


def test_api_batch_predict_fast_path_by_default():
    """Verify /batch_predict default behavior (explain=False) returns None for attributions."""
    customers = [
        make_customer_dict(4001, 28.0, "Male", 3.0, 5.0, 6.0, 12.0, "Basic", "Monthly", 150.0, 20.0),
        make_customer_dict(4002, 50.0, "Female", 40.0, 20.0, 0.0, 0.0, "Premium", "Annual", 1100.0, 2.0)
    ]
    response = client.post("/batch_predict", json=customers, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2
    for pred in data["predictions"]:
        assert pred["feature_attributions"] is None
        assert pred["explanation_summary"] is None


def test_api_batch_predict_conditional_xai_active():
    """Verify /batch_predict?explain=true conditionally explains only high-risk customers."""
    customers = [
        make_customer_dict(5001, 25.0, "Male", 2.0, 3.0, 10.0, 20.0, "Basic", "Monthly", 80.0, 30.0),
        make_customer_dict(5002, 55.0, "Female", 48.0, 25.0, 0.0, 0.0, "Premium", "Annual", 1200.0, 1.0)
    ]
    url = "/batch_predict?explain=true&explain_threshold=0.70"
    response = client.post(url, json=customers, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2

    high_risk_pred = next((p for p in data["predictions"] if p["customer_id"] == 5001), None)
    low_risk_pred = next((p for p in data["predictions"] if p["customer_id"] == 5002), None)
    assert high_risk_pred is not None and low_risk_pred is not None

    if high_risk_pred["churn_probability"] >= 0.70:
        assert high_risk_pred["feature_attributions"] is not None
        assert high_risk_pred["explanation_summary"] is not None
        assert "base_value=" in high_risk_pred["explanation_summary"]
    else:
        assert high_risk_pred["feature_attributions"] is None

    if low_risk_pred["churn_probability"] < 0.70:
        assert low_risk_pred["feature_attributions"] is None
        assert low_risk_pred["explanation_summary"] is None


def test_api_batch_predict_custom_threshold():
    """Verify explain_threshold parameter controls conditional explanation cutoff."""
    customers = [make_customer_dict(6001, 30.0, "Male", 5.0, 8.0, 5.0, 10.0, "Basic", "Monthly", 200.0, 15.0)]
    url = "/batch_predict?explain=true&explain_threshold=0.9999"
    response = client.post(url, json=customers, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["predictions"][0]["feature_attributions"] is None


def test_source_code_line_caps():
    """Verify source code line count constraints (Invariant 02 <= 400 lines)."""
    explain_path = PROJECT_ROOT / "src" / "models" / "explain.py"
    main_path = PROJECT_ROOT / "src" / "api" / "main.py"
    test_path = pathlib.Path(__file__)

    with open(explain_path, "r", encoding="utf-8") as f:
        explain_lines = len(f.readlines())
    with open(main_path, "r", encoding="utf-8") as f:
        main_lines = len(f.readlines())
    with open(test_path, "r", encoding="utf-8") as f:
        test_lines = len(f.readlines())

    assert explain_lines <= 250, f"src/models/explain.py exceeds 250 lines: {explain_lines}"
    assert main_lines <= 370, f"src/api/main.py exceeds 370 lines: {main_lines}"
    assert test_lines <= 300, f"test_shap_batch_optimization.py exceeds 300 lines: {test_lines}"
