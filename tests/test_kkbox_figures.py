"""Axis 8B: KKBox SVG Figure Rendering & Full/Pilot Evidence Validation Gates."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scripts import kkbox_make_figures


def _sample_reports(mode: str = "pilot", drift_mode: str | None = None, rev: str = "a" * 40) -> tuple[dict, dict, dict]:
    is_full = mode == "full"
    audit = {
        "status": "full_cohort" if is_full else "pilot",
        "complete_source": is_full,
        "input_file_count": 32 if is_full else 5,
        "input_bytes": 7_522_254_856 if is_full else 945_273_421,
        "source_revision_sha": rev,
    }
    model = {
        "mode": mode,
        "model": "xgboost",
        "model_version": "1" if is_full else "pilot-test",
        "source_revision_sha": rev,
        "test_rows": 970_960 if is_full else 48_803,
        "candidate_validation": {
            "xgboost": {"pr_auc": 0.6421},
            "logistic_regression": {"pr_auc": 0.4812},
        },
        "test": {
            "pr_auc": 0.6105,
            "roc_auc": 0.9123,
            "positive_rate": 0.0892,
            "confusion_matrix": [[850_000, 34_000], [25_000, 61_960]],
        },
        "test_pr_curve": {
            "recall": [0.0, 0.5, 1.0],
            "precision": [1.0, 0.65, 0.0892],
        },
    }
    drift = {
        "mode": drift_mode or ("full_cohort" if is_full else "pilot"),
        "source_revision_sha": rev,
        "flagged_features": ["paid_amount_30d"],
        "features": {
            "paid_amount_30d": {"psi": 0.312, "drift_flag": True},
            "txn_count_30d": {"psi": 0.045, "drift_flag": False},
        },
    }
    return audit, model, drift


def test_figures_validation_gates_reject_pilot_and_incomplete_full() -> None:
    audit_p, model_p, drift_p = _sample_reports(mode="pilot")

    # Pilot refused without --allow-pilot
    with pytest.raises(ValueError, match="Pilot reports cannot be rendered as final figures"):
        kkbox_make_figures.validate(audit_p, model_p, drift_p, allow_pilot=False)

    assert kkbox_make_figures.validate(audit_p, model_p, drift_p, allow_pilot=True) is True

    # Mode mismatch between model ("full") and drift ("pilot")
    audit_f, model_f, drift_f = _sample_reports(mode="full", drift_mode="pilot")
    with pytest.raises(ValueError, match="Model and drift modes differ"):
        kkbox_make_figures.validate(audit_f, model_f, drift_f, allow_pilot=False)

    # Full mode with drift_mode="full_cohort" (as emitted by src/kkbox/drift.py) succeeds
    audit_f, model_f, drift_fc = _sample_reports(mode="full", drift_mode="full_cohort")
    assert kkbox_make_figures.validate(audit_f, model_f, drift_fc, allow_pilot=False) is False

    # Revision SHA mismatch
    with pytest.raises(ValueError, match="Source revisions differ"):
        kkbox_make_figures.validate(audit_f, model_f, {**drift_fc, "source_revision_sha": "b" * 40}, allow_pilot=False)

    # Full mode rejected when input_file_count != 32 or input_bytes < 4 GB
    with pytest.raises(ValueError, match="ETL audit does not prove full >4 GB processing"):
        kkbox_make_figures.validate({**audit_f, "input_file_count": 31}, model_f, drift_fc, allow_pilot=False)
    with pytest.raises(ValueError, match="ETL audit does not prove full >4 GB processing"):
        kkbox_make_figures.validate({**audit_f, "input_bytes": 1_000_000}, model_f, drift_fc, allow_pilot=False)


def test_make_figures_cli_renders_valid_svg_in_pilot_and_full_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_files = (
        "kkbox_model_comparison.svg",
        "kkbox_confusion_matrix.svg",
        "kkbox_pr_curve.svg",
        "kkbox_drift.svg",
    )

    # 1. Pilot mode with --allow-pilot includes watermark
    audit_p, model_p, drift_p = _sample_reports(mode="pilot")
    p_dir = tmp_path / "pilot_inputs"
    p_dir.mkdir()
    (p_dir / "audit.json").write_text(json.dumps(audit_p), encoding="utf-8")
    (p_dir / "model.json").write_text(json.dumps(model_p), encoding="utf-8")
    (p_dir / "drift.json").write_text(json.dumps(drift_p), encoding="utf-8")
    p_out = tmp_path / "pilot_figs"

    monkeypatch.setattr(
        "sys.argv",
        [
            "kkbox_make_figures.py",
            "--etl-audit", str(p_dir / "audit.json"),
            "--model-report", str(p_dir / "model.json"),
            "--drift-report", str(p_dir / "drift.json"),
            "--output-dir", str(p_out),
            "--allow-pilot",
        ],
    )
    kkbox_make_figures.main()
    for name in expected_files:
        svg_text = (p_out / name).read_text(encoding="utf-8")
        assert "PILOT / INCOMPLETE SOURCE" in svg_text
        ET.fromstring(svg_text)

    # 2. Full mode without --allow-pilot renders clean unwatermarked SVGs
    audit_f, model_f, drift_f = _sample_reports(mode="full", drift_mode="full_cohort")
    f_dir = tmp_path / "full_inputs"
    f_dir.mkdir()
    (f_dir / "audit.json").write_text(json.dumps(audit_f), encoding="utf-8")
    (f_dir / "model.json").write_text(json.dumps(model_f), encoding="utf-8")
    (f_dir / "drift.json").write_text(json.dumps(drift_f), encoding="utf-8")
    f_out = tmp_path / "full_figs"

    monkeypatch.setattr(
        "sys.argv",
        [
            "kkbox_make_figures.py",
            "--etl-audit", str(f_dir / "audit.json"),
            "--model-report", str(f_dir / "model.json"),
            "--drift-report", str(f_dir / "drift.json"),
            "--output-dir", str(f_out),
        ],
    )
    kkbox_make_figures.main()
    for name in expected_files:
        svg_text = (f_out / name).read_text(encoding="utf-8")
        assert "PILOT / INCOMPLETE SOURCE" not in svg_text
        ET.fromstring(svg_text)
