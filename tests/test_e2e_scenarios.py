"""
End-to-End Multi-Tier Scenario Testing Suite for ChurnGuard MLOps Platform.
Covers 4 Quality Tiers:
- Tier 1: Functional Feature Coverage (redirects, Feast features, retrain, CSV errors)
- Tier 2: Boundary & Corner Cases (schema limits, negative values, zero-division, empty batches)
- Tier 3: Cross-Feature Combinations & Consistency (A/B hash routing, batch vs single parity)
- Tier 4: Real-World Operational Scenarios & SLAs (Feast latency SLA, schema contracts, throughput)

Tuân thủ Invariant 01 (Clean Architecture) và Invariant 02 (< 400 dòng mã).
"""
import io
import time
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.ab_testing import route_customer_to_model

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "mlops-churn-secret-2026"}

SAMPLE_BASE_CUSTOMER = {
    "customer_id": 1001,
    "age": 35.0,
    "gender": "Female",
    "tenure": 24.0,
    "usage_frequency": 15.0,
    "support_calls": 2.0,
    "payment_delay": 3.0,
    "subscription_type": "Standard",
    "contract_length": "Annual",
    "total_spend": 650.0,
    "last_interaction": 10.0
}


# ============================================================================
# TIER 1: FUNCTIONAL FEATURE COVERAGE
# ============================================================================

def test_tier1_root_redirect_to_docs():
    """Verify root path redirects to OpenAPI interactive documentation."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_tier1_feast_online_feature_lookup():
    """Verify Feast online feature retrieval endpoint by customer ID."""
    response = client.get("/features/156624")
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == 156624
    assert "features" in data
    features = data["features"]
    assert "age" in features or "customer_churn_features:age" in features


def test_tier1_trigger_retrain_evaluation():
    """Verify trigger_retrain endpoint evaluates drift without forced override."""
    response = client.post("/api/v1/trigger_retrain?force=false", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["SKIPPED", "TRIGGERED", "ALREADY_RUNNING"]
    assert "drift_share" in data


def test_tier1_csv_upload_missing_column():
    """Verify CSV batch upload fails when a mandatory column is missing."""
    csv_missing_spend = (
        "CustomerID,Age,Gender,Tenure,Usage Frequency,Support Calls,Payment Delay,Subscription Type,Contract Length,Last Interaction\n"
        "9001,35,Male,12,10,2,1,Standard,Monthly,5\n"
    )
    files = {"file": ("missing_spend.csv", io.BytesIO(csv_missing_spend.encode("utf-8")), "text/csv")}
    response = client.post("/upload_csv_predict", files=files, headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert "Tệp CSV thiếu cột bắt buộc" in response.json()["detail"]


def test_tier1_csv_upload_invalid_file_extension():
    """Verify CSV endpoint rejects non-CSV file extensions."""
    txt_content = "CustomerID,Age\n1,20\n"
    files = {"file": ("data.txt", io.BytesIO(txt_content.encode("utf-8")), "text/plain")}
    response = client.post("/upload_csv_predict", files=files, headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert "định dạng CSV" in response.json()["detail"]


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ============================================================================

def test_tier2_missing_required_fields():
    """Verify Pydantic validation rejects payload with missing mandatory fields."""
    incomplete_payload = {
        "customer_id": 1001,
        "age": 30.0,
        "gender": "Male"
        # Missing tenure, total_spend, contract_length, etc.
    }
    response = client.post("/predict", json=incomplete_payload, headers=AUTH_HEADERS)
    assert response.status_code == 422


@pytest.mark.parametrize("field,bad_value", [
    ("age", 17.0),          # ge=18
    ("age", 101.0),         # le=100
    ("tenure", -1.0),       # ge=0
    ("tenure", 121.0),      # le=120
    ("usage_frequency", -0.5), # ge=0
    ("usage_frequency", 51.0), # le=50
    ("support_calls", -1.0),   # ge=0
    ("support_calls", 31.0),   # le=30
    ("payment_delay", -2.0),   # ge=0
    ("payment_delay", 91.0),   # le=90
    ("total_spend", -10.0),    # ge=0
    ("total_spend", 100001.0), # le=100000
    ("last_interaction", -1.0),# ge=0
    ("last_interaction", 61.0) # le=60
])
def test_tier2_out_of_bounds_numerical_validation(field, bad_value):
    """Verify numerical boundaries strictly reject out-of-range inputs with HTTP 422."""
    payload = SAMPLE_BASE_CUSTOMER.copy()
    payload[field] = bad_value
    response = client.post("/predict", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 422


def test_tier2_exact_boundary_values():
    """Verify endpoint accepts exact minimum and maximum schema boundary values."""
    min_boundary_payload = {
        "customer_id": 1,
        "age": 18.0,
        "gender": "Female",
        "tenure": 0.0,
        "usage_frequency": 0.0,
        "support_calls": 0.0,
        "payment_delay": 0.0,
        "subscription_type": "Basic",
        "contract_length": "Monthly",
        "total_spend": 0.0,
        "last_interaction": 0.0
    }
    res_min = client.post("/predict", json=min_boundary_payload, headers=AUTH_HEADERS)
    assert res_min.status_code == 200
    assert res_min.json()["churn_prediction"] in [0, 1]

    max_boundary_payload = {
        "customer_id": 99999999,
        "age": 100.0,
        "gender": "Male",
        "tenure": 120.0,
        "usage_frequency": 50.0,
        "support_calls": 30.0,
        "payment_delay": 90.0,
        "subscription_type": "Premium",
        "contract_length": "Annual",
        "total_spend": 100000.0,
        "last_interaction": 60.0
    }
    res_max = client.post("/predict", json=max_boundary_payload, headers=AUTH_HEADERS)
    assert res_max.status_code == 200
    assert res_max.json()["churn_prediction"] in [0, 1]


def test_tier2_zero_division_safety():
    """Verify ratio calculations handle tenure=0 and last_interaction=0 safely without NaN."""
    payload = SAMPLE_BASE_CUSTOMER.copy()
    payload["tenure"] = 0.0
    payload["last_interaction"] = 0.0
    response = client.post("/predict", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert 0.0 <= data["churn_probability"] <= 1.0


def test_tier2_empty_batch_prediction():
    """Verify empty batch request returns zero processed count gracefully."""
    response = client.post("/batch_predict", json=[], headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 0
    assert data["predictions"] == []


def test_tier2_non_existent_and_extreme_customer_ids():
    """Verify non-existent customer in Feast returns 404, negative ID returns 422, and extreme positive ID returns 200."""
    res_feast_neg = client.get("/predict/customer/-1", headers=AUTH_HEADERS)
    assert res_feast_neg.status_code == 404

    payload_neg = SAMPLE_BASE_CUSTOMER.copy()
    payload_neg["customer_id"] = -9999
    res_predict_neg = client.post("/predict", json=payload_neg, headers=AUTH_HEADERS)
    assert res_predict_neg.status_code == 422

    payload_ext = SAMPLE_BASE_CUSTOMER.copy()
    payload_ext["customer_id"] = 999999999
    res_predict_ext = client.post("/predict", json=payload_ext, headers=AUTH_HEADERS)
    assert res_predict_ext.status_code == 200
    assert res_predict_ext.json()["customer_id"] == 999999999


# ============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS & CONSISTENCY
# ============================================================================

def test_tier3_ab_testing_deterministic_routing():
    """Verify deterministic MD5 routing assigns the exact same model across repeated requests."""
    route_champion, ver_champ = route_customer_to_model(1001)
    route_challenger, ver_chal = route_customer_to_model(3)

    assert route_champion == "champion"
    assert "champion" in ver_champ
    assert route_challenger == "challenger"
    assert "challenger" in ver_chal

    payload_champ = SAMPLE_BASE_CUSTOMER.copy()
    payload_champ["customer_id"] = 1001
    for _ in range(3):
        res = client.post("/predict/ab_test", json=payload_champ, headers=AUTH_HEADERS)
        assert res.status_code == 200
        assert res.json()["model_version"] == ver_champ

    payload_chal = SAMPLE_BASE_CUSTOMER.copy()
    payload_chal["customer_id"] = 3
    for _ in range(3):
        res = client.post("/predict/ab_test", json=payload_chal, headers=AUTH_HEADERS)
        assert res.status_code == 200
        assert res.json()["model_version"] == ver_chal


def test_tier3_single_vs_batch_prediction_consistency():
    """Verify inference results for a customer are identical between single and batch endpoints."""
    customer_a = SAMPLE_BASE_CUSTOMER.copy()
    customer_a["customer_id"] = 5001
    customer_b = SAMPLE_BASE_CUSTOMER.copy()
    customer_b["customer_id"] = 5002
    customer_b["support_calls"] = 8.0
    customer_b["payment_delay"] = 15.0

    res_single_a = client.post("/predict", json=customer_a, headers=AUTH_HEADERS).json()
    res_single_b = client.post("/predict", json=customer_b, headers=AUTH_HEADERS).json()

    res_batch = client.post("/batch_predict", json=[customer_a, customer_b], headers=AUTH_HEADERS).json()
    batch_preds = res_batch["predictions"]

    assert batch_preds[0]["churn_prediction"] == res_single_a["churn_prediction"]
    assert pytest.approx(batch_preds[0]["churn_probability"], abs=1e-4) == res_single_a["churn_probability"]
    assert batch_preds[0]["risk_level"] == res_single_a["risk_level"]

    assert batch_preds[1]["churn_prediction"] == res_single_b["churn_prediction"]
    assert pytest.approx(batch_preds[1]["churn_probability"], abs=1e-4) == res_single_b["churn_probability"]
    assert batch_preds[1]["risk_level"] == res_single_b["risk_level"]


def test_tier3_ab_analytics_traffic_distribution_consistency():
    """Verify A/B testing analytics endpoint preserves traffic accounting consistency."""
    response = client.get("/ab_test/analytics")
    assert response.status_code == 200
    data = response.json()
    if data.get("status") == "ACTIVE" and "traffic_observed" in data:
        observed = data["traffic_observed"]
        total = observed["total_inferences"]
        champ_s = observed["champion_samples"]
        chal_s = observed["challenger_samples"]
        assert total == champ_s + chal_s
        if total > 0:
            sum_pct = observed["champion_traffic_pct"] + observed["challenger_traffic_pct"]
            assert pytest.approx(sum_pct, abs=0.5) == 100.0


# ============================================================================
# TIER 4: REAL-WORLD OPERATIONAL SCENARIOS & SLAS
# ============================================================================

def test_tier4_feast_online_retrieval_latency_sla():
    """Verify Feast online feature retrieval and inference latency conforms to SLA (< 200ms)."""
    latencies = []
    for _ in range(5):
        t0 = time.perf_counter()
        res = client.get("/predict/customer/156624", headers=AUTH_HEADERS)
        dur = (time.perf_counter() - t0) * 1000.0
        assert res.status_code == 200
        latencies.append(dur)
        payload_lat = res.json()["latency_ms"]
        assert payload_lat > 0

    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 200.0, f"Average latency {avg_latency}ms exceeded 200ms SLA threshold"


def test_tier4_batch_inference_throughput_and_scaling():
    """Verify batch inference handles 30 customer payloads efficiently with consistent metrics."""
    batch_records = []
    for i in range(30):
        rec = SAMPLE_BASE_CUSTOMER.copy()
        rec["customer_id"] = 7000 + i
        rec["total_spend"] = float(100 + i * 25)
        rec["support_calls"] = float(i % 6)
        batch_records.append(rec)

    t0 = time.perf_counter()
    response = client.post("/batch_predict", json=batch_records, headers=AUTH_HEADERS)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 30
    assert len(data["predictions"]) == 30
    assert data["churn_count"] + data["retention_count"] == 30
    assert sum(data["risk_distribution"].values()) == 30
    assert elapsed_ms < 1500.0, f"Batch inference took {elapsed_ms}ms (> 1500ms threshold)"


def test_tier4_full_response_contract_verification():
    """Verify all fields and data types of PredictionResponse adhere to contract specifications."""
    response = client.post("/predict", json=SAMPLE_BASE_CUSTOMER, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["customer_id"], int)
    assert data["churn_prediction"] in [0, 1]
    assert 0.0 <= data["churn_probability"] <= 1.0
    assert data["risk_level"] in ["Low Risk", "Medium Risk", "High Risk"]
    assert isinstance(data["recommended_action"], str) and len(data["recommended_action"]) > 5
    assert isinstance(data["feature_attributions"], dict)
    assert len(data["feature_attributions"]) == 13
    assert "Đặc trưng thúc đẩy" in data["explanation_summary"] or "an toàn" in data["explanation_summary"]
    assert isinstance(data["model_version"], str)
    assert isinstance(data["latency_ms"], (float, int)) and data["latency_ms"] >= 0


def test_tier4_comprehensive_security_gate_matrix():
    """Verify security gateway rejects unauthenticated requests across all protected endpoints."""
    protected_calls = [
        ("POST", "/predict", {"json": SAMPLE_BASE_CUSTOMER}),
        ("POST", "/batch_predict", {"json": [SAMPLE_BASE_CUSTOMER]}),
        ("GET", "/predict/customer/156624", {}),
        ("POST", "/predict/ab_test", {"json": SAMPLE_BASE_CUSTOMER}),
        ("POST", "/api/v1/trigger_retrain", {})
    ]

    for method, path, kwargs in protected_calls:
        # Request with no API key
        if method == "POST":
            res_none = client.post(path, **kwargs)
            res_bad = client.post(path, headers={"X-API-Key": "invalid-token"}, **kwargs)
        else:
            res_none = client.get(path, **kwargs)
            res_bad = client.get(path, headers={"X-API-Key": "invalid-token"}, **kwargs)

        assert res_none.status_code == 401, f"{path} did not reject missing API key"
        assert res_bad.status_code == 401, f"{path} did not reject invalid API key"
