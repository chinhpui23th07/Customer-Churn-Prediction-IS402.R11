"""Azure Well-Architected Framework Security Testing (WAF SE:11) - Assume-Breach Suite.

Tests KKBox serving APIs against the 4 core cloud threat vectors:
1. Authorization Bypass (unauthenticated, empty, malformed, whitespace-only keys).
2. Input Sanitization & Injection Deterrence (SQLi, NoSQLi, path traversal in keys).
3. Privilege Escalation & Admin Route Segregation (reload endpoint security).
4. Information Leakage & Exception Traceback Sanitation (zero filesystem/secret leaks).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression

from src.kkbox import api
from src.kkbox.contract import FEATURE_COLUMNS, FEATURE_VERSION


@pytest.fixture(scope="module")
def api_security_client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    """Fixture configuring authentic KKBox pilot serving environment."""
    tmp_path = tmp_path_factory.mktemp("waf_security")
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    # Train dummy logistic regression
    x = np.ones((10, len(FEATURE_COLUMNS)), dtype=np.float32)
    y = np.array([0, 1] * 5, dtype=np.int8)
    clf = LogisticRegression()
    clf.fit(x, y)
    joblib.dump(clf, model_dir / "pilot_model.joblib")

    meta = {
        "mode": "pilot",
        "model": "logistic_regression",
        "model_version": "security-waf-v1",
        "feature_version": FEATURE_VERSION,
        "feature_columns": FEATURE_COLUMNS,
        "classification_threshold": 0.5,
        "risk_medium_threshold": 0.4,
        "risk_high_threshold": 0.7,
    }
    (model_dir / "model_metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    # Parquet feature row
    row = {
        "subscriber_key": "999999999999999999",
        "as_of_date": "2017-02-28",
        "snapshot_key": "999999999999999999|2017-02-28",
        **{c: 1.0 for c in FEATURE_COLUMNS},
    }
    feat_path = tmp_path / "features.parquet"
    pd.DataFrame([row]).to_parquet(feat_path, index=False)

    old_model_dir = api.MODEL_DIR
    old_feat_path = api.FEATURE_PATH
    api.MODEL_DIR = model_dir
    api.FEATURE_PATH = str(feat_path)
    api.load_model.cache_clear()

    import os
    os.environ["KKBOX_ALLOW_PILOT"] = "1"
    os.environ["KKBOX_FEATURE_BACKEND"] = "parquet"
    os.environ["KKBOX_API_KEY"] = "super-secret-waf-key-12345"

    yield TestClient(api.app)

    api.MODEL_DIR = old_model_dir
    api.FEATURE_PATH = old_feat_path
    api.load_model.cache_clear()


def test_waf_authorization_bypass_rejected(api_security_client: TestClient) -> None:
    """Vector 1: Reject unauthenticated or bypassed requests with HTTP 401."""
    valid_payload = {"subscriber_key": "999999999999999999", "as_of_date": "2017-02-28"}

    # 1. Missing header
    res_no_auth = api_security_client.post("/v1/predictions", json=valid_payload)
    assert res_no_auth.status_code == 401
    assert "Invalid API key" in res_no_auth.json()["detail"]

    # 2. Empty or whitespace-only header
    res_empty = api_security_client.post("/v1/predictions", headers={"x-api-key": ""}, json=valid_payload)
    assert res_empty.status_code == 401

    res_ws = api_security_client.post("/v1/predictions", headers={"x-api-key": "   "}, json=valid_payload)
    assert res_ws.status_code == 401

    # 3. Forged key
    res_forged = api_security_client.post("/v1/predictions", headers={"x-api-key": "attacker-fake-key"}, json=valid_payload)
    assert res_forged.status_code == 401


def test_waf_injection_attack_vectors_rejected(api_security_client: TestClient) -> None:
    """Vector 2: Test SQLi, NoSQLi, and directory traversal payloads in subscriber_key."""
    headers = {"x-api-key": "super-secret-waf-key-12345"}

    malicious_keys = [
        "' OR '1'='1",
        "1; DROP TABLE subscribers;--",
        "../../../../etc/passwd",
        "NaN",
        "1e18",
        "-999999",
        "001234",  # Non-canonical leading zeros
        "0xDEADBEEF",
        "18446744073709551616",  # Exceeds max uint64 (2^64 - 1)
    ]

    for attack_key in malicious_keys:
        res = api_security_client.post(
            "/v1/predictions",
            headers=headers,
            json={"subscriber_key": attack_key, "as_of_date": "2017-02-28"},
        )
        assert res.status_code == 422, f"Expected 422 for malicious key '{attack_key}', got {res.status_code}"
        body = res.text
        assert "Internal Server Error" not in body
        assert "syntax error" not in body.lower()


def test_waf_privilege_escalation_and_admin_segregation(api_security_client: TestClient) -> None:
    """Vector 3: Test that model reload requires valid administrative authorization."""
    # Unauthenticated reload attempt
    res_unauth = api_security_client.post("/v1/model/reload")
    assert res_unauth.status_code == 401

    # Bad credentials reload attempt
    res_bad = api_security_client.post("/v1/model/reload", headers={"x-api-key": "wrong-key"})
    assert res_bad.status_code == 401

    # Authorized reload succeeds and clears cache
    res_ok = api_security_client.post("/v1/model/reload", headers={"x-api-key": "super-secret-waf-key-12345"})
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "ready"

    # Strict privilege separation with distinct admin key
    import os
    os.environ["KKBOX_ADMIN_API_KEY"] = "admin-secret-waf-root-999"
    try:
        # Standard user key is rejected on admin reload route
        res_user_denied = api_security_client.post(
            "/v1/model/reload", headers={"x-api-key": "super-secret-waf-key-12345"}
        )
        assert res_user_denied.status_code == 401
        assert "Invalid admin API key" in res_user_denied.json()["detail"]

        # Admin key successfully reloads model
        res_admin_ok = api_security_client.post(
            "/v1/model/reload", headers={"x-api-key": "admin-secret-waf-root-999"}
        )
        assert res_admin_ok.status_code == 200
        assert res_admin_ok.json()["status"] == "ready"

        # Admin key cannot invoke standard prediction routes (privilege boundary)
        res_admin_predict = api_security_client.post(
            "/v1/predictions",
            headers={"x-api-key": "admin-secret-waf-root-999"},
            json={"subscriber_key": "999999999999999999", "as_of_date": "2017-02-28"},
        )
        assert res_admin_predict.status_code == 401
    finally:
        os.environ.pop("KKBOX_ADMIN_API_KEY", None)



def test_waf_information_leakage_and_traceback_sanitation(api_security_client: TestClient) -> None:
    """Vector 4: Ensure error responses never leak stack traces, local paths, or secrets."""
    headers = {"x-api-key": "super-secret-waf-key-12345"}

    # 1. Malformed JSON body
    res_malformed = api_security_client.post(
        "/v1/predictions",
        headers=headers,
        content=b"{'unclosed_json': true,",
    )
    assert res_malformed.status_code in (400, 422)
    body = res_malformed.text
    assert "Traceback (most recent call last)" not in body
    assert "super-secret-waf-key-12345" not in body
    assert "c:\\" not in body.lower()
    assert "/home/" not in body.lower()

    # 2. Unsupported cutoff date outside contract (temporal leak attempt)
    res_bad_cutoff = api_security_client.post(
        "/v1/predictions",
        headers=headers,
        json={"subscriber_key": "999999999999999999", "as_of_date": "2024-11-09"},
    )
    assert res_bad_cutoff.status_code == 422
    assert "2017-01-31" in res_bad_cutoff.text or "2017-02-28" in res_bad_cutoff.text


def test_waf_nan_inf_manual_prediction_sanitation(api_security_client: TestClient) -> None:
    """Vector 4b: Validate NaN, Infinity, and invalid types are strictly rejected in feature inputs."""
    headers = {"x-api-key": "super-secret-waf-key-12345"}

    # 1. Non-numeric string payload returns HTTP 422
    bad_features = {c: 1.0 for c in FEATURE_COLUMNS}
    bad_features["txn_count_30d"] = "unparseable_string"
    res_str = api_security_client.post(
        "/v1/predictions/manual",
        headers=headers,
        json={"features": bad_features},
    )
    assert res_str.status_code == 422

    # 2. Missing required feature columns returns HTTP 422
    partial_features = {"txn_count_30d": 5.0}
    res_partial = api_security_client.post(
        "/v1/predictions/manual",
        headers=headers,
        json={"features": partial_features},
    )
    assert res_partial.status_code == 422

    # 3. Direct Pydantic validation rejects NaN and Infinity
    from pydantic import ValidationError
    from src.kkbox.api import ManualPredictionRequest

    with pytest.raises(ValidationError) as exc_nan:
        ManualPredictionRequest(features={c: float("nan") if c == "txn_count_30d" else 1.0 for c in FEATURE_COLUMNS})
    assert "must be finite numbers or null" in str(exc_nan.value)

    with pytest.raises(ValidationError) as exc_inf:
        ManualPredictionRequest(features={c: float("inf") if c == "paid_amount_30d" else 1.0 for c in FEATURE_COLUMNS})
    assert "must be finite numbers or null" in str(exc_inf.value)


def test_waf_valid_authenticated_flow(api_security_client: TestClient) -> None:
    """Verify happy path works reliably with correct credentials and canonical key."""
    headers = {"x-api-key": "super-secret-waf-key-12345"}
    res = api_security_client.post(
        "/v1/predictions",
        headers=headers,
        json={"subscriber_key": "999999999999999999", "as_of_date": "2017-02-28"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["subscriber_key"] == "999999999999999999"
    assert data["as_of_date"] == "2017-02-28"
    assert data["prediction"] in (0, 1)
    assert 0.0 <= data["churn_probability"] <= 1.0
    assert data["prediction_mode"] == "historical_replay"
