"""Check the new API contract and 64-bit ID preservation with a tiny local artifact."""

import json

import joblib
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sklearn.linear_model import LogisticRegression

from src.kkbox import api
from src.kkbox.contract import FEATURE_COLUMNS, FEATURE_VERSION


def test_prediction_contract_and_missing_snapshot(tmp_path, monkeypatch):
    key = "18446744073709551614"
    sample = np.vstack([np.zeros(len(FEATURE_COLUMNS)), np.ones(len(FEATURE_COLUMNS))]).astype(np.float32)
    model = LogisticRegression().fit(sample, np.array([0, 1]))
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    joblib.dump(model, model_dir / "pilot_model.joblib")
    (model_dir / "model_metadata.json").write_text(json.dumps({
        "mode": "pilot", "model_version": "pilot-test", "feature_columns": FEATURE_COLUMNS,
        "feature_version": FEATURE_VERSION, "classification_threshold": 0.5,
        "risk_medium_threshold": 0.3, "risk_high_threshold": 0.7,
    }), encoding="utf-8")
    table = pa.table({"snapshot_key": [f"{key}|2017-02-28"],
                      **{name: [1.0] for name in FEATURE_COLUMNS}})
    feature_file = tmp_path / "features.parquet"
    pq.write_table(table, feature_file)

    monkeypatch.setattr(api, "MODEL_DIR", model_dir)
    monkeypatch.setattr(api, "FEATURE_PATH", str(feature_file))
    monkeypatch.setenv("KKBOX_ALLOW_PILOT", "1")
    monkeypatch.setenv("KKBOX_FEATURE_BACKEND", "parquet")
    monkeypatch.setenv("KKBOX_API_KEY", "local-test-key")
    api.load_model.cache_clear()
    payload = {"subscriber_key": key, "as_of_date": "2017-02-28"}
    body = api.predict(api.PredictionRequest.model_validate(payload), "local-test-key").model_dump()
    assert body["subscriber_key"] == key
    assert body["as_of_date"] == "2017-02-28"
    assert body["model_version"] == "pilot-test"
    assert body["prediction_mode"] == "historical_replay"
    assert 0.0 <= body["churn_probability"] <= 1.0
    assert api.reload_champion("local-test-key")["model_version"] == "pilot-test"

    with pytest.raises(HTTPException) as missing:
        api.predict(api.PredictionRequest.model_validate({**payload, "subscriber_key": "1"}), "local-test-key")
    assert missing.value.status_code == 404
    with pytest.raises(HTTPException) as unauthorized:
        api.predict(api.PredictionRequest.model_validate(payload), None)
    assert unauthorized.value.status_code == 401
    with pytest.raises(ValidationError):
        api.PredictionRequest.model_validate({**payload, "subscriber_key": 123})
    with pytest.raises(ValidationError):
        api.PredictionRequest.model_validate({**payload, "as_of_date": "2026-11-03"})
