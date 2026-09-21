"""
Integration & Unit Test Suite for MLOps FastAPI Serving.
Adapted from the production benchmark repository:
`el1zabethcodes/mlops-churn-feature-store/tests/test_api.py`.
Adheres to Invariant 01 (Clean Scaffolding) and Invariant 02 (< 400 lines).
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health():
    """Verify endpoint health status checks, model loading, and Feast store connectivity."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "champion_model" in data
    assert "2.0.0" in data["model_version"]


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
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["churn_prediction"] in [0, 1]
    assert 0.0 <= data["churn_probability"] <= 1.0
    assert data["risk_level"] in ["Low Risk", "Medium Risk", "High Risk"]
    assert len(data["recommended_action"]) > 5
    assert "feature_attributions" in data
    assert "payment_delay" in data["feature_attributions"]
    assert "explanation_summary" in data


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
    response = client.post("/batch_predict", json=customers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2
    assert len(data["predictions"]) == 2
    assert "risk_distribution" in data


def test_predict_from_feast_online_store():
    """Verify real-time prediction using Feast Feature Store retrieval by customer ID."""
    # Customer 156624 exists in the materialized SQLite online store
    response = client.get("/predict/customer/156624")
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == 156624
    assert data["churn_prediction"] in [0, 1]
    assert "feature_attributions" in data
    assert data["latency_ms"] >= 0


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
    response = client.post("/predict", json=payload)
    assert response.status_code == 422  # Unprocessable Entity


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
    """Verify retrain webhook endpoint response."""
    response = client.post("/api/v1/trigger_retrain?force=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "TRIGGERED"
    assert "triggered_at" in data
