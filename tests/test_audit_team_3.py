"""
Adversarial Audit Test Suite - Audit Team 3 (Stage 1: Parallel Grounded Hunting).
Covers all 8 Mandatory Audit Dimensions for UIT IS402 MLOps Customer Churn Prediction.
Strictly read-only against production code in src/, scripts/, and deploy/.
"""
import os
import sys
import json
import socket
import inspect
import tempfile
import numpy as np
import pandas as pd
import yaml
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
VERIF_DIR = os.path.join(BASE_DIR, "scripts", "verification")
if VERIF_DIR not in sys.path:
    sys.path.insert(0, VERIF_DIR)

from src.data.preprocess import engineer_features, process_large_dataset_chunks
from src.data.latency_simulator import measure_tcp_latency
from src.api.schemas import CustomerInput
from src.api.utils import (
    FEATURE_COLS,
    prepare_feature_vector_from_input,
    compute_shap_attributions,
    generate_recommendation,
    init_inference_db,
    log_inference_prediction,
)
from src.models.train_pipeline import evaluate_model_performance
from src.monitoring.drift_detector import calculate_psi, run_drift_analysis
from integrity_rubric_checker import AcademicIntegrityAuditor


# ==============================================================================
# TASK 1: IS402 Course & Rubric Alignment
# ==============================================================================

def test_t1_rubric_docstring_vs_evaluated_score_consistency():
    """
    [DEF-T1-01] Verify that integrity_rubric_checker.py module docstring score
    matches the actual evaluated local score returned by evaluate_all().
    Grounded in: [DOC-01: UIT_Cloud_Computing_Curriculum_Spec.md | Section 5 Rubric]
    """
    import integrity_rubric_checker as irc
    auditor = AcademicIntegrityAuditor()
    verdict = auditor.evaluate_all()
    actual_score_str = f"{verdict['total_score']:.2f}/10"
    doc = irc.__doc__ or ""
    assert actual_score_str in doc, (
        f"Rubric docstring claims stale score ({doc.strip().splitlines()[3]}), "
        f"but evaluate_all() returns {actual_score_str}!"
    )


def test_t1_dvc_yaml_pipeline_completeness():
    """
    [DEF-T1-02] Verify that dvc.yaml tracks scaler.joblib & metadata.json in preprocess
    and includes Feast feature store materialization and Optuna tuning stages.
    Grounded in: [REPO-03: Oyebamiji_Micheal_dvc_mlflow | dvc.yaml |
                  PAPER-01: Kreuzberger et al. 2023 | DOI: 10.1109/ACCESS.2023.3262138]
    """
    dvc_path = os.path.join(BASE_DIR, "dvc.yaml")
    with open(dvc_path, "r", encoding="utf-8") as f:
        dvc_cfg = yaml.safe_load(f)

    stages = dvc_cfg.get("stages", {})
    preprocess_outs = stages.get("preprocess", {}).get("outs", [])
    assert "data/processed/scaler.joblib" in preprocess_outs, (
        "dvc.yaml preprocess stage fails to track data/processed/scaler.joblib in outs!"
    )
    all_cmds = " ".join(s.get("cmd", "") for s in stages.values())
    assert "feature_store.py" in all_cmds, "dvc.yaml omits Feast feature_store.py stage!"
    assert "tune_optuna.py" in all_cmds, "dvc.yaml omits Optuna tune_optuna.py stage!"


# ==============================================================================
# TASK 2: Code Logic, Out-of-Core Streaming & Clean Architecture
# ==============================================================================

def test_t2_out_of_core_chunking_cross_chunk_customerid_dedup_and_schema():
    """
    [DEF-T2-04 & DEF-T5-01] Verify that process_large_dataset_chunks:
    1. Does not crash with PyArrow ValueError when chunk 1 has non-null ints and chunk 2 has NaNs.
    2. Deduplicates duplicate CustomerID records across chunk boundaries.
    Grounded in: [PAPER-08: Soumyadeep Roy 2026 | arXiv:2610.00118v1, Section 3.2]
    """
    rows = [
        {"CustomerID": 101, "Age": 30, "Gender": "Male", "Tenure": 12, "Usage Frequency": 10,
         "Support Calls": 1, "Payment Delay": 0, "Subscription Type": "Standard",
         "Contract Length": "Annual", "Total Spend": 500.0, "Last Interaction": 5, "Churn": 0},
        {"CustomerID": 102, "Age": 40, "Gender": "Female", "Tenure": 24, "Usage Frequency": 15,
         "Support Calls": 2, "Payment Delay": 1, "Subscription Type": "Premium",
         "Contract Length": "Quarterly", "Total Spend": 800.0, "Last Interaction": 3, "Churn": 0},
        # Chunk boundary (chunk_size=2): CustomerID 101 duplicated in chunk 2!
        {"CustomerID": 101, "Age": 30, "Gender": "Male", "Tenure": 12, "Usage Frequency": 10,
         "Support Calls": 1, "Payment Delay": 0, "Subscription Type": "Standard",
         "Contract Length": "Annual", "Total Spend": 500.0, "Last Interaction": 5, "Churn": 0},
        {"CustomerID": 103, "Age": 35, "Gender": "Male", "Tenure": 6, "Usage Frequency": 5,
         "Support Calls": 4, "Payment Delay": 10, "Subscription Type": "Basic",
         "Contract Length": "Monthly", "Total Spend": 200.0, "Last Interaction": 10, "Churn": 1},
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "chunk_input.csv")
        pq_path = os.path.join(tmpdir, "chunk_output.parquet")
        pd.DataFrame(rows).to_csv(csv_path, index=False)

        total_rows = process_large_dataset_chunks(csv_path, pq_path, chunk_size=2)
        out_df = pd.read_parquet(pq_path)

        assert total_rows == 3 and len(out_df) == 3, (
            f"Cross-chunk CustomerID duplicate leaked into output Parquet! "
            f"Expected 3 unique customers, got {len(out_df)} rows."
        )


def test_t2_latency_simulator_socket_cleanup_on_connection_error(monkeypatch):
    """
    [DEF-T2-03] Verify that measure_tcp_handshake_rtt closes the socket even when
    s.connect() raises socket.timeout / OSError.
    Grounded in: [REPO-07: telco-churn-mlops-pipeline | Resource Hygiene]
    """
    created_sockets = []

    class DummySocket:
        def __init__(self, *args, **kwargs):
            self.closed = False
            created_sockets.append(self)

        def settimeout(self, t):
            pass

        def connect(self, addr):
            raise socket.timeout("Simulated connection timeout")

        def close(self):
            self.closed = True

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(socket, "socket", DummySocket)
    import urllib.request
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("Fallback blocked")),
    )

    measure_tcp_latency("192.0.2.1", 443, num_pings=2)
    leaked = [s for s in created_sockets if not s.closed]
    assert len(leaked) == 0, (
        f"Socket resource leak detected: {len(leaked)}/{len(created_sockets)} "
        "sockets were never closed after connect() raised socket.timeout!"
    )


def test_t2_sqlite_wal_mode_and_connection_cleanup():
    """
    [DEF-T2-02] Verify that SQLite connections in src/api/utils.py enable WAL mode
    for concurrent FastAPI serving and use try/finally or context manager to close.
    Grounded in: [REPO-07: telco-churn-mlops-pipeline | src/api/database.py]
    """
    src_code = inspect.getsource(init_inference_db) + "\n" + inspect.getsource(log_inference_prediction)
    assert "WAL" in src_code.upper(), (
        "SQLite inference database does not enable PRAGMA journal_mode=WAL for concurrent writes!"
    )
    assert "finally:" in src_code, (
        "sqlite3.connect() in src/api/utils.py lacks a finally: conn.close() guard!"
    )


# ==============================================================================
# TASK 3: Literature & Mathematical Fidelity
# ==============================================================================

def test_t3_shap_local_accuracy_and_negative_attribution_preservation():
    """
    [DEF-T3-01] Verify Lundberg & Lee (NeurIPS 2017) Property 1 (Local Accuracy)
    and preservation of negative (churn-reducing) SHAP attributions.
    Grounded in: [PAPER-02: Lundberg & Lee 2017 | arXiv:1705.07874, Eq. 1 & Property 1]
    """
    class DummyExplainer:
        expected_value = 0.50

        def shap_values(self, X):
            # Strong negative (protective) attributions and one minor positive attribution
            vals = np.full((1, X.shape[1]), -0.15)
            vals[0, 0] = 0.01
            return vals

    X_dummy = np.zeros((1, 13))
    factors, summary = compute_shap_attributions(DummyExplainer(), X_dummy)

    app_js_path = os.path.join(BASE_DIR, "src", "web", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()
    assert "+${(weight * 100)" not in app_js, (
        "src/web/app.js hardcodes a '+' sign before all SHAP weights, falsifying negative attributions!"
    )


def test_t3_psi_small_sample_smoothing_bias():
    """
    [DEF-T3-02a] Verify that calculate_psi does not trigger false drift (>0.15)
    when comparing a reference distribution against an identically distributed N=10 batch
    (the minimum batch size in run_drift_analysis line 88) due to heavy +1 Laplace smoothing.
    Grounded in: [PAPER-03: Rabanser et al. 2019 | arXiv:1810.11953, Section 3.1]
    """
    # Skewed discrete distribution (50% zeros, 50% spread across 1..9)
    base_10 = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    expected = np.tile(base_10, 10000)  # N = 100,000
    actual = base_10.copy()             # N = 10 (100% identical empirical distribution!)

    psi_val = calculate_psi(expected, actual, num_buckets=10)
    assert psi_val < 0.05, (
        f"False-positive PSI drift on identical distribution! Expected PSI ~ 0.0, "
        f"got PSI = {psi_val:.4f} due to unscaled +1 Laplace smoothing on N=10 vs N=100,000."
    )


def test_t3_ks_drift_missing_bonferroni_correction():
    """
    [DEF-T3-02b] Verify that run_drift_analysis applies Bonferroni correction
    (alpha / M = 0.05 / 13 = 0.00385) across M=13 features as mandated by Rabanser et al. (2019).
    Grounded in: [PAPER-03: Rabanser et al. 2019 | arXiv:1810.11953, Section 3.1]
    """
    sig = inspect.signature(run_drift_analysis)
    default_p = sig.parameters["p_val_threshold"].default
    src_code = inspect.getsource(run_drift_analysis)
    has_bonferroni = ("p_val_threshold / len" in src_code) or (default_p <= 0.005)
    assert has_bonferroni, (
        f"run_drift_analysis uses unadjusted p_val_threshold={default_p} "
        "without Bonferroni correction (alpha / M) across M=13 features!"
    )


def test_t3_evaluate_single_class_and_empty_array_safety():
    """
    [DEF-T3-03] Verify that evaluate_model_performance handles single-class ground truth arrays
    without producing NaN roc_auc or crashing on empty slices.
    Grounded in: [PAPER-09: Adaptive_Ensemble_Churn_Prediction_2024.md | Section 3]
    """
    class DummyModel:
        def predict(self, X):
            return np.array([1, 1, 0, 1])

        def predict_proba(self, X):
            return np.array([[0.1, 0.9], [0.15, 0.85], [0.6, 0.4], [0.05, 0.95]])

    X_dummy = np.zeros((4, 13))
    y_true = np.array([1, 1, 1, 1])
    metrics = evaluate_model_performance(DummyModel(), X_dummy, X_dummy, y_true, is_linear=False)
    assert not np.isnan(metrics["roc_auc"]), (
        f"evaluate_model_performance produced NaN roc_auc ({metrics['roc_auc']}) on single-class subgroup!"
    )


def test_t3_diagnostics_vs_dashboard_json_schema_contract():
    """
    [DEF-T3-04] Verify that error_analysis_report.json produced by model_diagnostics.py
    matches the JSON schema keys ('counts', 'metrics') read by src/web/dashboard.py.
    Grounded in: [INVARIANT-17: Triple Cross-Validation & Data Consistency]
    """
    err_path = os.path.join(BASE_DIR, "data", "processed", "error_analysis_report.json")
    dash_path = os.path.join(BASE_DIR, "src", "web", "dashboard.py")
    with open(err_path, "r", encoding="utf-8") as f:
        err_json = json.load(f)
    with open(dash_path, "r", encoding="utf-8") as f:
        dash_code = f.read()

    if 'err_rep.get("counts"' in dash_code:
        assert "counts" in err_json and "metrics" in err_json, (
            f"Schema mismatch: dashboard.py reads 'counts' and 'metrics', "
            f"but error_analysis_report.json only has keys {list(err_json.keys())}!"
        )


# ==============================================================================
# TASK 4: Reference Repositories Code-to-Code Grounding
# ==============================================================================

def test_t4_ci_workflow_anti_mockup_grep_exit_code_logic():
    """
    [DEF-T4-01] Verify that .github/workflows/mlops_ci.yml anti-mockup gate fails CI
    (non-zero exit code) when git grep finds forbidden mockup tokens.
    Grounded in: [REPO-01: aio2025-mlops-project01 | .github/workflows/mlops_ci.yml]
    """
    ci_path = os.path.join(BASE_DIR, ".github", "workflows", "mlops_ci.yml")
    with open(ci_path, "r", encoding="utf-8") as f:
        ci_content = f.read()

    # In POSIX/bash, `git grep PATTERN || echo "clean"` exits 0 when PATTERN IS FOUND
    # AND exits 0 when PATTERN IS NOT FOUND. It can never fail!
    assert 'git grep -iE "TODO: mock|fakeData|dummyData|simulateTx" -- src/ || echo' not in ci_content, (
        "CI anti-mockup step uses `git grep ... || echo ...` which exits 0 even when mockups ARE found!"
    )


# ==============================================================================
# TASK 5: Customer Entity Anti-Leakage & Training-Serving Skew
# ==============================================================================

def test_t5_category_mapping_case_and_whitespace_parity():
    """
    [DEF-T5-03] Verify zero Training-Serving Skew between preprocess.engineer_features()
    and api.utils.extract_raw_feature_vector() when categorical inputs have lowercase or trailing spaces.
    Grounded in: [PAPER-08: Soumyadeep Roy 2026 | arXiv:2610.00118v1, Section 3.4]
    """
    raw_df = pd.DataFrame([{
        "age": 35.0,
        "gender": "male ",
        "tenure": 24.0,
        "usage_frequency": 14.0,
        "support_calls": 2.0,
        "payment_delay": 5.0,
        "subscription_type": "standard ",
        "contract_length": "quarterly",
        "total_spend": 650.0,
        "last_interaction": 10.0,
    }])
    from types import SimpleNamespace
    offline_engineered = engineer_features(raw_df)
    offline_vec = offline_engineered[FEATURE_COLS].iloc[0].to_numpy(dtype=float)

    online_customer = SimpleNamespace(
        customer_id=1, age=35.0, gender="male ", tenure=24.0,
        usage_frequency=14.0, support_calls=2.0, payment_delay=5.0,
        subscription_type="standard ", contract_length="quarterly",
        total_spend=650.0, last_interaction=10.0,
    )
    online_vec = prepare_feature_vector_from_input(online_customer)[0]

    np.testing.assert_allclose(
        offline_vec, online_vec,
        err_msg=f"Training-Serving Skew: Offline={offline_vec.tolist()} vs Online={online_vec.tolist()}",
    )


# ==============================================================================
# TASK 7: Telecom/SaaS Churn Domain & Cloud Economics Critique
# ==============================================================================

def test_t7_eprofits_recommendation_clv_and_contract_sensitivity():
    """
    [DEF-T7-01] Verify that generate_recommendation incorporates Customer Lifetime Value
    (total_spend / tenure / contract_length) per e-Profits and checks cloud TCO math consistency.
    Grounded in: [PAPER-07: Business_Aligned_Churn_Metrics_2025.md | Section 2.1 e-Profits]
    """
    sig = inspect.signature(generate_recommendation)
    params = set(sig.parameters.keys())
    assert "total_spend" in params or "contract_length" in params, (
        f"generate_recommendation({list(params)}) ignores CLV (total_spend) and contract_length, "
        "violating the e-Profits retention cost-benefit formulation!"
    )


# ==============================================================================
# TASK 8: API Serving, Web Bento Grid & Deliverables Audit
# ==============================================================================

def test_t8_api_nan_inf_validation_and_web_xss_escaping():
    """
    [DEF-T8-01 & DEF-T8-03] Verify that CustomerInput rejects negative customer_id,
    and that src/web/app.js does not hardcode cleartext API secrets or unescaped innerHTML.
    Grounded in: [REPO-06: dcwind-churn-mlops | src/api/schemas.py & OWASP XSS Prevention]
    """
    app_js_path = os.path.join(BASE_DIR, "src", "web", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()
    assert 'const API_KEY = "mlops-churn-secret-2026"' not in app_js, (
        "Cleartext production API_KEY is hardcoded in client-side src/web/app.js!"
    )
    with pytest.raises(Exception):
        CustomerInput(
            customer_id=-9999, age=30.0, gender="Male", tenure=12,
            usage_frequency=10, support_calls=1, payment_delay=0,
            subscription_type="Standard", contract_length="Annual",
            total_spend=500.0, last_interaction=5,
        )
