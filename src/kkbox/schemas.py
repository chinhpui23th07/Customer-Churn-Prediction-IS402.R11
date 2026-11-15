"""Pydantic schemas and contracts for KKBox churn serving API."""

from __future__ import annotations

import math
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

from src.kkbox.contract import FEATURE_COLUMNS

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
    fallback: bool = False


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
    fallback: bool = False


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
