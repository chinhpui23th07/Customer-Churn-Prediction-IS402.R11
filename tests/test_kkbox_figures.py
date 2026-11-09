"""Final evidence figures must reject pilot or mismatched aggregate reports."""

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.kkbox_make_figures import validate
from src.kkbox.train import metrics, pr_curve_points


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "docs" / "experiments" / name).read_text(encoding="utf-8"))


def test_pilot_cannot_be_rendered_as_final():
    audit = load("kkbox_pilot_etl_audit.json")
    model = load("kkbox_pilot_model_report.json")
    drift = load("kkbox_pilot_drift_report.json")
    with pytest.raises(ValueError, match="Pilot reports cannot"):
        validate(audit, model, drift, False)
    assert validate(audit, model, drift, True) is True
    drift["source_revision_sha"] = "wrong-revision"
    with pytest.raises(ValueError, match="Source revisions differ"):
        validate(audit, model, drift, True)


def test_pr_curve_and_baseline_are_derived_from_predictions():
    labels = np.array([0, 0, 1, 1])
    probabilities = np.array([0.1, 0.4, 0.7, 0.9])
    curve = pr_curve_points(labels, probabilities, max_points=3)
    result = metrics(labels, probabilities, 0.5)
    assert curve["display_points"] <= 3
    assert len(curve["recall"]) == len(curve["precision"])
    assert result["positive_rate"] == 0.5
    assert result["precision"] == 1
    assert result["recall"] == 1
