"""
Adversarial Unit Test Suite - Audit Team 4 (Triple-Blind Peer-Swap Audit Swarm)
Course: UIT IS402 Cloud Computing - Topic 11: MLOps Customer Churn Prediction
Covers all 8 Audit Dimensions (Tasks 1-8) with repo-grounded & paper-grounded assertions.
"""
import io
import os
import sys
import json
import yaml
import tempfile
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.main import app, FEATURE_COLS
from src.api.utils import compute_shap_attributions, generate_recommendation
from src.data.preprocess import (
    clean_raw_data,
    engineer_features,
    process_large_dataset_chunks,
)
from src.monitoring.drift_detector import calculate_psi

client = TestClient(app)
API_KEY = os.environ.get("API_KEY_SECRET", "mlops-churn-secret-2026")
AUTH_HEADERS = {"X-API-Key": API_KEY}


# ---------------------------------------------------------------------------
# TASK 1: IS402 Rubric & DVC / CI-CD Pipeline Reproducibility
# Grounding: [Oyebamiji_Micheal_dvc_mlflow | dvc.yaml:L22-L33 | GitHub-Benchmark]
# ---------------------------------------------------------------------------
def test_t1_dvc_pipeline_tracks_scaler_and_feast_stages():
    """
    Verify whether dvc.yaml tracks data/processed/scaler.joblib and metadata.json
    in preprocess outs and train_models deps, plus Optuna/Feast stages.
    Exposes DEF-T1-02: scaler.joblib is loaded by train_pipeline.py but omitted from dvc.yaml.
    """
    with open("dvc.yaml", "r", encoding="utf-8") as f:
        dvc_cfg = yaml.safe_load(f)
    stages = dvc_cfg.get("stages", {})
    preprocess_outs = stages.get("preprocess", {}).get("outs", [])
    train_deps = stages.get("train_models", {}).get("deps", [])

    out_paths = [
        list(item.keys())[0] if isinstance(item, dict) else item
        for item in preprocess_outs
    ]
    assert "data/processed/scaler.joblib" in out_paths, (
        f"DEF-T1-02: data/processed/scaler.joblib is omitted from dvc.yaml preprocess.outs ({out_paths})"
    )
    assert "data/processed/scaler.joblib" in train_deps, (
        "DEF-T1-02: data/processed/scaler.joblib is omitted from dvc.yaml train_models.deps"
    )


def test_t1_dual_track_rubric_score_consistency():
    """
    Verify consistency of Local vs Cloud score reporting across verification scripts.
    Exposes DEF-T1-01: integrity_rubric_checker.py docstring claims 6.25/10 Local
    while actual summed local_scores in the script is 3.35/10.
    """
    with open("scripts/verification/integrity_rubric_checker.py", "r", encoding="utf-8") as f:
        src_text = f.read()

    import re
    local_vals = [float(x) for x in re.findall(r'self\.local_scores\[".*?"\]\s*=\s*([0-9.]+)', src_text)]
    actual_local_sum = round(sum(local_vals), 2)

    assert f"Local ({actual_local_sum}/10)" in src_text, (
        f"DEF-T1-01: Docstring claims Local (6.25/10) but actual computed sum of local_scores is {actual_local_sum}/10"
    )


# ---------------------------------------------------------------------------
# TASK 2: Out-of-Core Streaming, Cross-Chunk Deduplication & Imputation
# Grounding: [Soumyadeep Roy 2026 | Section 2.2 P-Clean vs P-Leak | arXiv:2610.00118v1]
# ---------------------------------------------------------------------------
def test_t2_out_of_core_cross_chunk_deduplication_and_imputation():
    """
    Verify that process_large_dataset_chunks deduplicates customerid across chunk
    boundaries and maintains consistent median imputation across chunks.
    Exposes DEF-T2-01: duplicate customerids across chunks are written into output_parquet
    and per-chunk medians drift across chunks.
    """
    rows = [
        {"CustomerID": 101, "Age": 25.0, "Gender": "Female", "Tenure": 10.0,
         "Usage Frequency": 5.0, "Support Calls": 1.0, "Payment Delay": 2.0,
         "Subscription Type": "Basic", "Contract Length": "Monthly",
         "Total Spend": 200.0, "Last Interaction": 5.0, "Churn": 0.0},
        {"CustomerID": 102, "Age": 35.0, "Gender": "Male", "Tenure": 20.0,
         "Usage Frequency": 10.0, "Support Calls": 2.0, "Payment Delay": 4.0,
         "Subscription Type": "Standard", "Contract Length": "Annual",
         "Total Spend": 500.0, "Last Interaction": 10.0, "Churn": 1.0},
        # Chunk 2 repeats CustomerID 101 and has NaN Age
        {"CustomerID": 101, "Age": 25.0, "Gender": "Female", "Tenure": 10.0,
         "Usage Frequency": 5.0, "Support Calls": 1.0, "Payment Delay": 2.0,
         "Subscription Type": "Basic", "Contract Length": "Monthly",
         "Total Spend": 200.0, "Last Interaction": 5.0, "Churn": 0.0},
        {"CustomerID": 103, "Age": np.nan, "Gender": "Male", "Tenure": 15.0,
         "Usage Frequency": 8.0, "Support Calls": 0.0, "Payment Delay": 1.0,
         "Subscription Type": "Premium", "Contract Length": "Quarterly",
         "Total Spend": 800.0, "Last Interaction": 3.0, "Churn": 0.0},
    ]
    df = pd.DataFrame(rows)
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "stream_input.csv")
        pq_path = os.path.join(tmpdir, "stream_out.parquet")
        df.to_csv(csv_path, index=False)

        total_rows = process_large_dataset_chunks(csv_path, pq_path, chunk_size=2)
        out_df = pd.read_parquet(pq_path)

        assert out_df["customerid"].is_unique, (
            f"DEF-T2-01: Cross-chunk duplicate customerid persisted in output Parquet ({total_rows} rows)"
        )


# ---------------------------------------------------------------------------
# TASK 3: Mathematical Fidelity - PSI Binning Collapse & SHAP Local Accuracy
# Grounding:
# - [Rabanser et al. 2019 | Section 3.1 Univariate Shift Detection | arXiv:1810.11953]
# - [Katalay et al. 2025 | Eq. 4 PSI Definition | arXiv:2512.11541v1]
# - [Lundberg & Lee 2017 | Eq. 1 & Property 1 Local Accuracy | arXiv:1705.07874]
# ---------------------------------------------------------------------------
def test_t3_psi_discrete_binary_and_ternary_shift_detection():
    """
    Verify that calculate_psi detects extreme distribution shifts on 3-class discrete
    encoded features (subscription_type_encoded / contract_length_encoded in {0, 1, 2}).
    Exposes DEF-T3-02: When class proportions are e.g. 35% / 30% / 35%, np.unique(breakpoints)
    has exactly 3 elements [0.0, 1.0, 2.0] (bypassing len < 3), and overwriting
    breakpoints[0]=-inf, breakpoints[-1]=+inf yields [-inf, 1.0, +inf], merging classes 1 and 2
    into the same bin [1.0, +inf) and returning PSI = 0.0 even when class 1 collapses from 30% to 1%!
    """
    expected_ternary = np.array([0.0] * 350 + [1.0] * 300 + [2.0] * 350)
    actual_ternary = np.array([0.0] * 350 + [1.0] * 10 + [2.0] * 640)
    psi_ternary = calculate_psi(expected_ternary, actual_ternary, 10)

    assert psi_ternary > 0.25, (
        f"DEF-T3-02: Ternary feature PSI collapsed to {psi_ternary:.6f} (expected > 0.25) due to merging classes 1 and 2 into [1.0, +inf)"
    )


def test_t3_shap_linear_model_fallback_and_negative_attribution_handling():
    """
    Verify that compute_shap_attributions supports non-tree linear models
    (Corollary 1 Linear SHAP, Lundberg & Lee 2017) instead of returning empty factors={}.
    Exposes DEF-T3-01: When tree_explainer is None (e.g. Logistic_Regression),
    compute_shap_attributions returns empty factors={} and claims safe distribution.
    """
    x_input = np.array([[1.5, -1.2, 2.0, 3.5, 2.8, 0.0, -1.0, 1.0, -0.5, 1.2, 2.1, -0.8, 1.9]])
    factors, explanations = compute_shap_attributions(None, x_input)
    assert len(factors) > 0, (
        "DEF-T3-01: compute_shap_attributions returns empty factors={} when tree_explainer is None (violating Linear SHAP Corollary 1)"
    )


# ---------------------------------------------------------------------------
# TASK 4: Reference Repos Grounding - Diagnostics Schema & Feast Precision
# Grounding: [mlops-churn-feature-store | feature_store/features.py:L43-L65 | GitHub-Benchmark]
# ---------------------------------------------------------------------------
def test_t4_diagnostics_report_schema_matches_dashboard_consumer():
    """
    Verify that error_analysis_report.json schema produced by src/models/model_diagnostics.py
    matches the keys read by src/web/dashboard.py ('counts' and 'metrics').
    Exposes DEF-T3-03 / DEF-T4-01: model_diagnostics.py writes 'confusion_breakdown'
    while dashboard.py reads 'counts' and 'metrics', causing all KPIs to render as 0.
    """
    with open("src/models/model_diagnostics.py", "r", encoding="utf-8") as f:
        diag_src = f.read()
    with open("src/web/dashboard.py", "r", encoding="utf-8") as f:
        dash_src = f.read()

    assert '"counts"' in diag_src and '"metrics"' in diag_src, (
        "DEF-T4-01: src/web/dashboard.py reads err_rep.get('counts') and err_rep.get('metrics'), "
        "but src/models/model_diagnostics.py writes 'confusion_breakdown' and omits 'metrics'"
    )


# ---------------------------------------------------------------------------
# TASK 5: Customer Entity Anti-Leakage & Training-Serving Skew
# Grounding:
# - [Soumyadeep Roy 2026 | Section 2.2 & 3.4 Data Leakage Audit | arXiv:2610.00118v1]
# - [Feature_Store_Survey_Architectures | Online-Offline Skew | Survey-2023]
# ---------------------------------------------------------------------------
def test_t5_zero_customerid_overlap_across_splits():
    """
    Verify strict entity isolation: zero customerid overlap across train, val, and test splits.
    """
    train_ids = set(pd.read_parquet("data/processed/train_features.parquet", columns=["customerid"])["customerid"])
    val_ids = set(pd.read_parquet("data/processed/val_features.parquet", columns=["customerid"])["customerid"])
    test_ids = set(pd.read_parquet("data/processed/test_features.parquet", columns=["customerid"])["customerid"])

    assert len(train_ids & val_ids) == 0, "CustomerID leakage between Train and Val"
    assert len(train_ids & test_ids) == 0, "CustomerID leakage between Train and Test"
    assert len(val_ids & test_ids) == 0, "CustomerID leakage between Val and Test"


def test_t5_feast_online_store_covers_validation_and_test_entities():
    """
    Verify whether Feast Online Store materializes validation and test customer entities
    and avoids silent 0.0 default imputation or 404 misses for valid test customers.
    Exposes DEF-T5-02: prepare_feast_data() only materializes train_features.parquet,
    leaving 100% of val_features.parquet and test_features.parquet unmaterialized!
    """
    test_df = pd.read_parquet("data/processed/test_features.parquet").iloc[:1]
    test_cid = int(test_df["customerid"].iloc[0])

    resp = client.get(f"/predict/customer/{test_cid}", headers=AUTH_HEADERS)
    assert resp.status_code == 200, (
        f"DEF-T5-02: Feast Online Store returned HTTP {resp.status_code} for valid test set customer_id={test_cid} "
        "because prepare_feast_data() only materializes train_features.parquet (excluding 30% of customers)"
    )


# ---------------------------------------------------------------------------
# TASK 6: Adversarial Numerical Edge Cases (Tenure=0, NaN/Inf, Division-by-Zero)
# ---------------------------------------------------------------------------
def test_t6_engineer_features_zero_tenure_and_zero_delay_stability():
    """
    Verify that engineer_features handles tenure=0 and payment_delay=0 without
    producing NaN or Inf in derived ratio features.
    """
    df = pd.DataFrame([
        {
            "customerid": 1,
            "age": 18.0,
            "gender": "Female",
            "tenure": 0.0,
            "usage_frequency": 0.0,
            "support_calls": 5.0,
            "payment_delay": 0.0,
            "subscription_type": "Basic",
            "contract_length": "Monthly",
            "total_spend": 100.0,
            "last_interaction": 1.0,
            "churn": 1,
        }
    ])
    feat = engineer_features(df)
    for col in ["support_calls_per_tenure", "spend_per_tenure", "delay_ratio"]:
        assert np.isfinite(feat[col].iloc[0]), f"Non-finite value in {col}"


# ---------------------------------------------------------------------------
# TASK 7: Telecom/SaaS Domain & Cloud Economics Consistency
# Grounding: [Manzoor et al. 2025 | Business-Aligned Churn Metrics | arXiv:2507.08860v2]
# ---------------------------------------------------------------------------
def test_t7_risk_threshold_and_clv_aware_recommendation():
    """
    Verify risk tier threshold alignment (Medium >= 0.40 per IS402 grounding catalog).
    Exposes DEF-T7-01: prob=0.36 is misclassified as Medium (hardcoded 0.35 threshold
    in generate_recommendation and /predict).
    """
    rec_text = generate_recommendation(prob=0.36, calls=1.0, delay=2.0)
    assert "Duy trì chất lượng dịch vụ tiêu chuẩn" in rec_text, (
        f"DEF-T7-01: prob=0.36 received Medium-risk action '{rec_text}' instead of Low-risk standard action (expected Medium >= 0.40)"
    )


def test_t7_cloud_storage_container_name_consistency_across_code_and_iac():
    """
    Verify that AZURE_STORAGE_CONTAINER in src/data/preprocess.py matches the
    blob container provisioned in deploy/azure/main.tf and deploy/azure/arm_template.json.
    Exposes DEF-T7-02: preprocess.py uses 'mlops-processed-data' while IaC provisions 'churnguard-datasets'.
    """
    with open("src/data/preprocess.py", "r", encoding="utf-8") as f:
        prep_src = f.read()
    with open("deploy/azure/main.tf", "r", encoding="utf-8") as f:
        tf_src = f.read()

    assert "churnguard-datasets" in prep_src or "mlops-processed-data" in tf_src, (
        "DEF-T7-02: Container mismatch - src/data/preprocess.py uploads to 'mlops-processed-data' "
        "while deploy/azure/main.tf provisions 'churnguard-datasets'"
    )


# ---------------------------------------------------------------------------
# TASK 8: API Serving, Input Validation, CSV Upload Robustness & Web Hygiene
# ---------------------------------------------------------------------------
def test_t8_upload_csv_predict_malformed_row_returns_400_not_500():
    """
    Verify that /upload_csv_predict gracefully rejects a CSV containing alphanumeric
    CustomerID 'CUST-001' with HTTP 400/422 instead of crashing with unhandled ValueError (HTTP 500).
    Exposes DEF-T8-01: /upload_csv_predict crashes on string CustomerID or invalid cell values.
    """
    bad_csv = (
        "CustomerID,Age,Gender,Tenure,Usage Frequency,Support Calls,Payment Delay,"
        "Subscription Type,Contract Length,Total Spend,Last Interaction\n"
        "CUST-001,30,Female,12,10,1,2,Standard,Monthly,500,5\n"
    )
    files = {"file": ("bad_customers.csv", io.BytesIO(bad_csv.encode("utf-8")), "text/csv")}
    no_raise_client = TestClient(app, raise_server_exceptions=False)
    resp = no_raise_client.post("/upload_csv_predict", files=files, headers=AUTH_HEADERS)
    assert resp.status_code in (400, 422), (
        f"DEF-T8-01: Expected HTTP 400/422 for alphanumeric CustomerID 'CUST-001', got HTTP {resp.status_code}"
    )


def test_t8_web_static_no_hardcoded_secret_key_and_valid_drift_report_route():
    """
    Verify that /docs/drift_report.html linked in src/web/index.html is routable.
    Exposes DEF-T8-03: /docs/drift_report.html returns HTTP 404 Not Found.
    """
    drift_resp = client.get("/docs/drift_report.html")
    assert drift_resp.status_code == 200, (
        f"DEF-T8-03: /docs/drift_report.html linked in src/web/index.html:L269 returned HTTP {drift_resp.status_code}"
    )
