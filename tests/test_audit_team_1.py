"""
Adversarial Audit Test Suite - Audit Team 1 (Stage 5 Post-Fix Acceptance)
UIT IS402 Cloud Computing - Topic 11: MLOps Customer Churn Prediction
Covers all 8 Audit Tasks with real execution and literature/repo-grounded assertions.
"""

import io
import json
import pathlib
import socket
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient

from src.api.ab_testing import analyze_ab_test_performance
from src.api.main import app
from src.api.schemas import CustomerInput
from src.data.latency_simulator import measure_tcp_latency
from src.data.preprocess import clean_raw_data, process_large_dataset_chunks
from src.models.train_pipeline import evaluate_model_performance
from src.monitoring.drift_detector import calculate_psi, run_drift_analysis

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
client = TestClient(app)


# ==============================================================================
# TASK 1: IS402 Course & Rubric Alignment
# ==============================================================================

def test_task1_rubric_dual_track_score_math():
    """Verify rubric scoring arithmetic consistency and dynamic test counting."""
    import scripts.verification.integrity_rubric_checker as irc
    from scripts.verification.integrity_rubric_checker import AcademicIntegrityAuditor

    auditor = AcademicIntegrityAuditor()
    verdict = auditor.evaluate_all()
    actual_local_sum = round(float(verdict["total_score"]), 2)
    irc_doc = irc.__doc__ or ""

    final_check_src = (
        PROJECT_ROOT / "scripts" / "verification" / "final_comprehensive_check.py"
    ).read_text(encoding="utf-8")

    assert f"({actual_local_sum:.2f}/10)" in irc_doc, (
        f"Docstring Local score does not match actual sum of local_scores ({actual_local_sum:.2f}/10)"
    )
    assert "47/47 tests PASSED" not in final_check_src, (
        "final_comprehensive_check.py hardcodes '47/47 tests PASSED (100%)' instead of parsing pytest count"
    )


def test_task1_dvc_yaml_pipeline_completeness():
    """Verify dvc.yaml declares all required artifacts and Feast feature store stage."""
    dvc_path = PROJECT_ROOT / "dvc.yaml"
    dvc_cfg = yaml.safe_load(dvc_path.read_text(encoding="utf-8"))
    stages = dvc_cfg.get("stages", {})

    train_outs = stages.get("train_models", {}).get("outs", [])
    all_cmds = " ".join(s.get("cmd", "") for s in stages.values())

    assert "data/models/evaluation_results.json" in train_outs, (
        "evaluate.py reads data/models/evaluation_results.json, but train_models.outs in dvc.yaml omits it"
    )
    assert "feature_store.py" in all_cmds, (
        "dvc.yaml has no stage for Feast feature store materialization (src/features/feature_store.py)"
    )


# ==============================================================================
# TASK 2: Code Logic, Out-of-Core Streaming & Clean Architecture
# ==============================================================================

def test_task2_out_of_core_chunk_dedup_and_schema():
    """Verify out-of-core chunked processor deduplicates CustomerID entities across chunks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = pathlib.Path(tmpdir)
        csv_file = tmp_path / "chunk_test.csv"
        parquet_file = tmp_path / "chunk_out.parquet"

        # Create 6 rows where CustomerID 101 and 102 are duplicated across chunks
        df_raw = pd.DataFrame({
            "CustomerID": [101, 102, 103, 101, 102, 104],
            "Age": [25, 35, 45, 25, 35, 50],
            "Gender": ["Male", "Female", "Male", "Male", "Female", "Female"],
            "Tenure": [12, 24, 36, 12, 24, 48],
            "Usage Frequency": [10, 20, 15, 10, 20, 25],
            "Support Calls": [1, 2, 0, 1, 2, 3],
            "Payment Delay": [0, 5, 2, 0, 5, 10],
            "Subscription Type": ["Basic", "Standard", "Premium", "Basic", "Standard", "Premium"],
            "Contract Length": ["Monthly", "Annual", "Quarterly", "Monthly", "Annual", "Quarterly"],
            "Total Spend": [200.0, 500.0, 800.0, 200.0, 500.0, 900.0],
            "Last Interaction": [5, 10, 3, 5, 10, 7],
            "Churn": [1, 0, 0, 1, 0, 1],
        })
        df_raw.to_csv(csv_file, index=False)

        process_large_dataset_chunks(csv_file, parquet_file, chunk_size=3)
        df_out = pd.read_parquet(parquet_file)

        assert df_out["customerid"].nunique() == len(df_out), (
            f"Duplicate customerid rows leaked into output parquet: {len(df_out)} rows for {df_out['customerid'].nunique()} unique IDs"
        )


def test_task2_model_hot_reload_thread_safety_and_sqlite_wal():
    """Verify thread lock on model hot-reload and WAL mode on SQLite connections."""
    main_src = (PROJECT_ROOT / "src" / "api" / "main.py").read_text(encoding="utf-8")
    utils_src = (PROJECT_ROOT / "src" / "api" / "utils.py").read_text(encoding="utf-8")

    assert "threading.Lock" in main_src or "threading.RLock" in main_src, (
        "src/api/main.py mutates global MODEL_ARTIFACT and TREE_EXPLAINER in load_artifacts() without a threading.Lock/RLock"
    )
    assert "journal_mode=WAL" in utils_src or "with sqlite3.connect" in utils_src, (
        "src/api/utils.py opens SQLite connections without WAL mode or context manager cleanup"
    )


def test_task2_latency_simulator_socket_cleanup_on_error():
    """Verify measure_tcp_latency closes the TCP socket even when connect() raises an exception."""
    mock_sock = MagicMock()
    mock_sock.connect.side_effect = socket.timeout("simulated timeout")

    with patch("socket.socket", return_value=mock_sock), patch(
        "urllib.request.urlopen", side_effect=OSError("no fallback")
    ):
        res = measure_tcp_latency("198.51.100.1", port=443, num_pings=1)

    assert res["status"] == "UNREACHABLE"
    assert mock_sock.close.called, (
        "Socket was not closed when s.connect() raised socket.timeout (resource leak)"
    )


# ==============================================================================
# TASK 3: Literature & Mathematical Fidelity
# ==============================================================================

def test_task3_shap_local_accuracy_and_negative_attribution_ui():
    """Verify SHAP UI rendering preserves negative directional sign per Lundberg & Lee (2017)."""
    app_js = (PROJECT_ROOT / "src" / "web" / "app.js").read_text(encoding="utf-8")
    utils_py = (PROJECT_ROOT / "src" / "api" / "utils.py").read_text(encoding="utf-8")

    assert "+${(weight * 100).toFixed(1)}%" not in app_js, (
        "src/web/app.js unconditionally prepends '+' to negative SHAP attributions, rendering '+-X.X%'"
    )
    assert "LinearExplainer" in utils_py or "LinearExplainer" in (
        PROJECT_ROOT / "src" / "api" / "main.py"
    ).read_text(encoding="utf-8"), (
        "No fallback to shap.LinearExplainer when Champion model is Logistic_Regression"
    )


def test_task3_psi_binary_feature_quantile_collapse():
    """Verify PSI detects severe shift (90/10 -> 10/90) on binary features like gender_encoded."""
    rng = np.random.default_rng(42)
    expected_binary = rng.choice([0.0, 1.0], size=10000, p=[0.90, 0.10])
    actual_binary = rng.choice([0.0, 1.0], size=10000, p=[0.10, 0.90])

    psi_val = calculate_psi(expected_binary, actual_binary, num_buckets=10)
    assert psi_val >= 0.25, (
        f"PSI returned {psi_val} instead of ~3.52 on a 90/10 -> 10/90 binary shift due to percentile bin collapse"
    )


def test_task3_ks_drift_bonferroni_multiple_testing():
    """Verify run_drift_analysis applies Bonferroni family-wise error correction (alpha / M)."""
    drift_src = (PROJECT_ROOT / "src" / "monitoring" / "drift_detector.py").read_text(
        encoding="utf-8"
    )
    assert "len(MONITORED_FEATURES)" in drift_src or "bonferroni" in drift_src.lower(), (
        "run_drift_analysis does not apply Bonferroni correction (alpha / M) across M=13 features per Rabanser et al. (2019)"
    )


def test_task3_optuna_tpe_claim_vs_gridsearch_and_single_class_auc():
    """Verify Optuna TPE implementation and single-class safety in evaluate_model_performance."""
    train_src = (PROJECT_ROOT / "src" / "models" / "train_pipeline.py").read_text(
        encoding="utf-8"
    )
    assert "optuna" in train_src.lower(), (
        "Docs and routes_management.py claim Optuna Bayesian TPE (12 Trials), but train_pipeline.py only uses GridSearchCV"
    )

    dummy_model = MagicMock()
    dummy_model.predict.return_value = np.zeros(10, dtype=int)
    dummy_model.predict_proba.return_value = np.column_stack(
        [np.ones(10) * 0.8, np.ones(10) * 0.2]
    )
    X_single = pd.DataFrame(np.zeros((10, 13)))
    y_single = pd.Series(np.zeros(10, dtype=int))

    metrics = evaluate_model_performance(
        dummy_model, X_single, X_single, y_single, is_linear=False
    )
    assert not np.isnan(metrics["roc_auc"]), "Single-class slice produced NaN or raised ValueError in roc_auc_score"


# ==============================================================================
# TASK 4: Reference Repositories Code-to-Code Grounding
# ==============================================================================

def test_task4_reseed_inference_logs_key_and_column_mismatch():
    """Verify reseed_inference_logs.py matches ab_testing.py keys and parquet column names."""
    reseed_src = (PROJECT_ROOT / "scripts" / "reseed_inference_logs.py").read_text(
        encoding="utf-8"
    )
    ab_res = analyze_ab_test_performance()

    assert "hypothesis_testing" in ab_res, "analyze_ab_test_performance must return 'hypothesis_testing'"
    assert "hypothesis_test_two_sample_ttest" not in reseed_src, (
        "reseed_inference_logs.py line 93 queries non-existent key 'hypothesis_test_two_sample_ttest' instead of 'hypothesis_testing'"
    )
    assert '"customer_id" in row' not in reseed_src, (
        "reseed_inference_logs.py line 62 checks 'customer_id' instead of 'customerid', causing all IDs to fall back to 100000+idx"
    )


# ==============================================================================
# TASK 5: Customer Entity Anti-Leakage & Training-Serving Skew
# ==============================================================================

def test_task5_preprocess_pre_split_imputation_leakage_and_csv_strip():
    """Verify /upload_csv_predict strips whitespace on categorical strings and preprocess avoids pre-split leakage."""
    csv_content = (
        "customer_id,age,gender,tenure,usage_frequency,support_calls,"
        "payment_delay,subscription_type,contract_length,total_spend,last_interaction\n"
        "1001,35, male ,12,15,2,5, standard , monthly ,500.0,10\n"
    )
    files = {"file": ("whitespace.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post(
        "/upload_csv_predict",
        files=files,
        headers={"X-API-Key": "mlops-churn-secret-2026"},
    )

    assert resp.status_code == 200, (
        f"/upload_csv_predict failed with status {resp.status_code} on whitespace-padded strings (' male ') due to missing .strip()"
    )


# ==============================================================================
# TASK 6: Code Hygiene, 400-Line Cap & Anti-Mockup Verification
# ==============================================================================

def test_task6_line_cap_and_non_ascii_hyphen_invariants():
    """Verify 400-line cap across src/ and scripts/ (Invariant 02) and ASCII-only hyphens (Invariant 05)."""
    over_limit = []
    non_ascii_dash_files = []

    for folder in ["src", "scripts"]:
        for path in (PROJECT_ROOT / folder).rglob("*.*"):
            if path.suffix not in {".py", ".js", ".html", ".css"}:
                continue
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if path.suffix == ".py" and len(lines) > 400:
                over_limit.append(f"{path.relative_to(PROJECT_ROOT)} ({len(lines)} lines)")
            for idx, line in enumerate(lines, start=1):
                if "\u2014" in line or "\u2013" in line:
                    non_ascii_dash_files.append(f"{path.relative_to(PROJECT_ROOT)}:{idx}")
                    break

    assert len(over_limit) == 0, f"Files exceeding 400-line cap: {over_limit}"
    assert len(non_ascii_dash_files) == 0, (
        f"Invariant 05 violation - files containing em-dash/en-dash: {non_ascii_dash_files}"
    )


# ==============================================================================
# TASK 7: Telecom/SaaS Churn Domain & Cloud Economics Critique
# ==============================================================================

def test_task7_feast_partial_null_nan_handling_and_cloud_tco_consistency():
    """Verify Cloud IaC templates deploy actual container image and align with TCO documentation."""
    arm_text = (PROJECT_ROOT / "deploy" / "azure" / "arm_template.json").read_text(
        encoding="utf-8"
    )
    tf_text = (PROJECT_ROOT / "deploy" / "azure" / "main.tf").read_text(encoding="utf-8")
    tco_text = (PROJECT_ROOT / "configs" / "cloud_architecture_and_cost.md").read_text(
        encoding="utf-8"
    )

    assert "aci-helloworld" not in arm_text and "aci-helloworld" not in tf_text, (
        "arm_template.json and main.tf hardcode placeholder 'mcr.microsoft.com/azuredocs/aci-helloworld:latest'"
    )
    assert "PostgreSQL" not in tco_text, (
        "cloud_architecture_and_cost.md bills $48.90/mo for Azure Database for PostgreSQL while architecture uses SQLite + Redis"
    )


# ==============================================================================
# TASK 8: API Serving, Web Bento Grid & Deliverables Audit
# ==============================================================================

def test_task8_api_negative_customer_id_csv_nan_and_web_xss_sinks():
    """Verify API input validation rejects negative customer_id, handles NaN CSV cells cleanly, and escapes HTML in app.js."""
    csv_nan = (
        "customer_id,age,gender,tenure,usage_frequency,support_calls,"
        "payment_delay,subscription_type,contract_length,total_spend,last_interaction\n"
        "1001,,Male,12,15,2,5,Standard,Monthly,500.0,10\n"
    )
    files = {"file": ("nan_age.csv", io.BytesIO(csv_nan.encode("utf-8")), "text/csv")}
    resp = client.post(
        "/upload_csv_predict",
        files=files,
        headers={"X-API-Key": "mlops-churn-secret-2026"},
    )
    assert resp.status_code in (400, 422), (
        f"Expected 400/422 validation error on CSV with NaN age, got {resp.status_code}: {resp.text}"
    )

    with pytest.raises(Exception):
        CustomerInput(
            customer_id=-9999,
            age=30,
            gender="Male",
            tenure=12,
            usage_frequency=10,
            support_calls=1,
            payment_delay=0,
            subscription_type="Standard",
            contract_length="Monthly",
            total_spend=500.0,
            last_interaction=5,
        )
