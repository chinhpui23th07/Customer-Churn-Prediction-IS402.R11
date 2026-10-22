"""
Independent Adversarial Unit Test Suite - Audit Team 5.
Covers all 8 Mandatory Audit Dimensions (Tasks 1 to 8) for UIT IS402 Cloud Computing
Topic 11: MLOps Customer Churn Prediction.
Complies with Invariant 01, Invariant 02 (<= 400 lines), and Invariant 05 (ASCII hyphen -).
"""
import io
import json
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.utils import (
    compute_shap_attributions,
    generate_recommendation,
    log_inference_prediction,
    run_model_inference,
)
from src.data.latency_simulator import measure_tcp_latency
from src.data.preprocess import process_large_dataset_chunks
from src.models.train_pipeline import evaluate_model_performance
from src.monitoring.drift_detector import calculate_psi

BASE_DIR = Path(__file__).resolve().parent.parent
client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "mlops-churn-secret-2026"}


# ============================================================================
# TASK 1: IS402 COURSE & RUBRIC ALIGNMENT + CI/CD GATE SEMANTICS
# ============================================================================

def test_task1_verification_score_and_ci_grep_semantics():
    """DEF-01 & DEF-02: Check rubric score consistency and CI anti-mockup grep exit code."""
    checker_path = BASE_DIR / "scripts" / "verification" / "integrity_rubric_checker.py"
    ci_path = BASE_DIR / ".github" / "workflows" / "mlops_ci.yml"

    checker_text = checker_path.read_text(encoding="utf-8")
    ci_text = ci_path.read_text(encoding="utf-8")

    # integrity_rubric_checker.py docstring must not claim 6.25/10 when actual sum is 3.35/10
    assert "6.25/10" not in checker_text, (
        "Stale docstring in integrity_rubric_checker.py claims 6.25/10 instead of 3.35/10"
    )
    # In mlops_ci.yml, 'git grep ... || echo' succeeds with exit code 0 even when mockups ARE found
    assert 'git grep -iE "TODO: mock|fakeData|dummyData|simulateTx" -- src/ || echo' not in ci_text, (
        "CI anti-mockup gate uses 'git grep ... || echo', which exits 0 both when mockups exist and when clean"
    )


def test_task1_dvc_pipeline_stage_completeness():
    """DEF-03: Verify dvc.yaml includes all core MLOps stages (Feast, Optuna, Diagnostics, Drift)."""
    dvc_path = BASE_DIR / "dvc.yaml"
    dvc_cfg = yaml.safe_load(dvc_path.read_text(encoding="utf-8"))
    stages = dvc_cfg.get("stages", {})
    all_cmds = " ".join(stage.get("cmd", "") for stage in stages.values())

    assert "feature_store.py" in all_cmds, "dvc.yaml omits Feast feature store materialization stage"
    assert "tune_optuna.py" in all_cmds, "dvc.yaml omits Optuna hyperparameter tuning stage"
    assert "drift_detector.py" in all_cmds, "dvc.yaml omits drift detection stage"


# ============================================================================
# TASK 2: CODE LOGIC, STREAMING MEMORY & CLEAN ARCHITECTURE
# ============================================================================

def test_task2_out_of_core_cross_chunk_deduplication_and_median(tmp_path):
    """DEF-04: Verify process_large_dataset_chunks deduplicates CustomerID across chunks."""
    csv_file = tmp_path / "chunk_test.csv"
    pq_file = tmp_path / "chunk_out.parquet"

    # CustomerID 101 appears in chunk 1 and chunk 2 when chunk_size=2
    raw_df = pd.DataFrame({
        "CustomerID": [101, 102, 101, 103],
        "Age": [25.0, 35.0, 25.0, 45.0],
        "Gender": ["Male", "Female", "Male", "Female"],
        "Tenure": [10.0, 20.0, 10.0, 30.0],
        "Usage Frequency": [5.0, 10.0, 5.0, 15.0],
        "Support Calls": [1.0, 2.0, 1.0, 0.0],
        "Payment Delay": [0.0, 5.0, 0.0, 2.0],
        "Subscription Type": ["Basic", "Standard", "Basic", "Premium"],
        "Contract Length": ["Monthly", "Annual", "Monthly", "Quarterly"],
        "Total Spend": [100.0, 500.0, 100.0, 900.0],
        "Last Interaction": [5.0, 10.0, 5.0, 3.0],
        "Churn": [1.0, 0.0, 1.0, 0.0],
    })
    raw_df.to_csv(csv_file, index=False)

    process_large_dataset_chunks(csv_file, pq_file, chunk_size=2)
    out_df = pd.read_parquet(pq_file)

    assert out_df["customerid"].is_unique, (
        f"Duplicate customerid leaked across chunks in process_large_dataset_chunks: {out_df['customerid'].tolist()}"
    )


def test_task2_latency_simulator_socket_cleanup_on_failure():
    """DEF-05: Verify measure_tcp_latency closes OS socket when connect() raises socket.timeout."""
    mock_sock = MagicMock()
    mock_sock.connect.side_effect = socket.timeout("simulated timeout")

    with patch("socket.socket", return_value=mock_sock):
        res = measure_tcp_latency("example.invalid", port=443, num_pings=2)

    assert res["status"] == "UNREACHABLE"
    assert mock_sock.close.call_count == 2, (
        f"Socket descriptor leaked on connect timeout: close() called {mock_sock.close.call_count} times for 2 pings"
    )


def test_task2_sqlite_connection_leak_on_exception():
    """DEF-06: Verify log_inference_prediction closes SQLite connection via try/finally or context manager."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.execute.side_effect = RuntimeError("Simulated DB Lock")

    with patch("sqlite3.connect", return_value=mock_conn):
        log_inference_prediction(1001, [35.0, 0.0], 1, 0.85)

    assert mock_conn.close.called, (
        "sqlite3 connection in log_inference_prediction was NOT closed when cursor.execute raised an exception"
    )


# ============================================================================
# TASK 3: LITERATURE & MATHEMATICAL FIDELITY (SHAP, PSI, KS-TEST, OPTUNA)
# ============================================================================

def test_task3_psi_binary_and_ternary_categorical_collapse():
    """DEF-07: Verify calculate_psi detects severe shift in binary and 3-class discrete features."""
    rng = np.random.default_rng(42)
    # Binary feature shifting from 90% 0 / 10% 1 to 10% 0 / 90% 1 (theoretical PSI = 3.5156)
    expected_bin = pd.Series(rng.choice([0.0, 1.0], size=2000, p=[0.9, 0.1]))
    actual_bin = pd.Series(rng.choice([0.0, 1.0], size=2000, p=[0.1, 0.9]))
    psi_bin = calculate_psi(expected_bin, actual_bin, num_buckets=10)

    # Ternary feature shifting between class 1 and class 2
    expected_tri = pd.Series(rng.choice([0.0, 1.0, 2.0], size=3000, p=[0.2, 0.7, 0.1]))
    actual_tri = pd.Series(rng.choice([0.0, 1.0, 2.0], size=3000, p=[0.2, 0.1, 0.7]))
    psi_tri = calculate_psi(expected_tri, actual_tri, num_buckets=10)

    assert psi_bin > 0.25, f"Binary PSI collapsed to {psi_bin} (expected > 0.25) due to [-inf, inf] single-bin overwrite"
    assert psi_tri > 0.25, f"Ternary PSI collapsed to {psi_tri} (expected > 0.25) due to [-inf, 1, inf] bin merge"


def test_task3_evaluate_model_performance_single_class_guard():
    """DEF-08: Verify evaluate_model_performance handles single-class slices without ValueError."""
    dummy_clf = MagicMock()
    dummy_clf.predict.return_value = np.array([1, 1, 1, 1])
    dummy_clf.predict_proba.return_value = np.array([[0.1, 0.9], [0.2, 0.8], [0.1, 0.9], [0.05, 0.95]])

    X_single = pd.DataFrame(np.ones((4, 13)))
    y_single = pd.Series([1, 1, 1, 1])

    # Should not crash with ValueError: Only one class present in y_true
    metrics = evaluate_model_performance(dummy_clf, X_single, y_single, name="TestModel")
    assert "roc_auc" in metrics


def test_task3_shap_local_accuracy_and_negative_attribution_handling():
    """DEF-09: Verify SHAP explanation ranks by magnitude |phi_i| and UI does not format negative values as +-X%."""
    mock_explainer = MagicMock()
    # Suppose feature 0 has strong negative SHAP (-0.85) and others are near 0
    mock_explainer.shap_values.return_value = np.array([[-0.85] + [0.0] * 12])
    x_in = np.array([[2.0] + [1.0] * 12])

    factors, summary = compute_shap_attributions(mock_explainer, x_in)
    app_js = (BASE_DIR / "src" / "web" / "app.js").read_text(encoding="utf-8")

    assert "-0.85" in summary or "age" in summary, (
        "Negative protective SHAP attributions are completely dropped from explanation summary"
    )
    assert "+${(weight * 100).toFixed(1)}%" not in app_js, (
        "app.js unconditionally prefixes '+' to negative SHAP weights, rendering '+-15.2%'"
    )


def test_task4_optuna_tuning_disconnected_from_train_pipeline():
    """DEF-10: Verify train_pipeline.py uses Optuna best_params from tuning_history.json."""
    tuning_data = json.loads((BASE_DIR / "data" / "models" / "tuning_history.json").read_text(encoding="utf-8"))
    eval_data = json.loads((BASE_DIR / "data" / "models" / "evaluation_results.json").read_text(encoding="utf-8"))

    optuna_xgb_params = tuning_data["xgboost_champion"]["best_params"]
    trained_xgb_params = eval_data["models"]["XGBoost"]["params"]

    assert trained_xgb_params.get("n_estimators") == optuna_xgb_params.get("n_estimators"), (
        f"XGBoost trained with {trained_xgb_params} from GridSearchCV instead of Optuna {optuna_xgb_params}"
    )


# ============================================================================
# TASK 5: CUSTOMER ENTITY ANTI-LEAKAGE & TRAINING-SERVING SKEW
# ============================================================================

def test_task5_feast_materialization_omits_val_and_test_splits():
    """DEF-11: Verify Feast online store serves customers from validation/test splits and /predict/feast/online."""
    test_pq = BASE_DIR / "data" / "processed" / "test_features.parquet"
    test_df = pd.read_parquet(test_pq, columns=["customerid"])
    sample_test_cid = int(test_df["customerid"].iloc[0])

    res = client.get(f"/predict/customer/{sample_test_cid}", headers=AUTH_HEADERS)
    assert res.status_code == 200, (
        f"Customer {sample_test_cid} from test_features.parquet returned HTTP {res.status_code} "
        "because prepare_feast_data() only materializes train_features.parquet (70% of data)"
    )


# ============================================================================
# TASK 6 & TASK 8: ADVERSARIAL API BOUNDARY & INPUT VALIDATION
# ============================================================================

def test_task6_api_customer_id_zero_falsy_overwrite_and_nan_csv():
    """DEF-12: Verify customer_id=0 is not overwritten to 999999 and CSV NaN returns 400/422 instead of 500."""
    payload = {
        "customer_id": 0,
        "age": 35.0,
        "gender": "Female",
        "tenure": 24.0,
        "usage_frequency": 15.0,
        "support_calls": 2.0,
        "payment_delay": 3.0,
        "subscription_type": "Standard",
        "contract_length": "Annual",
        "total_spend": 650.0,
        "last_interaction": 10.0,
    }
    res = client.post("/predict", json=payload, headers=AUTH_HEADERS)
    if res.status_code == 200:
        assert res.json()["customer_id"] == 0, (
            f"customer_id=0 was falsy-overwritten to {res.json()['customer_id']} via 'customer.customer_id or 999999'"
        )

    csv_with_nan = (
        "CustomerID,Age,Gender,Tenure,Usage Frequency,Support Calls,Payment Delay,"
        "Subscription Type,Contract Length,Total Spend,Last Interaction\n"
        "1005,,Male,12,10,2,1,Standard,Monthly,500,5\n"
    )
    files = {"file": ("nan_row.csv", io.BytesIO(csv_with_nan.encode("utf-8")), "text/csv")}
    res_csv = client.post("/upload_csv_predict", files=files, headers=AUTH_HEADERS)
    assert res_csv.status_code in (400, 422), (
        f"CSV upload with NaN crashed with HTTP {res_csv.status_code} instead of graceful 400/422"
    )


# ============================================================================
# TASK 7: TELECOM/SAAS CHURN DOMAIN & CLOUD ECONOMICS CRITIQUE
# ============================================================================

def test_task7_churn_recommendation_clv_and_risk_tier_threshold():
    """DEF-13: Verify risk tier medium threshold (0.40) and CLV-aware retention recommendation."""
    dummy_clf = MagicMock()
    del dummy_clf.feature_names_in_
    dummy_clf.predict.return_value = np.array([0])
    dummy_clf.predict_proba.return_value = np.array([[0.64, 0.36]])
    raw_vec = np.ones((1, 13))

    _, _, _, risk_tier = run_model_inference(dummy_clf, raw_vec, None, False)
    # Paper 07 & Grounding Catalog specify Medium Risk in [0.40, 0.70), Low Risk < 0.40
    assert risk_tier == "Low Risk", (
        f"run_model_inference at prob=0.36 returned '{risk_tier}' because threshold is 0.35 instead of 0.40"
    )


def test_task7_cloud_tco_arithmetic_and_azure_iac_container_mismatch():
    """DEF-14: Verify Cloud TCO consistency and Azure Blob container name alignment across code and IaC."""
    cost_md = (BASE_DIR / "configs" / "cloud_architecture_and_cost.md").read_text(encoding="utf-8")
    ch5_py = (BASE_DIR / "scripts" / "uit_report_ch5.py").read_text(encoding="utf-8")
    arm_json = (BASE_DIR / "deploy" / "azure" / "arm_template.json").read_text(encoding="utf-8")
    preprocess_py = (BASE_DIR / "src" / "data" / "preprocess.py").read_text(encoding="utf-8")

    # Container name in preprocess.py must match deploy/azure/arm_template.json
    assert ("churnguard-datasets" in preprocess_py) or ("mlops-processed-data" in arm_json), (
        "Blob container mismatch: preprocess.py uses 'mlops-processed-data' while Azure IaC provisions 'churnguard-datasets'"
    )
    # TCO in cloud_architecture_and_cost.md ($138.07) vs uit_report_ch5.py ($90.75)
    assert ("$90.75" in cost_md) or ("$138.07" in ch5_py), (
        "TCO mismatch between configs/cloud_architecture_and_cost.md ($138.07) and scripts/uit_report_ch5.py ($90.75)"
    )


# ============================================================================
# TASK 8: API SERVING, WEB BENTO GRID & DELIVERABLES HYGIENE
# ============================================================================

def test_task8_dashboard_error_analysis_key_mismatch_and_web_xss_secret():
    """DEF-15: Verify dashboard.py reads 'confusion_breakdown' from error_analysis_report.json."""
    err_json = json.loads((BASE_DIR / "data" / "processed" / "error_analysis_report.json").read_text(encoding="utf-8"))
    dashboard_py = (BASE_DIR / "src" / "web" / "dashboard.py").read_text(encoding="utf-8")

    assert "confusion_breakdown" in err_json
    assert 'err_rep.get("confusion_breakdown"' in dashboard_py, (
        "dashboard.py queries err_rep.get('counts', {}) instead of 'confusion_breakdown', displaying all 0s"
    )
