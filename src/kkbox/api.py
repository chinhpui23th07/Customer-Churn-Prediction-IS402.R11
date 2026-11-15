"""Historical KKBox churn API using the same feature columns as training."""

from __future__ import annotations

import hmac
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import duckdb
import joblib
import numpy as np
from fastapi import APIRouter, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.kkbox.contract import ALLOWED_CUTOFFS, FEATURE_COLUMNS, FEATURE_VERSION
from src.kkbox.feast_config import build_feature_store
from src.kkbox.schemas import (
    BatchPredictionItem,
    BatchPredictionRequest,
    BatchPredictionResponse,
    FeatureResponse,
    ManualPredictionRequest,
    ManualPredictionResponse,
    MAX_UINT64,
    PredictionRequest,
    PredictionResponse,
)
from src.resilience import CircuitBreaker, CircuitBreakerOpenException

MODEL_DIR = Path(os.getenv("KKBOX_MODEL_DIR", "data/kkbox_models"))
FEATURE_PATH = os.getenv("KKBOX_FEATURE_PATH", "data/kkbox_processed/features/**/*.parquet")
FEAST_REPO = os.getenv("KKBOX_FEAST_REPO", "data/kkbox_feast")

feature_circuit_breaker = CircuitBreaker(
    name="kkbox_feature_store",
    failure_threshold=int(os.getenv("KKBOX_CB_FAILURE_THRESHOLD", "5")),
    recovery_timeout=float(os.getenv("KKBOX_CB_RECOVERY_TIMEOUT", "30.0")),
)
model_circuit_breaker = CircuitBreaker(
    name="kkbox_model_inference",
    failure_threshold=int(os.getenv("KKBOX_CB_FAILURE_THRESHOLD", "5")),
    recovery_timeout=float(os.getenv("KKBOX_CB_RECOVERY_TIMEOUT", "30.0")),
)


def reset_circuit_breakers() -> None:
    feature_circuit_breaker.reset()
    model_circuit_breaker.reset()


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
    pattern = FEATURE_PATH
    if (
        os.getenv("KKBOX_ALLOW_PILOT") == "1"
        and pattern == "data/kkbox_processed/features/**/*.parquet"
        and not Path("data/kkbox_processed/features").exists()
        and Path("data/kkbox_processed/pilot_features").exists()
    ):
        pattern = "data/kkbox_processed/pilot_features/**/*.parquet"
    connection = duckdb.connect()
    try:
        columns = ", ".join(FEATURE_COLUMNS)
        rows = connection.execute(
            f"SELECT {columns} FROM read_parquet(?, hive_partitioning=true) WHERE snapshot_key = ? LIMIT 2",
            [pattern, snapshot_key],
        ).fetchall()
        if len(rows) > 1:
            raise RuntimeError("Duplicate snapshot key in processed feature output")
        return list(rows[0]) if rows else None
    finally:
        connection.close()


@lru_cache(maxsize=1)
def feast_store():
    return build_feature_store(FEAST_REPO)


def feast_features(snapshot_key: str) -> list[float | None] | None:
    features = [f"kkbox_churn_features:{name}" for name in FEATURE_COLUMNS]
    result = feast_store().get_online_features(
        features=features, entity_rows=[{"snapshot_key": snapshot_key}]
    ).to_dict()
    values = [result.get(name, result.get(f"kkbox_churn_features:{name}", [None]))[0]
              for name in FEATURE_COLUMNS]
    return None if all(value is None for value in values) else values


def _get_features(snapshot_key: str, backend: str) -> list[float | None] | None:
    return parquet_features(snapshot_key) if backend == "parquet" else feast_features(snapshot_key)


router = APIRouter(tags=["KKBox Churn Serving"])
WEB_DIR = Path(__file__).resolve().parent / "web"


def require_api_key(value: str | None) -> None:
    configured_key = os.getenv("KKBOX_API_KEY")
    if not configured_key:
        raise HTTPException(
            status_code=503, detail="API secret is not configured", headers={"Content-Type": "application/problem+json"}
        )
    if not value or not hmac.compare_digest(value, configured_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


def require_admin_key(value: str | None) -> None:
    configured_key = os.getenv("KKBOX_ADMIN_API_KEY")
    if not configured_key and os.getenv("KKBOX_ALLOW_PILOT") == "1":
        configured_key = os.getenv("KKBOX_API_KEY")
    if not configured_key:
        raise HTTPException(
            status_code=503, detail="Admin API secret is not configured", headers={"Content-Type": "application/problem+json"}
        )
    if not value or not hmac.compare_digest(value, configured_key):
        raise HTTPException(status_code=401, detail="Invalid admin API key")


def _degraded_prediction(key: str, cutoff: str, metadata: dict[str, Any] | None = None) -> PredictionResponse:
    threshold = float(metadata.get("classification_threshold", 0.5)) if metadata else 0.5
    version = str(metadata.get("model_version", "fallback-degraded")) if metadata else "fallback-degraded"
    return PredictionResponse(
        subscriber_key=key,
        as_of_date=cutoff,
        prediction=int(0.5 >= threshold),
        churn_probability=0.5,
        risk_level="medium",
        model_version=version,
        feature_version=FEATURE_VERSION,
        fallback=True,
    )


@router.get("/demo", include_in_schema=False)
def demo():
    return FileResponse(WEB_DIR / "index.html")


app = FastAPI(title="KKBox Customer Churn API", version="1.0.0")
app.mount("/demo/assets", StaticFiles(directory=WEB_DIR), name="kkbox-demo-assets")


@router.get("/v1/health")
@app.get("/health")
def health():
    try:
        _, metadata = load_model()
        return {"status": "ready", "model_version": str(metadata["model_version"]),
                "mode": metadata["mode"]}
    except Exception:
        return {"status": "degraded", "reason": "Model unavailable"}


@router.get("/v1/resilience/status")
def resilience_status():
    return {
        "feature_store": feature_circuit_breaker.get_metrics(),
        "model_inference": model_circuit_breaker.get_metrics(),
    }



@router.post("/v1/predictions", response_model=PredictionResponse)
def predict(payload: PredictionRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    if payload.as_of_date not in ALLOWED_CUTOFFS:
        raise HTTPException(status_code=422, detail="Unsupported cutoff")
    try:
        model, metadata = load_model()
    except Exception as exc:
        if os.getenv("KKBOX_ENABLE_FALLBACK", "0") == "1":
            return _degraded_prediction(payload.subscriber_key, payload.as_of_date)
        raise HTTPException(
            status_code=503, detail="Model unavailable", headers={"Content-Type": "application/problem+json"}
        ) from exc

    snapshot_key = f"{payload.subscriber_key}|{payload.as_of_date}"
    backend = os.getenv("KKBOX_FEATURE_BACKEND", "feast")
    try:
        values = feature_circuit_breaker.call(_get_features, snapshot_key, backend)
    except CircuitBreakerOpenException as exc:
        if os.getenv("KKBOX_ENABLE_FALLBACK", "0") == "1":
            return _degraded_prediction(payload.subscriber_key, payload.as_of_date, metadata)
        raise HTTPException(
            status_code=503, detail=f"Circuit breaker open: {exc}", headers={"Content-Type": "application/problem+json"}
        ) from exc
    except Exception as exc:
        if os.getenv("KKBOX_ENABLE_FALLBACK", "0") == "1":
            return _degraded_prediction(payload.subscriber_key, payload.as_of_date, metadata)
        raise HTTPException(
            status_code=503, detail="Feature store unavailable", headers={"Content-Type": "application/problem+json"}
        ) from exc

    if values is None:
        raise HTTPException(status_code=404, detail="No feature snapshot for this ID and cutoff")

    vector = np.array([[np.nan if value is None else float(value) for value in values]], dtype=np.float32)
    try:
        proba = model_circuit_breaker.call(model.predict_proba, vector)
        probability = float(proba[0, 1])
    except CircuitBreakerOpenException as exc:
        if os.getenv("KKBOX_ENABLE_FALLBACK", "0") == "1":
            return _degraded_prediction(payload.subscriber_key, payload.as_of_date, metadata)
        raise HTTPException(
            status_code=503, detail=f"Circuit breaker open: {exc}", headers={"Content-Type": "application/problem+json"}
        ) from exc
    except Exception as exc:
        if os.getenv("KKBOX_ENABLE_FALLBACK", "0") == "1":
            return _degraded_prediction(payload.subscriber_key, payload.as_of_date, metadata)
        raise HTTPException(
            status_code=503, detail="Model inference unavailable", headers={"Content-Type": "application/problem+json"}
        ) from exc

    risk_level = ("high" if probability >= metadata["risk_high_threshold"] else
                  "medium" if probability >= metadata["risk_medium_threshold"] else "low")
    return PredictionResponse(
        subscriber_key=payload.subscriber_key,
        as_of_date=payload.as_of_date,
        prediction=int(probability >= metadata["classification_threshold"]),
        churn_probability=round(probability, 6),
        risk_level=risk_level,
        model_version=str(metadata["model_version"]),
        feature_version=FEATURE_VERSION,
        fallback=False,
    )


@router.post("/v1/features", response_model=FeatureResponse)
def inspect_features(payload: PredictionRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    snapshot_key = f"{payload.subscriber_key}|{payload.as_of_date}"
    backend = os.getenv("KKBOX_FEATURE_BACKEND", "feast")
    try:
        values = feature_circuit_breaker.call(_get_features, snapshot_key, backend)
    except CircuitBreakerOpenException as exc:
        raise HTTPException(
            status_code=503, detail=f"Circuit breaker open: {exc}", headers={"Content-Type": "application/problem+json"}
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Feature store unavailable", headers={"Content-Type": "application/problem+json"}
        ) from exc
    if values is None:
        raise HTTPException(status_code=404, detail="No feature snapshot for this ID and cutoff")
    return FeatureResponse(
        subscriber_key=payload.subscriber_key,
        as_of_date=payload.as_of_date,
        features=dict(zip(FEATURE_COLUMNS, values)),
        missing_count=sum(value is None for value in values),
        feature_version=FEATURE_VERSION,
    )


@router.post("/v1/predictions/manual", response_model=ManualPredictionResponse)
def predict_manual(payload: ManualPredictionRequest, x_api_key: str | None = Header(default=None)):
    require_api_key(x_api_key)
    try:
        model, metadata = load_model()
    except Exception as exc:
        if os.getenv("KKBOX_ENABLE_FALLBACK", "0") == "1":
            return ManualPredictionResponse(
                prediction=1, churn_probability=0.5, risk_level="medium",
                model_version="fallback-degraded", feature_version=FEATURE_VERSION, fallback=True,
            )
        raise HTTPException(
            status_code=503, detail="Model unavailable", headers={"Content-Type": "application/problem+json"}
        ) from exc

    vector = np.array([[np.nan if payload.features[name] is None else payload.features[name]
                        for name in FEATURE_COLUMNS]], dtype=np.float32)
    try:
        proba = model_circuit_breaker.call(model.predict_proba, vector)
        probability = float(proba[0, 1])
    except CircuitBreakerOpenException as exc:
        if os.getenv("KKBOX_ENABLE_FALLBACK", "0") == "1":
            threshold = float(metadata.get("classification_threshold", 0.5))
            return ManualPredictionResponse(
                prediction=int(0.5 >= threshold), churn_probability=0.5, risk_level="medium",
                model_version=str(metadata["model_version"]), feature_version=FEATURE_VERSION, fallback=True,
            )
        raise HTTPException(
            status_code=503, detail=f"Circuit breaker open: {exc}", headers={"Content-Type": "application/problem+json"}
        ) from exc
    except Exception as exc:
        if os.getenv("KKBOX_ENABLE_FALLBACK", "0") == "1":
            threshold = float(metadata.get("classification_threshold", 0.5))
            return ManualPredictionResponse(
                prediction=int(0.5 >= threshold), churn_probability=0.5, risk_level="medium",
                model_version=str(metadata["model_version"]), feature_version=FEATURE_VERSION, fallback=True,
            )
        raise HTTPException(
            status_code=503, detail="Model unavailable", headers={"Content-Type": "application/problem+json"}
        ) from exc

    risk_level = ("high" if probability >= metadata["risk_high_threshold"] else
                  "medium" if probability >= metadata["risk_medium_threshold"] else "low")
    return ManualPredictionResponse(
        prediction=int(probability >= metadata["classification_threshold"]),
        churn_probability=round(probability, 6),
        risk_level=risk_level,
        model_version=str(metadata["model_version"]),
        feature_version=FEATURE_VERSION,
        fallback=False,
    )


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
    require_admin_key(x_api_key)
    load_model.cache_clear()
    reset_circuit_breakers()
    try:
        _, metadata = load_model()
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Champion model unavailable", headers={"Content-Type": "application/problem+json"}
        ) from exc
    return {"status": "ready", "model_version": str(metadata["model_version"])}


app.include_router(router)
