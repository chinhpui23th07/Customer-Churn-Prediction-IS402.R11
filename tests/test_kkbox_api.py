"""Axis 6: KKBox FastAPI Serving, uint64 Validation, Manual & Batch Replay, Feast/Parquet Backends & Security."""

from __future__ import annotations

import json
import types
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from src.api.main import app as main_app
from src.kkbox import api
from src.kkbox.contract import FEATURE_COLUMNS, FEATURE_VERSION

MAX_UINT64_STR = "18446744073709551615"


def _setup_pilot_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    x = np.array(
        [[float(i + j) for j in range(len(FEATURE_COLUMNS))] for i in range(40)],
        dtype=np.float32,
    )
    y = np.array([i % 2 for i in range(40)], dtype=np.int8)
    model = make_pipeline(SimpleImputer(strategy="constant", fill_value=-1), LogisticRegression())
    model.fit(x, y)

    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "pilot_model.joblib")
    metadata = {
        "mode": "pilot",
        "model": "logistic_regression",
        "model_version": "pilot-test",
        "feature_version": FEATURE_VERSION,
        "feature_columns": FEATURE_COLUMNS,
        "classification_threshold": 0.5,
        "risk_medium_threshold": 0.4,
        "risk_high_threshold": 0.7,
    }
    (model_dir / "model_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    # Row 1: max uint64 key with all 12 features present
    row_full = {
        "subscriber_key": MAX_UINT64_STR,
        "as_of_date": "2017-02-28",
        "snapshot_key": f"{MAX_UINT64_STR}|2017-02-28",
        **{name: float(idx + 1) for idx, name in enumerate(FEATURE_COLUMNS)},
    }
    # Row 2: key "0" with 3 null features (cold-start transaction history)
    row_nulls = {
        "subscriber_key": "0",
        "as_of_date": "2017-01-31",
        "snapshot_key": "0|2017-01-31",
        **{name: float(idx + 2) for idx, name in enumerate(FEATURE_COLUMNS)},
    }
    row_nulls["days_since_last_txn"] = None
    row_nulls["last_auto_renew"] = None
    row_nulls["days_until_expiry"] = None

    feature_file = tmp_path / "features.parquet"
    pd.DataFrame([row_full, row_nulls]).to_parquet(feature_file, index=False)

    monkeypatch.setattr(api, "MODEL_DIR", model_dir)
    monkeypatch.setattr(api, "FEATURE_PATH", str(feature_file))
    monkeypatch.setenv("KKBOX_ALLOW_PILOT", "1")
    monkeypatch.setenv("KKBOX_FEATURE_BACKEND", "parquet")
    monkeypatch.setenv("KKBOX_API_KEY", "test-secret-key")
    api.load_model.cache_clear()
    api.feast_store.cache_clear()
    return {"x-api-key": "test-secret-key"}


def test_health_and_historical_prediction_endpoints_on_both_apps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _setup_pilot_fixture(tmp_path, monkeypatch)

    for target_app in (api.app, main_app):
        client = TestClient(target_app)

        # Predict max uint64 key
        res = client.post(
            "/v1/predictions",
            headers=headers,
            json={"subscriber_key": MAX_UINT64_STR, "as_of_date": "2017-02-28"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["subscriber_key"] == MAX_UINT64_STR
        assert body["as_of_date"] == "2017-02-28"
        assert body["prediction"] in (0, 1)
        assert 0.0 <= body["churn_probability"] <= 1.0
        assert body["risk_level"] in ("low", "medium", "high")
        assert body["model_version"] == "pilot-test"
        assert body["feature_version"] == FEATURE_VERSION
        assert body["prediction_mode"] == "historical_replay"
        assert "is_churn" not in body
        assert "recommended_action" not in body

        # Inspect features with partial nulls (key "0")
        feat_res = client.post(
            "/v1/features",
            headers=headers,
            json={"subscriber_key": "0", "as_of_date": "2017-01-31"},
        )
        assert feat_res.status_code == 200
        feat_body = feat_res.json()
        assert feat_body["missing_count"] == 3
        assert feat_body["features"]["days_since_last_txn"] is None
        assert feat_body["feature_version"] == FEATURE_VERSION

        # Unknown snapshot returns 404
        missing_res = client.post(
            "/v1/predictions",
            headers=headers,
            json={"subscriber_key": "999", "as_of_date": "2017-02-28"},
        )
        assert missing_res.status_code == 404
        assert client.post(
            "/v1/features",
            headers=headers,
            json={"subscriber_key": "999", "as_of_date": "2017-02-28"},
        ).status_code == 404

    # Health check on standalone KKBox app
    kkbox_client = TestClient(api.app)
    health_ok = kkbox_client.get("/health").json()
    assert health_ok == {"status": "ready", "model_version": "pilot-test", "mode": "pilot"}


def test_uint64_and_cutoff_validation_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _setup_pilot_fixture(tmp_path, monkeypatch)
    client = TestClient(api.app)

    invalid_keys = [
        "",
        "01",
        "00",
        "-1",
        "18446744073709551616",  # 2**64 (overflows uint64)
        "abc",
        "12.34",
        " 123",
        "１２３",  # Full-width non-ASCII digits
    ]
    for bad_key in invalid_keys:
        resp = client.post(
            "/v1/predictions",
            headers=headers,
            json={"subscriber_key": bad_key, "as_of_date": "2017-02-28"},
        )
        assert resp.status_code == 422, f"Expected 422 for key={bad_key!r}"

    bad_cutoff = client.post(
        "/v1/predictions",
        headers=headers,
        json={"subscriber_key": "1", "as_of_date": "2017-03-31"},
    )
    assert bad_cutoff.status_code == 422


def test_manual_and_batch_prediction_scenarios_and_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _setup_pilot_fixture(tmp_path, monkeypatch)
    client = TestClient(api.app)

    # Valid manual scenario with partial nulls
    features_payload: dict[str, float | None] = {name: float(i) for i, name in enumerate(FEATURE_COLUMNS)}
    features_payload["days_since_last_txn"] = None
    manual_res = client.post("/v1/predictions/manual", headers=headers, json={"features": features_payload})
    assert manual_res.status_code == 200
    assert manual_res.json()["prediction_mode"] == "manual_scenario"

    # Missing column -> 422
    incomplete = dict(features_payload)
    incomplete.pop("txn_count_30d")
    assert client.post("/v1/predictions/manual", headers=headers, json={"features": incomplete}).status_code == 422

    # Extra column -> 422
    extra = {**features_payload, "extra_col": 1.0}
    assert client.post("/v1/predictions/manual", headers=headers, json={"features": extra}).status_code == 422

    # All nulls -> 422
    all_nulls = {name: None for name in FEATURE_COLUMNS}
    assert client.post("/v1/predictions/manual", headers=headers, json={"features": all_nulls}).status_code == 422

    # Non-finite NaN / Inf rejected by ManualPredictionRequest validator
    for non_finite in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError, match="finite numbers"):
            api.ManualPredictionRequest(features={**features_payload, "paid_amount_30d": non_finite})

    # Batch prediction: 2 existing + 1 missing
    batch_res = client.post(
        "/v1/predictions/batch",
        headers=headers,
        json={
            "items": [
                {"subscriber_key": MAX_UINT64_STR, "as_of_date": "2017-02-28"},
                {"subscriber_key": "0", "as_of_date": "2017-01-31"},
                {"subscriber_key": "404", "as_of_date": "2017-02-28"},
            ]
        },
    )
    assert batch_res.status_code == 200
    batch_body = batch_res.json()
    assert batch_body["total"] == 3
    assert batch_body["succeeded"] == 2
    assert batch_body["failed"] == 1
    assert batch_body["results"][0]["result"]["subscriber_key"] == MAX_UINT64_STR
    assert batch_body["results"][2]["result"] is None
    assert batch_body["results"][2]["error"] == "No feature snapshot"

    # Batch limits: empty (0) and > 100 (101) rejected with 422
    assert client.post("/v1/predictions/batch", headers=headers, json={"items": []}).status_code == 422
    too_many = [{"subscriber_key": "1", "as_of_date": "2017-02-28"}] * 101
    assert client.post("/v1/predictions/batch", headers=headers, json={"items": too_many}).status_code == 422


def test_feast_backend_duplicate_parquet_and_model_reload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _setup_pilot_fixture(tmp_path, monkeypatch)
    client = TestClient(api.app)

    # 1. Feast online store backend lookup
    class _FakeFeastResp:
        def __init__(self, data: dict) -> None:
            self._data = data

        def to_dict(self) -> dict:
            return self._data

    class _FakeFeastStore:
        def get_online_features(self, features: list[str], entity_rows: list[dict]) -> _FakeFeastResp:
            key = entity_rows[0]["snapshot_key"]
            if key == "777|2017-02-28":
                return _FakeFeastResp({name: [float(i + 1)] for i, name in enumerate(FEATURE_COLUMNS)})
            return _FakeFeastResp({name: [None] for name in FEATURE_COLUMNS})

    monkeypatch.setenv("KKBOX_FEATURE_BACKEND", "feast")
    monkeypatch.setattr(api, "feast_store", lambda: _FakeFeastStore())
    res_feast = client.post(
        "/v1/predictions",
        headers=headers,
        json={"subscriber_key": "777", "as_of_date": "2017-02-28"},
    )
    assert res_feast.status_code == 200
    assert client.post(
        "/v1/predictions",
        headers=headers,
        json={"subscriber_key": "888", "as_of_date": "2017-02-28"},
    ).status_code == 404

    # 2. Duplicate snapshot_key in Parquet raises 503
    monkeypatch.setenv("KKBOX_FEATURE_BACKEND", "parquet")
    dup_file = tmp_path / "dup_features.parquet"
    dup_row = {
        "subscriber_key": "555",
        "as_of_date": "2017-02-28",
        "snapshot_key": "555|2017-02-28",
        **{name: 1.0 for name in FEATURE_COLUMNS},
    }
    pd.DataFrame([dup_row, dup_row]).to_parquet(dup_file, index=False)
    monkeypatch.setattr(api, "FEATURE_PATH", str(dup_file))
    assert client.post(
        "/v1/predictions",
        headers=headers,
        json={"subscriber_key": "555", "as_of_date": "2017-02-28"},
    ).status_code == 503

    # 3. Reload endpoint
    reload_res = client.post("/v1/model/reload", headers=headers)
    assert reload_res.status_code == 200
    assert reload_res.json() == {"status": "ready", "model_version": "pilot-test"}


def test_security_auth_pilot_gate_and_contract_mismatch_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _setup_pilot_fixture(tmp_path, monkeypatch)
    client = TestClient(api.app)

    # Wrong or missing x-api-key -> 401
    assert client.post(
        "/v1/predictions",
        headers={"x-api-key": "wrong"},
        json={"subscriber_key": MAX_UINT64_STR, "as_of_date": "2017-02-28"},
    ).status_code == 401
    assert client.post(
        "/v1/predictions",
        json={"subscriber_key": MAX_UINT64_STR, "as_of_date": "2017-02-28"},
    ).status_code == 401

    # Unconfigured KKBOX_API_KEY -> 503
    monkeypatch.delenv("KKBOX_API_KEY", raising=False)
    assert client.post(
        "/v1/predictions",
        headers=headers,
        json={"subscriber_key": MAX_UINT64_STR, "as_of_date": "2017-02-28"},
    ).status_code == 503
    monkeypatch.setenv("KKBOX_API_KEY", "test-secret-key")

    # Pilot model disabled when KKBOX_ALLOW_PILOT != 1 -> 503 & degraded health
    monkeypatch.setenv("KKBOX_ALLOW_PILOT", "0")
    api.load_model.cache_clear()
    assert client.get("/health").json()["status"] == "degraded"
    assert client.post(
        "/v1/predictions",
        headers=headers,
        json={"subscriber_key": MAX_UINT64_STR, "as_of_date": "2017-02-28"},
    ).status_code == 503
    assert client.post("/v1/model/reload", headers=headers).status_code == 503

    # Feature version mismatch in model_metadata.json -> 503
    monkeypatch.setenv("KKBOX_ALLOW_PILOT", "1")
    meta_path = tmp_path / "models" / "model_metadata.json"
    bad_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    bad_meta["feature_version"] = "wrong-version"
    meta_path.write_text(json.dumps(bad_meta), encoding="utf-8")
    api.load_model.cache_clear()
    assert client.post(
        "/v1/predictions",
        headers=headers,
        json={"subscriber_key": MAX_UINT64_STR, "as_of_date": "2017-02-28"},
    ).status_code == 503
