"""
Integration & Unit Test Suite for MLOps FastAPI Serving.
Kiểm thử toàn diện: Health, Auth (401), Serving, Feast Online Store (200 & 404),
Validation (422), Observability, A/B Testing, CSV Upload và Trigger Retrain.
"""
import io
import os
import time
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "mlops-churn-secret-2026"}


def test_health():
    """Verify endpoint health status checks, model loading, and Feast store connectivity."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "champion_model" in data
    assert "2.0.0" in data["model_version"]
    assert "CONNECTED" in data["feast_online_store"]


def test_unauthorized_access():
    """Verify security gateway strictly rejects unauthenticated requests with HTTP 401."""
    # Request without API key header
    res_no_key = client.post("/predict", json={"customer_id": 1001})
    assert res_no_key.status_code == 401
    assert "Thiếu hoặc sai API Key" in res_no_key.json()["detail"]

    # Request with invalid API key header
    res_bad_key = client.post("/predict", json={"customer_id": 1001}, headers={"X-API-Key": "wrong-secret"})
    assert res_bad_key.status_code == 401


def test_predict_single_customer():
    """Verify single customer churn prediction and risk categorization with SHAP."""
    payload = {
        "customer_id": 1001,
        "age": 45.0,
        "gender": "Female",
        "tenure": 36.0,
        "usage_frequency": 22.0,
        "support_calls": 1.0,
        "payment_delay": 0.0,
        "subscription_type": "Premium",
        "contract_length": "Annual",
        "total_spend": 980.0,
        "last_interaction": 3.0
    }
    response = client.post("/predict", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["churn_prediction"] in [0, 1]
    assert 0.0 <= data["churn_probability"] <= 1.0
    assert data["risk_level"] in ["Low Risk", "Medium Risk", "High Risk"]
    assert len(data["recommended_action"]) > 5
    assert "feature_attributions" in data
    assert "payment_delay" in data["feature_attributions"]
    assert "explanation_summary" in data
    assert "model_version" in data


def test_batch_predict():
    """Verify batch JSON inference across multiple customer records."""
    customers = [
        {
            "customer_id": 2001,
            "age": 22.0,
            "gender": "Male",
            "tenure": 2.0,
            "usage_frequency": 4.0,
            "support_calls": 8.0,
            "payment_delay": 15.0,
            "subscription_type": "Basic",
            "contract_length": "Monthly",
            "total_spend": 120.0,
            "last_interaction": 25.0
        },
        {
            "customer_id": 2002,
            "age": 55.0,
            "gender": "Female",
            "tenure": 48.0,
            "usage_frequency": 25.0,
            "support_calls": 0.0,
            "payment_delay": 0.0,
            "subscription_type": "Premium",
            "contract_length": "Annual",
            "total_spend": 1250.0,
            "last_interaction": 2.0
        }
    ]
    response = client.post("/batch_predict", json=customers, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2
    assert len(data["predictions"]) == 2
    assert "risk_distribution" in data


def test_predict_from_feast_online_store():
    """Verify real-time prediction using Feast Feature Store retrieval by customer ID."""
    # Customer 156624 exists in the materialized SQLite online store
    response = client.get("/predict/customer/156624", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == 156624
    assert data["churn_prediction"] in [0, 1]
    assert "feature_attributions" in data
    assert data["latency_ms"] >= 0


def test_predict_feast_customer_not_found():
    """Verify querying non-existent customer in Feast returns HTTP 404."""
    response = client.get("/predict/customer/99999999", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert "Không tìm thấy khách hàng" in response.json()["detail"]


def test_predict_invalid_enum_validation():
    """Verify strict Pydantic validation rejects invalid enum values with HTTP 422."""
    payload = {
        "customer_id": 9999,
        "age": 30.0,
        "gender": "Alien",  # Invalid enum value!
        "tenure": 12.0,
        "usage_frequency": 10.0,
        "support_calls": 2.0,
        "payment_delay": 1.0,
        "subscription_type": "Basic",
        "contract_length": "Monthly",
        "total_spend": 500.0,
        "last_interaction": 5.0
    }
    response = client.post("/predict", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 422


def test_ab_testing_routing_and_analytics():
    """Verify A/B testing deterministic traffic split and statistical evaluation."""
    payload = {
        "customer_id": 8888,
        "age": 40.0,
        "gender": "Male",
        "tenure": 15.0,
        "usage_frequency": 12.0,
        "support_calls": 4.0,
        "payment_delay": 3.0,
        "subscription_type": "Standard",
        "contract_length": "Quarterly",
        "total_spend": 450.0,
        "last_interaction": 7.0
    }
    res_ab = client.post("/predict/ab_test", json=payload, headers=AUTH_HEADERS)
    assert res_ab.status_code == 200
    data_ab = res_ab.json()
    assert data_ab["model_version"] in ["v2.0.0-champion", "v1.0.0-challenger"]

    res_analytics = client.get("/ab_test/analytics")
    assert res_analytics.status_code == 200
    data_analytics = res_analytics.json()
    assert "traffic_split_config" in data_analytics
    assert "hypothesis_testing" in data_analytics


def test_upload_csv_predict():
    """Verify batch prediction directly from CSV upload."""
    csv_content = (
        "CustomerID,Age,Gender,Tenure,Usage Frequency,Support Calls,Payment Delay,Subscription Type,Contract Length,Total Spend,Last Interaction\n"
        "3001,42,Male,24,18,2,0,Standard,Quarterly,620.0,5\n"
        "3002,29,Female,6,8,7,12,Basic,Monthly,180.0,20\n"
    )
    files = {"file": ("test_batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/upload_csv_predict", files=files, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2
    assert len(data["predictions"]) == 2


def test_models_summary():
    """Verify MLflow experiment tracking summary across all 4 benchmark models."""
    response = client.get("/models/summary")
    assert response.status_code == 200
    data = response.json()
    assert "champion_model" in data
    assert "Random_Forest" in data["models"]
    assert "XGBoost" in data["models"]
    assert "LightGBM" in data["models"]
    assert "Logistic_Regression" in data["models"]


def test_models_tuning():
    """Verify Optuna hyperparameter tuning history endpoint."""
    response = client.get("/models/tuning")
    assert response.status_code == 200
    data = response.json()
    assert "framework" in data
    assert "xgboost_champion" in data
    assert data["xgboost_champion"]["trials_count"] == 12


def test_drift_status():
    """Verify Kolmogorov-Smirnov and Population Stability Index (PSI) drift monitoring."""
    response = client.get("/drift/status")
    assert response.status_code == 200
    data = response.json()
    assert "dataset_drift_detected" in data
    assert "features" in data
    assert "support_calls" in data["features"]
    assert "psi_score" in data["features"]["support_calls"]


def test_metrics_endpoint():
    """Verify observability metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ChurnGuard-MLOps"
    assert "uptime_seconds" in data
    assert "total_inference_requests" in data


def test_trigger_retrain():
    """Verify retrain webhook endpoint response with genuine background execution."""
    response = client.post("/api/v1/trigger_retrain?force=true&dry_run=true", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "TRIGGERED"
    assert "triggered_at" in data
    assert data["job_type"] == "dry_run_execution"

    # Allow detached subprocess to complete and write proof
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "retrain_execution.log")
    for _ in range(50):
        time.sleep(0.2)
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                if "Dry-run verification" in f.read():
                    break
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Dry-run verification" in content


def test_ui_endpoint():
    """Verify Web UI static mount serves HTML."""
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_reload_model_endpoint():
    """Verify hot-reload endpoint responds with reload confirmation."""
    response = client.post("/api/v1/reload_model", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["RELOADED", "NOOP"]

