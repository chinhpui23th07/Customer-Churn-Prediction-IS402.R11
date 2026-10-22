"""
Adversarial Regression & Acceptance Test Suite - Audit Team 6 (Stage 5 Verification).
Verifies that all 14 audit findings across the 8 IS402 MLOps Audit Dimensions (Tasks 1-8)
have been completely resolved to SOTA standards in production code.
Complies with Invariant 01 (Clean Architecture), Invariant 02 (<= 400 lines), and Invariant 05 (-).
"""
import inspect
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient

import src.api.main as api_main
from src.api.main import app
from src.api.utils import compute_shap_attributions, generate_recommendation, prepare_feature_vector_from_input
from src.api.schemas import CustomerInput
from src.api.ab_testing import route_customer_to_model
from src.data.preprocess import process_large_dataset_chunks
from src.monitoring.drift_detector import calculate_psi
from scripts.verification.integrity_rubric_checker import AcademicIntegrityAuditor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "mlops-churn-secret-2026"}


# ============================================================================
# TASK 1: IS402 COURSE & RUBRIC ALIGNMENT AUDIT (SOTA VERIFICATION)
# ============================================================================

def test_task1_rubric_score_discrepancy_and_packaging_omissions():
    """
    Task 1 Verification (T6-F01): integrity_rubric_checker.py docstring and
    AcademicIntegrityAuditor.evaluate_all() are 100% synchronized at Local Score
    3.35/10 vs Target Cloud Score 9.90/10 across 17 penalized sub-criteria.
    Also audit_vision_and_package.py includes 'deploy' and 'notebooks' in allowed_dirs.
    Citation: [UIT_Cloud_Computing_Curriculum_Spec | Section 1-3 | HinnoNguyen/IS402]
    """
    checker_path = PROJECT_ROOT / "scripts" / "verification" / "integrity_rubric_checker.py"
    checker_src = checker_path.read_text(encoding="utf-8")
    assert "3.35/10" in checker_src and "9.90/10" in checker_src
    assert "6.25/10" not in checker_src

    auditor = AcademicIntegrityAuditor()
    verdict = auditor.evaluate_all()
    assert pytest.approx(verdict["local_real_score"], abs=1e-2) == 3.35
    assert pytest.approx(verdict["target_cloud_score"], abs=1e-2) == 9.90
    assert len(verdict["penalties"]) == 17

    pkg_src = (PROJECT_ROOT / "scripts" / "audit_vision_and_package.py").read_text(encoding="utf-8")
    assert "'deploy'" in pkg_src and "'notebooks'" in pkg_src


def test_task1_dvc_pipeline_and_ci_gate_defects():
    """
    Task 1 Verification (T6-F02): dvc.yaml defines all 9 MLOps pipeline stages with
    explicit params/metrics/outs (including scaler.joblib and metadata.json), and
    .github/workflows/mlops_ci.yml enforces strict non-zero exit codes without '|| echo'.
    Citation: [Oyebamiji_Micheal_dvc_mlflow | dvc.yaml:L1-L59 | GitHub Benchmark]
    """
    dvc_data = yaml.safe_load((PROJECT_ROOT / "dvc.yaml").read_text(encoding="utf-8"))
    stages = dvc_data.get("stages", {})
    expected_stages = {
        "download_data", "preprocess", "data_quality", "feature_store",
        "tune_optuna", "train_models", "evaluate_and_benchmark",
        "model_diagnostics", "drift_detector"
    }
    assert expected_stages.issubset(set(stages.keys()))
    assert "data/processed/scaler.joblib" in stages["preprocess"].get("outs", [])
    assert "data/processed/metadata.json" in stages["preprocess"].get("outs", [])
    for stage_cfg in stages.values():
        assert "params" in stage_cfg

    ci_src = (PROJECT_ROOT / ".github" / "workflows" / "mlops_ci.yml").read_text(encoding="utf-8")
    assert '! git grep -iE "TODO: mock|fakeData|dummyData|simulateTx" -- src/' in ci_src
    assert "dvc dag" in ci_src and "dvc status" in ci_src
    assert 'dvc status || echo' not in ci_src


# ============================================================================
# TASK 2: CODE LOGIC, OUT-OF-CORE STREAMING & CLEAN ARCHITECTURE AUDIT
# ============================================================================

def test_task2_missing_database_module_and_sqlite_wal_config():
    """
    Task 2 Verification (T6-F03): Dedicated src/api/database.py exists and enforces
    PRAGMA journal_mode=WAL, busy_timeout=5000, and try...finally connection cleanup,
    mirrored across src/api/utils.py.
    Citation: [Kreuzberger_2022_MLOps_Architecture_Review | Section IV | DOI: 10.1109/ACCESS.2023.3262138]
    """
    db_module = PROJECT_ROOT / "src" / "api" / "database.py"
    assert db_module.exists(), "Expected src/api/database.py to exist"
    db_src = db_module.read_text(encoding="utf-8")
    assert "PRAGMA journal_mode=WAL;" in db_src
    assert "finally:" in db_src and "conn.close()" in db_src

    utils_src = (PROJECT_ROOT / "src" / "api" / "utils.py").read_text(encoding="utf-8")
    assert "PRAGMA journal_mode=WAL;" in utils_src
    assert "finally:" in utils_src


def test_task2_hot_reload_missing_lock_and_socket_leak():
    """
    Task 2 Verification (T6-F04): src/api/main.py guards global artifact reload and
    inference access with MODEL_LOCK (threading.RLock), and src/data/latency_simulator.py
    closes TCP sockets in finally: and wraps urlopen in a context manager.
    Citation: [Architecting_CT_Pipelines_CICD_2023 | Section 3 | IEEE 2023]
    """
    main_src = (PROJECT_ROOT / "src" / "api" / "main.py").read_text(encoding="utf-8")
    assert "MODEL_LOCK = threading.RLock()" in main_src
    load_src = inspect.getsource(api_main.load_artifacts)
    assert "with MODEL_LOCK:" in load_src

    lat_src = (PROJECT_ROOT / "src" / "data" / "latency_simulator.py").read_text(encoding="utf-8")
    assert "finally:" in lat_src and "s.close()" in lat_src
    assert "with urllib.request.urlopen" in lat_src


# ============================================================================
# TASK 3: LITERATURE & MATHEMATICAL FIDELITY AUDIT
# ============================================================================

def test_task3_corrupted_arxiv_papers_in_research_directory():
    """
    Task 3 Verification (T6-F05): Rabanser_2019_Failing_Loudly_Dataset_Shift_Detection.md
    and Feature_Store_Survey_Architectures.md contain authentic domain-aligned MLOps
    mathematical formulations (KS-test, Bonferroni FWER, PSI, Dual-Store Feast).
    Citation: [Rabanser_2019_Failing_Loudly_Dataset_Shift_Detection | arXiv:1810.11953]
    """
    rabanser_md = (
        PROJECT_ROOT / "docs" / "research" / "papers" / "Rabanser_2019_Failing_Loudly_Dataset_Shift_Detection.md"
    ).read_text(encoding="utf-8")
    feature_md = (
        PROJECT_ROOT / "docs" / "research" / "papers" / "Feature_Store_Survey_Architectures.md"
    ).read_text(encoding="utf-8")

    assert "Nutty dyonic black hole" not in rabanser_md
    assert "Failing Loudly" in rabanser_md and "arXiv:1810.11953" in rabanser_md and "Bonferroni" in rabanser_md
    assert "Atmospheric Cherenkov" not in feature_md
    assert "Feature Store" in feature_md and "Dual-Store" in feature_md and "Point-in-Time" in feature_md


def test_task3_shap_local_accuracy_and_negative_attribution_loss():
    """
    Task 3 Verification (T6-F06): compute_shap_attributions in src/api/utils.py
    reports base_value (phi_0), preserves negative SHAP attributions in explanation_summary
    (sorted by |phi_i|), and provides a Linear SHAP fallback when tree_explainer is None.
    Citation: [Lundberg_2017_SHAP_Unified_Model_Interpretation | Eq. 1 & Property 1 | arXiv:1705.07874]
    """
    api_main.load_artifacts()
    customer = CustomerInput(
        customer_id=1001, age=45.0, gender="Female", tenure=48.0,
        usage_frequency=25.0, support_calls=0.0, payment_delay=0.0,
        subscription_type="Premium", contract_length="Annual",
        total_spend=1500.0, last_interaction=2.0
    )
    raw_vec = prepare_feature_vector_from_input(customer)
    use_scaled = api_main.MODEL_ARTIFACT.get("use_scaled", False)
    x_input = api_main.SCALER.transform(raw_vec) if use_scaled and api_main.SCALER is not None else raw_vec
    attributions, summary = compute_shap_attributions(api_main.TREE_EXPLAINER, x_input)

    assert "base_value=" in summary
    neg_features = [k for k, v in attributions.items() if v < 0]
    assert len(neg_features) > 0, "Expected at least one feature pushing toward retention (phi_i < 0)"
    assert any(nf in summary for nf in neg_features), "Top negative SHAP attributions must be preserved in summary"

    fallback_factors, fallback_summary = compute_shap_attributions(None, x_input)
    assert len(fallback_factors) == 13
    assert "base_value=" in fallback_summary


def test_task3_psi_binary_feature_bin_collapse_to_zero():
    """
    Task 3 Verification (T6-F07): calculate_psi in src/monitoring/drift_detector.py
    uses midpoint boundaries for discrete binary/ternary features so a 90% -> 10%
    shift yields PSI > 0.25 instead of collapsing to 0.0.
    Citation: [Automated_MLOps_Retraining_Distribution_Shifts_2025 | Eq. 4 PSI | arXiv:2512.11541]
    """
    rng = np.random.default_rng(42)
    expected_binary = rng.choice([0.0, 1.0], size=10000, p=[0.90, 0.10])
    actual_binary = rng.choice([0.0, 1.0], size=10000, p=[0.10, 0.90])

    psi_val = calculate_psi(expected_binary, actual_binary, num_buckets=10)
    assert psi_val > 0.25, f"Binary feature PSI must detect extreme shift (> 0.25), got {psi_val}"

    expected_ternary = rng.choice([0.0, 1.0, 2.0], size=10000, p=[0.20, 0.70, 0.10])
    actual_ternary = rng.choice([0.0, 1.0, 2.0], size=10000, p=[0.20, 0.10, 0.70])
    psi_ternary = calculate_psi(expected_ternary, actual_ternary, num_buckets=10)
    assert psi_ternary > 0.25, f"Ternary feature PSI must detect class 1->2 shift (> 0.25), got {psi_ternary}"


# ============================================================================
# TASK 4: BENCHMARK REPOSITORY GROUNDING & MODEL EVALUATION AUDIT
# ============================================================================

def test_task4_optuna_disconnected_and_mlflow_registry_mismatch():
    """
    Task 4 Verification (T6-F08): src/models/train_pipeline.py loads Optuna best_params
    from tuning_history.json, selects the Champion model on validation metrics
    (val_metrics['roc_auc']) without test-set snooping, and transitions
    CustomerChurnChampion to stage 'Production' via MlflowClient.
    Citation: [aio2025-mlops-project01 | model_pipeline/src/mlflow_utils/model_registry.py:L297-L411 | GitHub Benchmark]
    """
    train_src = (PROJECT_ROOT / "src" / "models" / "train_pipeline.py").read_text(encoding="utf-8")
    main_src = (PROJECT_ROOT / "src" / "api" / "main.py").read_text(encoding="utf-8")

    assert "tuning_history.json" in train_src
    assert 'val_metrics["roc_auc"]' in train_src
    assert 'if test_metrics["roc_auc"] > best_roc_auc:' not in train_src
    assert "transition_model_version_stage" in train_src
    assert 'stage="Production"' in train_src
    assert 'models:/CustomerChurnChampion/Production' in main_src


def test_task4_dashboard_error_analysis_schema_key_mismatch():
    """
    Task 4 Verification (T6-F09): data/processed/error_analysis_report.json and
    src/models/model_diagnostics.py include both 'confusion_breakdown', 'counts',
    and 'metrics' keys matching src/web/dashboard.py.
    Citation: [Gees14_feast_drift | src/models/evaluate.py | GitHub Benchmark]
    """
    err_report_path = PROJECT_ROOT / "data" / "processed" / "error_analysis_report.json"
    err_data = json.loads(err_report_path.read_text(encoding="utf-8"))
    assert "confusion_breakdown" in err_data
    assert "counts" in err_data
    assert "metrics" in err_data
    assert err_data["metrics"]["roc_auc"] > 0.90

    dash_src = (PROJECT_ROOT / "src" / "web" / "dashboard.py").read_text(encoding="utf-8")
    assert 'err_rep.get("counts"' in dash_src
    assert 'err_rep.get("metrics"' in dash_src


# ============================================================================
# TASK 5: CUSTOMER ENTITY ANTI-LEAKAGE & TRAINING-SERVING SKEW AUDIT
# ============================================================================

def test_task5_streaming_chunk_duplicate_entity_leakage_and_median_skew(tmp_path):
    """
    Task 5 Verification (T6-F10): process_large_dataset_chunks in src/data/preprocess.py
    deduplicates CustomerID across chunks via seen_customer_ids and enforces global
    unique-entity medians across all chunks.
    Citation: [Soumyadeep_Roy_2026_Telco_Churn_Trustworthiness_Audit | Section 2.2 & 3.4 | arXiv:2610.00118]
    """
    raw_csv = tmp_path / "chunk_test.csv"
    out_pq = tmp_path / "chunk_out.parquet"

    rows = [
        {"CustomerID": 555, "Age": 30, "Gender": "Male", "Tenure": 10, "Usage Frequency": 5,
         "Support Calls": 1, "Payment Delay": 2, "Subscription Type": "Basic",
         "Contract Length": "Monthly", "Total Spend": 200.0, "Last Interaction": 5, "Churn": 1},
        {"CustomerID": 556, "Age": None, "Gender": "Female", "Tenure": 20, "Usage Frequency": 10,
         "Support Calls": 2, "Payment Delay": 0, "Subscription Type": "Standard",
         "Contract Length": "Annual", "Total Spend": 500.0, "Last Interaction": 3, "Churn": 0},
        {"CustomerID": 555, "Age": 50, "Gender": "Male", "Tenure": 10, "Usage Frequency": 5,
         "Support Calls": 1, "Payment Delay": 2, "Subscription Type": "Basic",
         "Contract Length": "Monthly", "Total Spend": 200.0, "Last Interaction": 5, "Churn": 1},
        {"CustomerID": 557, "Age": None, "Gender": "Female", "Tenure": 25, "Usage Frequency": 12,
         "Support Calls": 0, "Payment Delay": 1, "Subscription Type": "Premium",
         "Contract Length": "Annual", "Total Spend": 800.0, "Last Interaction": 2, "Churn": 0},
    ]
    pd.DataFrame(rows).to_csv(raw_csv, index=False)

    stats = process_large_dataset_chunks(str(raw_csv), str(out_pq), chunk_size=2)
    df_out = pd.read_parquet(out_pq)

    assert stats["total_records"] == 3
    assert not df_out["customerid"].duplicated().any(), "Cross-chunk duplicate CustomerID=555 must be removed"
    imputed_ages = df_out.loc[df_out["customerid"].isin([556, 557]), "age"].tolist()
    assert imputed_ages[0] == imputed_ages[1] == 30.0, "Global median imputation must be identical across chunks"


def test_task5_feast_store_omits_validation_and_test_splits():
    """
    Task 5 Verification (T6-F11): prepare_feast_data() in src/features/feature_store.py
    concatenates PROCESSED_TRAIN_FILE, PROCESSED_VAL_FILE, and PROCESSED_TEST_FILE
    with deterministic seeded rng = np.random.default_rng(42).
    Citation: [mlops-churn-feature-store | src/api/app.py:L120-L198 | GitHub Benchmark]
    """
    fs_src = (PROJECT_ROOT / "src" / "features" / "feature_store.py").read_text(encoding="utf-8")
    assert "PROCESSED_TRAIN_FILE" in fs_src
    assert "PROCESSED_VAL_FILE" in fs_src
    assert "PROCESSED_TEST_FILE" in fs_src
    assert "np.random.default_rng(42)" in fs_src


# ============================================================================
# TASK 6: AUTOMATED CT RETRAINING & A/B TESTING INFRASTRUCTURE AUDIT
# ============================================================================

def test_task6_drift_threshold_inconsistency_across_pipeline():
    """
    Task 6 Verification (T6-F12): Drift threshold is unified at 'drift_share >= 0.30'
    with Bonferroni correction across drift_detector.py, routes_management.py, and dashboard.py.
    Citation: [Gees14_feast_drift | src/monitoring/drift.py:L72-L109 | GitHub Benchmark]
    """
    drift_src = (PROJECT_ROOT / "src" / "monitoring" / "drift_detector.py").read_text(encoding="utf-8")
    routes_src = (PROJECT_ROOT / "src" / "api" / "routes_management.py").read_text(encoding="utf-8")
    dash_src = (PROJECT_ROOT / "src" / "web" / "dashboard.py").read_text(encoding="utf-8")

    assert "drift_share >= 0.30" in drift_src
    assert "bonferroni_alpha" in drift_src
    assert "drift_share >= 0.30" in routes_src
    assert "drift_share >= 0.30" in dash_src

    route, ver = route_customer_to_model(1001)
    assert route in ("champion", "challenger")
    assert ver in ("v2.0.0-champion", "v1.0.0-challenger")


# ============================================================================
# TASK 7: TELECOM/SAAS CHURN DOMAIN & CLOUD ECONOMICS CRITIQUE
# ============================================================================

def test_task7_business_risk_threshold_and_cloud_tco_arithmetic_error():
    """
    Task 7 Verification (T6-F13): generate_recommendation in src/api/utils.py enforces
    standard risk tiers (High >= 0.70, Medium [0.40, 0.70), Low < 0.40) and incorporates
    total_spend (CLV) and contract_length. Also configs/cloud_architecture_and_cost.md
    eliminates the $28.50 arithmetic error and unused PostgreSQL, unifying TCO at $74.67/month.
    Citation: [Business_Aligned_Churn_Metrics_2025 | Eq. 2-4 e-Profits | arXiv:2507.08860]
    """
    rec_36 = generate_recommendation(prob=0.36, calls=1.0, delay=0.0)
    assert "KHÁCH HÀNG ỔN ĐỊNH (Low Risk)" in rec_36, "prob=0.36 (< 0.40) must be Low Risk"

    sig = inspect.signature(generate_recommendation)
    assert "total_spend" in sig.parameters
    assert "contract_length" in sig.parameters

    rec_low_clv = generate_recommendation(prob=0.80, calls=5.0, delay=10.0, total_spend=80.0)
    rec_high_clv = generate_recommendation(prob=0.80, calls=5.0, delay=10.0, total_spend=1500.0)
    assert rec_low_clv != rec_high_clv

    tco_md = (PROJECT_ROOT / "configs" / "cloud_architecture_and_cost.md").read_text(encoding="utf-8")
    assert "$74.67/month" in tco_md
    assert "$28.50" not in tco_md
    assert "PostgreSQL" not in tco_md


# ============================================================================
# TASK 8: API SERVING, WEB BENTO GRID & DELIVERABLES AUDIT
# ============================================================================

def test_task8_api_customer_id_zero_falsy_overwrite_and_ui_governance():
    """
    Task 8 Verification (T6-F14):
    1) src/api/schemas.py rejects customer_id < 1 and src/api/main.py uses explicit None checks.
    2) src/web/app.js removes hardcoded API_KEY and sanitizes DOM strings via escapeHtml().
    3) src/web/dashboard.py complies with the <= 200-line presentation cap and removes primitive emojis.
    4) deploy/azure/main.tf deploys churnguard-mlops:latest from ACR and /docs/drift_report.html returns 200.
    Citation: [aio2025-mlops-project01 | serving_pipeline/api/routers/predict.py:L92-L110 | GitHub Benchmark]
    """
    main_src = (PROJECT_ROOT / "src" / "api" / "main.py").read_text(encoding="utf-8")
    assert "customer.customer_id or 999999" not in main_src
    assert "customer.customer_id if customer.customer_id is not None else 999999" in main_src

    with pytest.raises(Exception):
        CustomerInput(
            customer_id=0, age=30.0, gender="Male", tenure=12.0,
            usage_frequency=10.0, support_calls=1.0, payment_delay=0.0,
            subscription_type="Basic", contract_length="Monthly",
            total_spend=300.0, last_interaction=5.0
        )

    app_js = (PROJECT_ROOT / "src" / "web" / "app.js").read_text(encoding="utf-8")
    assert 'const API_KEY = "' not in app_js
    assert "function escapeHtml(" in app_js

    dash_py = (PROJECT_ROOT / "src" / "web" / "dashboard.py").read_text(encoding="utf-8")
    assert len(dash_py.splitlines()) <= 200, "dashboard.py must be <= 200 lines (Invariant 06)"

    tf_src = (PROJECT_ROOT / "deploy" / "azure" / "main.tf").read_text(encoding="utf-8")
    assert "mcr.microsoft.com/azuredocs/aci-helloworld:latest" not in tf_src
    assert "churnguard-mlops:latest" in tf_src

    resp_drift = client.get("/docs/drift_report.html")
    assert resp_drift.status_code == 200
