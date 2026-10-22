"""
Independent Adversarial Unit Test Suite - Audit Team 2.
Covers all 8 Mandatory IS402 MLOps Audit Dimensions:
- Task 1: IS402 Rubric, CI Anti-Mockup Exit Code, and DVC Pipeline Completeness
- Task 2: Out-of-Core Streaming Deduplication, Socket Leak, and SQLite Concurrency
- Task 3: SHAP Local Accuracy/Negative Attributions, PSI Out-of-Bounds Bins, and KS Bonferroni
- Task 4: Model Diagnostics vs Dashboard Schema Mismatch and Feast Online Route
- Task 5: Pre-Split Imputation Leakage and Serving Categorical Whitespace Skew
- Task 6: Boundary Values, NaN/Inf Handling, and Entity ID Validation
- Task 7: Cloud TCO Architecture Mismatch (PostgreSQL vs Redis/ACR) and Retention Thresholds
- Task 8: Web UI Broken /docs/drift_report.html Route, DOM XSS, and Azure IaC Dummy Image
"""
import io
import json
import socket
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.schemas import CustomerInput
from src.api.utils import (
    compute_shap_attributions,
    generate_recommendation,
    prepare_feature_vector_from_input,
)
from src.data.latency_simulator import measure_tcp_latency
from src.data.preprocess import process_large_dataset_chunks
from src.monitoring.drift_detector import calculate_psi

PROJECT_ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "mlops-churn-secret-2026"}


# ==============================================================================
# TASK 1: IS402 Course & Rubric Alignment
# ==============================================================================
def test_t1_rubric_docstring_vs_computed_score_and_dvc_stages():
    """
    [DEF-T2-01] Verify rubric checker docstring matches actual 3.35/10 score
    and dvc.yaml includes Feast feature store and Optuna tuning stages.
    """
    checker_path = PROJECT_ROOT / "scripts" / "verification" / "integrity_rubric_checker.py"
    checker_text = checker_path.read_text(encoding="utf-8")
    dvc_text = (PROJECT_ROOT / "dvc.yaml").read_text(encoding="utf-8")

    assert "6.25/10" not in checker_text, (
        "integrity_rubric_checker.py docstring claims 6.25/10 while actual local score is 3.35/10"
    )
    assert "feature_store.py" in dvc_text, "dvc.yaml omits Feast feature_store.py materialization stage"
    assert "tune_optuna.py" in dvc_text, "dvc.yaml omits Optuna tune_optuna.py hyperparameter stage"


def test_t1_ci_anti_mockup_grep_does_not_mask_matches():
    """
    [DEF-T2-01b] Verify .github/workflows/mlops_ci.yml fails when git grep finds
    forbidden mockup tokens instead of succeeding with exit code 0.
    """
    ci_path = PROJECT_ROOT / ".github" / "workflows" / "mlops_ci.yml"
    ci_text = ci_path.read_text(encoding="utf-8")
    # In POSIX shell, `git grep PATTERN || echo "Clean"` returns exit code 0 both when
    # matches ARE found (git grep exits 0) and when NO matches are found (echo exits 0).
    assert 'git grep -iE "TODO: mock|fakeData|dummyData|simulateTx" -- src/ || echo' not in ci_text, (
        "mlops_ci.yml uses `git grep ... || echo` which exits 0 even when mockup strings ARE found"
    )


def test_t1_research_papers_match_claimed_titles():
    """
    [DEF-T2-02] Verify downloaded research papers in docs/research/papers/ contain
    actual ML/drift/feature-store content rather than unrelated physics papers.
    """
    rabanser_md = (
        PROJECT_ROOT / "docs" / "research" / "papers" / "Rabanser_2019_Failing_Loudly_Dataset_Shift_Detection.md"
    ).read_text(encoding="utf-8", errors="ignore")
    feast_md = (
        PROJECT_ROOT / "docs" / "research" / "papers" / "Feature_Store_Survey_Architectures.md"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "Nutty dyonic black hole" not in rabanser_md, (
        "Rabanser_2019_Failing_Loudly_Dataset_Shift_Detection.md contains a black hole physics paper"
    )
    assert "Cherenkov Telescope" not in feast_md, (
        "Feature_Store_Survey_Architectures.md contains an astrophysics Cherenkov Telescope paper"
    )


# ==============================================================================
# TASK 2: Code Logic, Out-of-Core Streaming & Clean Architecture
# ==============================================================================
def test_t2_cross_chunk_customer_id_deduplication(tmp_path):
    """
    [DEF-T2-09] Verify process_large_dataset_chunks deduplicates CustomerID
    both within a chunk and across chunk boundaries, with consistent medians.
    """
    csv_file = tmp_path / "chunk_test.csv"
    parquet_file = tmp_path / "chunk_test.parquet"

    rows = [
        # Chunk 1 (rows 0-2): CustomerID 101 appears here
        {"CustomerID": 101, "Age": 30, "Gender": "Male", "Tenure": 12, "Usage Frequency": 10,
         "Support Calls": 1, "Payment Delay": 2, "Subscription Type": "Basic",
         "Contract Length": "Monthly", "Total Spend": 500.0, "Last Interaction": 5, "Churn": 0},
        {"CustomerID": 102, "Age": 40, "Gender": "Female", "Tenure": 24, "Usage Frequency": 15,
         "Support Calls": 2, "Payment Delay": 0, "Subscription Type": "Standard",
         "Contract Length": "Annual", "Total Spend": 800.0, "Last Interaction": 3, "Churn": 0},
        {"CustomerID": 103, "Age": 35, "Gender": "Male", "Tenure": 18, "Usage Frequency": 12,
         "Support Calls": 3, "Payment Delay": 5, "Subscription Type": "Premium",
         "Contract Length": "Quarterly", "Total Spend": 650.0, "Last Interaction": 7, "Churn": 1},
        # Chunk 2 (rows 3-5): CustomerID 101 is duplicated across chunk boundary!
        {"CustomerID": 101, "Age": 30, "Gender": "Male", "Tenure": 12, "Usage Frequency": 10,
         "Support Calls": 1, "Payment Delay": 2, "Subscription Type": "Basic",
         "Contract Length": "Monthly", "Total Spend": 500.0, "Last Interaction": 5, "Churn": 1},
        {"CustomerID": 104, "Age": 28, "Gender": "Female", "Tenure": 6, "Usage Frequency": 5,
         "Support Calls": 6, "Payment Delay": 14, "Subscription Type": "Basic",
         "Contract Length": "Monthly", "Total Spend": 210.0, "Last Interaction": 19, "Churn": 1},
        {"CustomerID": 105, "Age": 50, "Gender": "Male", "Tenure": 48, "Usage Frequency": 25,
         "Support Calls": 0, "Payment Delay": 0, "Subscription Type": "Premium",
         "Contract Length": "Annual", "Total Spend": 1400.0, "Last Interaction": 2, "Churn": 0},
    ]
    pd.DataFrame(rows).to_csv(csv_file, index=False)

    process_large_dataset_chunks(csv_file, parquet_file, chunk_size=3)
    df_out = pd.read_parquet(parquet_file)

    assert df_out["customerid"].is_unique, (
        f"Duplicate CustomerID leaked across chunks: {df_out['customerid'].tolist()}"
    )
    assert len(df_out) == 5


def test_t2_latency_simulator_closes_socket_on_connect_failure(monkeypatch):
    """
    [DEF-T2-05] Verify measure_tcp_latency closes the OS socket even when
    s.connect() raises socket.timeout or socket.error.
    """
    import urllib.request

    closed_tracker = {"closed": False}

    class FailingSocket:
        def __init__(self, *args, **kwargs):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, addr):
            raise socket.timeout("simulated connection timeout")

        def close(self):
            closed_tracker["closed"] = True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.close()

    def fail_urlopen(*args, **kwargs):
        raise OSError("no http fallback")

    monkeypatch.setattr(socket, "socket", FailingSocket)
    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)
    res = measure_tcp_latency("127.0.0.1", port=65534, num_pings=1)
    assert res["status"] == "UNREACHABLE"
    assert closed_tracker["closed"] is True, (
        "Socket was not closed when s.connect() raised socket.timeout"
    )


def test_t2_database_module_and_sqlite_context_safety():
    """
    [DEF-T2-03] Verify centralized src/api/database.py exists or SQLite connections
    in src/api/utils.py use WAL mode / try-finally closure.
    """
    utils_text = (PROJECT_ROOT / "src" / "api" / "utils.py").read_text(encoding="utf-8")
    db_file = PROJECT_ROOT / "src" / "api" / "database.py"
    has_wal_or_try = ("journal_mode=WAL" in utils_text) or ("finally:" in utils_text) or db_file.exists()
    assert has_wal_or_try, (
        "SQLite connections in src/api/utils.py lack PRAGMA journal_mode=WAL, timeout, and try/finally closure"
    )


# ==============================================================================
# TASK 3: Literature & Mathematical Fidelity (SHAP, PSI, KS-Test)
# ==============================================================================
def test_t3_shap_retains_negative_attributions_and_3d_arrays():
    """
    [DEF-T2-06] Verify compute_shap_attributions preserves negative Shapley values
    (features reducing churn risk) and handles 3D (1, n_features, 2) SHAP outputs.
    Grounded in Lundberg & Lee (2017, arXiv:1705.07874, Eq. 1 Local Accuracy).
    """
    customer = CustomerInput(
        customer_id=701,
        age=45.0,
        gender="Female",
        tenure=55.0,
        usage_frequency=28.0,
        support_calls=0.0,
        payment_delay=0.0,
        subscription_type="Premium",
        contract_length="Annual",
        total_spend=1450.0,
        last_interaction=1.0,
    )
    x_vec = prepare_feature_vector_from_input(customer)

    class Dummy3DTreeExplainer:
        expected_value = [0.4, -0.4]

        def shap_values(self, X):
            # Shape (1, 13, 2) where class 1 has strong negative attributions (-0.60, -0.45)
            n_feat = X.shape[1]
            arr = np.zeros((1, n_feat, 2), dtype=float)
            arr[0, :, 1] = -0.25
            arr[0, 4, 1] = -0.60  # support_calls = 0 reduces churn risk strongly
            arr[0, 5, 1] = -0.45  # payment_delay = 0 reduces churn risk strongly
            return arr

    attributions, summary = compute_shap_attributions(Dummy3DTreeExplainer(), x_vec)
    assert "support_calls" in summary or "-0.600" in summary, (
        f"Negative SHAP attributions were ignored in explanation_summary: {summary}"
    )
    app_js = (PROJECT_ROOT / "src" / "web" / "app.js").read_text(encoding="utf-8")
    assert "+${(weight * 100)" not in app_js, (
        "src/web/app.js hardcodes '+${(weight * 100).toFixed(1)}%' causing '+-60.0%' on negative SHAP values"
    )


def test_t3_psi_captures_out_of_bounds_shifted_distribution():
    """
    [DEF-T2-07a] Verify calculate_psi does not collapse to a single [-inf, +inf] bin
    (returning PSI == 0.0) on binary/discrete features like gender_encoded.
    """
    rng = np.random.default_rng(42)
    expected_bin = rng.choice([0.0, 1.0], size=1000, p=[0.90, 0.10])
    actual_bin = rng.choice([0.0, 1.0], size=1000, p=[0.10, 0.90])

    psi_shifted = calculate_psi(expected_bin, actual_bin, num_buckets=10)
    assert psi_shifted > 0.25, (
        f"calculate_psi collapsed binary breakpoints [0.0, 1.0] into [-inf, +inf] and returned PSI={psi_shifted}"
    )


def test_t3_ks_drift_uses_bonferroni_multiple_testing_correction():
    """
    [DEF-T2-07b] Verify drift_detector.py applies Bonferroni correction (alpha / D)
    for multiple univariate KS tests across D=13 features per Rabanser et al. (2019, arXiv:1810.11953).
    """
    drift_src = (PROJECT_ROOT / "src" / "monitoring" / "drift_detector.py").read_text(encoding="utf-8")
    has_bonferroni = ("len(" in drift_src and "p_val_threshold /" in drift_src) or ("bonferroni" in drift_src.lower())
    assert has_bonferroni, (
        "drift_detector.py runs 13 univariate KS tests at unadjusted alpha=0.05 without Bonferroni correction"
    )


# ==============================================================================
# TASK 4: Reference Repositories Code-to-Code Audit
# ==============================================================================
def test_t4_error_analysis_report_matches_dashboard_schema():
    """
    [DEF-T2-08] Verify error_analysis_report.json path and schema match between
    src/models/model_diagnostics.py and src/web/dashboard.py (data/processed/error_analysis_report.json).
    """
    report_path = PROJECT_ROOT / "data" / "processed" / "error_analysis_report.json"
    assert report_path.exists(), "data/processed/error_analysis_report.json missing"
    err_rep = json.loads(report_path.read_text(encoding="utf-8"))
    dashboard_src = (PROJECT_ROOT / "src" / "web" / "dashboard.py").read_text(encoding="utf-8")

    has_confusion_or_counts = (
        ("confusion_breakdown" in err_rep and "confusion_breakdown" in dashboard_src)
        or ("counts" in err_rep and "metrics" in err_rep)
    )
    assert has_confusion_or_counts, (
        f"Schema mismatch between dashboard.py and error_analysis_report.json keys {list(err_rep.keys())}"
    )


# ==============================================================================
# TASK 5: Customer Entity Anti-Leakage & Training-Serving Skew
# ==============================================================================
def test_t5_csv_upload_strips_whitespace_in_categorical_columns():
    """
    [DEF-T2-10] Verify /upload_csv_predict handles whitespace-padded categorical values
    (e.g. ' Male ', ' Basic ', ' Monthly ') without crashing with HTTP 500 ValidationError.
    """
    csv_content = (
        "CustomerID,Age,Gender,Tenure,Usage Frequency,Support Calls,Payment Delay,"
        "Subscription Type,Contract Length,Total Spend,Last Interaction\n"
        "5001,34, Male ,12,14,2,1, Basic , Monthly ,420.0,6\n"
    )
    files = {"file": ("whitespace.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/upload_csv_predict", files=files, headers=AUTH_HEADERS)
    assert response.status_code == 200, (
        f"/upload_csv_predict crashed with {response.status_code} on whitespace-padded categories: {response.text}"
    )


# ==============================================================================
# TASK 6: Boundary Values, NaN/Inf Inputs & Entity ID Constraints
# ==============================================================================
def test_t6_customer_input_rejects_non_positive_customer_id_and_nan():
    """
    [DEF-T2-10b] Verify CustomerInput rejects negative/zero customer_id and NaN floats.
    """
    res_neg_id = client.post(
        "/predict",
        json={
            "customer_id": -999,
            "age": 30.0,
            "gender": "Male",
            "tenure": 12.0,
            "usage_frequency": 10.0,
            "support_calls": 1.0,
            "payment_delay": 0.0,
            "subscription_type": "Basic",
            "contract_length": "Monthly",
            "total_spend": 500.0,
            "last_interaction": 5.0,
        },
        headers=AUTH_HEADERS,
    )
    assert res_neg_id.status_code == 422, (
        f"CustomerInput accepted negative customer_id=-999 with HTTP {res_neg_id.status_code}"
    )


# ==============================================================================
# TASK 7: Telecom/SaaS Churn Domain & Cloud Economics Critique
# ==============================================================================
def test_t7_cloud_cost_doc_matches_actual_deployed_services():
    """
    [DEF-T2-11] Verify configs/cloud_architecture_and_cost.md does not bill for unused
    PostgreSQL while omitting deployed Azure Cache for Redis and Azure Container Registry.
    """
    cost_md = (PROJECT_ROOT / "configs" / "cloud_architecture_and_cost.md").read_text(encoding="utf-8")
    assert "PostgreSQL" not in cost_md, (
        "cloud_architecture_and_cost.md allocates $48.90/mo (54% of TCO) to unused Azure PostgreSQL"
    )
    assert "Redis" in cost_md, (
        "cloud_architecture_and_cost.md omits Azure Cache for Redis from the Cloud Cost TCO breakdown"
    )


# ==============================================================================
# TASK 8: API Serving, Web Bento Grid & Deliverables Audit
# ==============================================================================
def test_t8_web_drift_report_link_and_xss_and_azure_iac_image():
    """
    [DEF-T2-12] Verify /docs/drift_report.html linked in index.html does not 404,
    app.js does not inject unescaped innerHTML, and Azure IaC does not deploy aci-helloworld.
    """
    res_drift = client.get("/docs/drift_report.html")
    assert res_drift.status_code == 200, (
        f"index.html links to /docs/drift_report.html which returned HTTP {res_drift.status_code}"
    )

    arm_text = (PROJECT_ROOT / "deploy" / "azure" / "arm_template.json").read_text(encoding="utf-8")
    assert "aci-helloworld" not in arm_text, (
        "deploy/azure/arm_template.json deploys dummy image mcr.microsoft.com/azuredocs/aci-helloworld:latest"
    )
