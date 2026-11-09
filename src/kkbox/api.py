"""Historical KKBox churn API using the same feature columns as training."""

from __future__ import annotations

import hmac
import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import duckdb
import joblib
import numpy as np
from fastapi import APIRouter, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from src.kkbox.contract import ALLOWED_CUTOFFS, FEATURE_COLUMNS, FEATURE_VERSION

MODEL_DIR = Path(os.getenv("KKBOX_MODEL_DIR", "data/kkbox_models"))
FEATURE_PATH = os.getenv("KKBOX_FEATURE_PATH", "data/kkbox_processed/features/**/*.parquet")
FEAST_REPO = os.getenv("KKBOX_FEAST_REPO", "data/kkbox_feast")
MAX_UINT64 = 2**64 - 1


class PredictionRequest(BaseModel):
    subscriber_key: str = Field(..., description="Pseudonymized 64-bit key as a decimal string")
    as_of_date: Literal["2017-01-31", "2017-02-28"]

    @field_validator("subscriber_key")
    @classmethod
    def valid_key(cls, value: str) -> str:
        if not value or not value.isascii() or not value.isdecimal() or (len(value) > 1 and value[0] == "0"):
            raise ValueError("subscriber_key must be a canonical decimal string")
        if int(value) > MAX_UINT64:
            raise ValueError("subscriber_key exceeds uint64 range")
        return value


class PredictionResponse(BaseModel):
    subscriber_key: str
    as_of_date: str
    prediction: int
    churn_probability: float
    risk_level: Literal["low", "medium", "high"]
    model_version: str
    feature_version: str
    prediction_mode: Literal["historical_replay"] = "historical_replay"


class ManualPredictionRequest(BaseModel):
    features: dict[str, float | None]

    @model_validator(mode="after")
    def valid_features(self):
        if set(self.features) != set(FEATURE_COLUMNS):
            raise ValueError("features must contain exactly the 12 KKBox model columns")
        if all(value is None for value in self.features.values()):
            raise ValueError("at least one feature value is required")
        if any(value is not None and not math.isfinite(value) for value in self.features.values()):
            raise ValueError("feature values must be finite numbers or null")
        return self


class ManualPredictionResponse(BaseModel):
    prediction: int
    churn_probability: float
    risk_level: Literal["low", "medium", "high"]
    model_version: str
    feature_version: str
    prediction_mode: Literal["manual_scenario"] = "manual_scenario"


class FeatureResponse(BaseModel):
    subscriber_key: str
    as_of_date: str
    features: dict[str, float | None]
    missing_count: int
    feature_version: str


class BatchPredictionRequest(BaseModel):
    items: list[PredictionRequest] = Field(..., min_length=1, max_length=100)


class BatchPredictionItem(BaseModel):
    row: int
    subscriber_key: str
    as_of_date: str
    result: PredictionResponse | None = None
    error: str | None = None


class BatchPredictionResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[BatchPredictionItem]


@lru_cache(maxsize=1)
def load_model():
    metadata_path = MODEL_DIR / "model_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError("KKBox model metadata is missing")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata["feature_columns"] != FEATURE_COLUMNS or metadata["feature_version"] != FEATURE_VERSION:
        raise RuntimeError("Training and serving feature contracts differ")
    if metadata["mode"] == "pilot" and os.getenv("KKBOX_ALLOW_PILOT") != "1":
        raise RuntimeError("Pilot model serving is disabled")
    if metadata["mode"] == "pilot":
        return joblib.load(MODEL_DIR / "pilot_model.joblib"), metadata
    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{(MODEL_DIR / 'mlflow.db').resolve().as_posix()}")
    mlflow.set_tracking_uri(tracking_uri)
    version = MlflowClient().get_model_version_by_alias("KKBoxChurn", "champion")
    tags = version.tags or {}
    if tags.get("feature_version") != FEATURE_VERSION:
        raise RuntimeError("Champion model feature version differs from serving contract")
    metadata = {**metadata, "model_version": str(version.version),
                "classification_threshold": float(tags["classification_threshold"]),
                "risk_medium_threshold": float(tags["risk_medium_threshold"]),
                "risk_high_threshold": float(tags["risk_high_threshold"])}
    model = mlflow.sklearn.load_model(f"models:/KKBoxChurn/{version.version}")
    return model, metadata


def parquet_features(snapshot_key: str) -> list[float | None] | None:
    connection = duckdb.connect()
    try:
        columns = ", ".join(FEATURE_COLUMNS)
        rows = connection.execute(
            f"SELECT {columns} FROM read_parquet(?, hive_partitioning=true) WHERE snapshot_key = ? LIMIT 2",
            [FEATURE_PATH, snapshot_key],
        ).fetchall()
        if len(rows) > 1:
            raise RuntimeError("Duplicate snapshot key in processed feature output")
        return list(rows[0]) if rows else None
    finally:
        connection.close()


@lru_cache(maxsize=1)
def feast_store():
    from feast import FeatureStore
    return FeatureStore(repo_path=FEAST_REPO)


def feast_features(snapshot_key: str) -> list[float | None] | None:
    features = [f"kkbox_churn_features:{name}" for name in FEATURE_COLUMNS]
    result = feast_store().get_online_features(
        features=features, entity_rows=[{"snapshot_key": snapshot_key}]
    ).to_dict()
    values = [result.get(name, result.get(f"kkbox_churn_features:{name}", [None]))[0]
              for name in FEATURE_COLUMNS]
    return None if all(value is None for value in values) else values


router = APIRouter(tags=["KKBox Churn Serving"])
WEB_DIR = Path(__file__).resolve().parent / "web"


def require_api_key(value: str | None) -> None:
    configured_key = os.getenv("KKBOX_API_KEY")
    if not configured_key:
        raise HTTPException(status_code=503, detail="API secret is not configured")
    if not value or not hmac.compare_digest(value, configured_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.get("/demo", include_in_schema=False)
def demo():
    return FileResponse(WEB_DIR / "index.html")


app = FastAPI(title="KKBox Customer Churn API", version="1.0.0")
app.mount("/demo/assets", StaticFiles(directory=WEB_DIR), name="kkbox-demo-assets")


@app.get("/health")
def health():
    try:
        _, metadata = load_model()
        return {"status": "ready", "model_version": str(metadata["model_version"]),
                "mode": metadata["mode"]}
    except Exception:
        return {"status": "degraded", "reason": "Model unavailable"}


@router.post("/v1/predictions", response_model=PredictionResponse)
def predict(payload: PredictionRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    if payload.as_of_date not in ALLOWED_CUTOFFS:
        raise HTTPException(status_code=422, detail="Unsupported cutoff")
    try:
        model, metadata = load_model()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Model unavailable") from exc
    snapshot_key = f"{payload.subscriber_key}|{payload.as_of_date}"
    backend = os.getenv("KKBOX_FEATURE_BACKEND", "feast")
    try:
        values = parquet_features(snapshot_key) if backend == "parquet" else feast_features(snapshot_key)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Feature store unavailable") from exc
    if values is None:
        raise HTTPException(status_code=404, detail="No feature snapshot for this ID and cutoff")
    vector = np.array([[np.nan if value is None else float(value) for value in values]], dtype=np.float32)
    probability = float(model.predict_proba(vector)[0, 1])
    risk_level = ("high" if probability >= metadata["risk_high_threshold"] else
                  "medium" if probability >= metadata["risk_medium_threshold"] else "low")
    return PredictionResponse(
        subscriber_key=payload.subscriber_key,
        as_of_date=payload.as_of_date,
        prediction=int(probability >= metadata["classification_threshold"]),
        churn_probability=round(probability, 6), risk_level=risk_level,
        model_version=str(metadata["model_version"]), feature_version=FEATURE_VERSION,
    )


@router.post("/v1/features", response_model=FeatureResponse)
def inspect_features(payload: PredictionRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    snapshot_key = f"{payload.subscriber_key}|{payload.as_of_date}"
    backend = os.getenv("KKBOX_FEATURE_BACKEND", "feast")
    try:
        values = parquet_features(snapshot_key) if backend == "parquet" else feast_features(snapshot_key)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Feature store unavailable") from exc
    if values is None:
        raise HTTPException(status_code=404, detail="No feature snapshot for this ID and cutoff")
    return FeatureResponse(subscriber_key=payload.subscriber_key, as_of_date=payload.as_of_date,
                           features=dict(zip(FEATURE_COLUMNS, values)),
                           missing_count=sum(value is None for value in values),
                           feature_version=FEATURE_VERSION)


@router.post("/v1/predictions/manual", response_model=ManualPredictionResponse)
def predict_manual(payload: ManualPredictionRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    try:
        model, metadata = load_model()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Model unavailable") from exc
    vector = np.array([[np.nan if payload.features[name] is None else payload.features[name]
                        for name in FEATURE_COLUMNS]], dtype=np.float32)
    probability = float(model.predict_proba(vector)[0, 1])
    risk_level = ("high" if probability >= metadata["risk_high_threshold"] else
                  "medium" if probability >= metadata["risk_medium_threshold"] else "low")
    return ManualPredictionResponse(prediction=int(probability >= metadata["classification_threshold"]),
                                    churn_probability=round(probability, 6), risk_level=risk_level,
                                    model_version=str(metadata["model_version"]),
                                    feature_version=FEATURE_VERSION)


@router.post("/v1/predictions/batch", response_model=BatchPredictionResponse)
def predict_batch(payload: BatchPredictionRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    results = []
    for row, item in enumerate(payload.items, start=1):
        try:
            result = predict(item, x_api_key)
            results.append(BatchPredictionItem(row=row, subscriber_key=item.subscriber_key,
                                               as_of_date=item.as_of_date, result=result))
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            results.append(BatchPredictionItem(row=row, subscriber_key=item.subscriber_key,
                                               as_of_date=item.as_of_date, error="No feature snapshot"))
    succeeded = sum(item.result is not None for item in results)
    return BatchPredictionResponse(total=len(results), succeeded=succeeded,
                                   failed=len(results) - succeeded, results=results)


@router.post("/v1/model/reload", include_in_schema=False)
def reload_champion(x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    load_model.cache_clear()
    try:
        _, metadata = load_model()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Champion model unavailable") from exc
    return {"status": "ready", "model_version": str(metadata["model_version"])}


app.include_router(router)
