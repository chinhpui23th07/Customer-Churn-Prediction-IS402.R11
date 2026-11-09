"""Axes 3 & 4: KKBox Time-Based Split, LR vs XGBoost Training, MLflow Registry & Feast Online/Offline Store."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from feast import FeatureView, FileSource
from mlflow.tracking import MlflowClient

from data.kkbox_feast import definitions as feast_defs
from src.kkbox import prepare_feast, train
from src.kkbox.contract import FEATURE_COLUMNS, FEATURE_VERSION


def _build_synthetic_period_df(period: str, cutoff: str, count: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    keys = [str(10_000_000 + i) for i in range(count)]
    y = np.array([i % 2 for i in range(count)], dtype=np.int64)
    data: dict[str, object] = {
        "subscriber_key": keys,
        "label_period": [period] * count,
        "as_of_date": [cutoff] * count,
        "snapshot_key": [f"{k}|{cutoff}" for k in keys],
        "is_churn": y,
        "txn_count_30d": rng.integers(0, 5, size=count, dtype=np.int32),
        "paid_amount_30d": (y * 100.0 + rng.uniform(0, 50, size=count)).astype(np.float64),
        "cancel_count_90d": y.astype(np.int32),
        "days_since_last_txn": [None if (i + 1) % 11 == 0 else int(rng.integers(1, 25)) for i in range(count)],
        "last_auto_renew": [None if (i + 1) % 11 == 0 else int(1 - y[i]) for i in range(count)],
        "days_until_expiry": [None if (i + 1) % 11 == 0 else int(rng.integers(-10, 30)) for i in range(count)],
        "active_days_30d": rng.integers(0, 30, size=count, dtype=np.int32),
        "listening_secs_30d": ((1 - y) * 3000.0 + rng.uniform(0, 500, size=count)).astype(np.float64),
        "days_since_last_listen": [None if (i + 1) % 13 == 0 else int(rng.integers(0, 15)) for i in range(count)],
        "registration_tenure_days": [None if (i + 1) % 17 == 0 else int(rng.integers(30, 1000)) for i in range(count)],
        "has_txn_history": [0 if (i + 1) % 11 == 0 else 1 for i in range(count)],
        "has_listening_history": [0 if (i + 1) % 13 == 0 else 1 for i in range(count)],
    }
    return pd.DataFrame(data)


def _write_hive_features(root: Path, feb_df: pd.DataFrame, mar_df: pd.DataFrame) -> Path:
    for period, df in (("2017-02", feb_df), ("2017-03", mar_df)):
        part_dir = root / f"label_period={period}"
        part_dir.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(df.drop(columns=["label_period"]), preserve_index=False), part_dir / "part.parquet")
    return root


def test_train_helper_metrics_pr_curve_and_f1_threshold() -> None:
    y = np.array([0, 0, 0, 1, 1, 1], dtype=np.int8)
    probs = np.array([0.05, 0.15, 0.35, 0.65, 0.85, 0.95], dtype=np.float64)

    thresh = train.f1_threshold(y, probs)
    assert 0.35 < thresh <= 0.65

    m = train.metrics(y, probs, thresh)
    assert m["roc_auc"] == 1.0
    assert m["pr_auc"] == 1.0
    assert m["f1"] == 1.0
    assert m["confusion_matrix"] == [[3, 0], [0, 3]]

    curve = train.pr_curve_points(y, probs, max_points=4)
    assert curve["display_points"] <= 4
    assert curve["source_points"] == len(probs) + 1
    assert len(curve["recall"]) == len(curve["precision"])


def test_train_cli_guards_audit_row_counts_and_class_balance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feat_root = tmp_path / "features"
    feb_df = _build_synthetic_period_df("2017-02", "2017-01-31", 140, seed=1)
    mar_df = _build_synthetic_period_df("2017-03", "2017-02-28", 140, seed=2)
    _write_hive_features(feat_root, feb_df, mar_df)

    pilot_audit = tmp_path / "pilot_audit.json"
    pilot_audit.write_text(
        json.dumps({"status": "pilot", "complete_source": False, "source_revision_sha": "a" * 40}),
        encoding="utf-8",
    )
    full_audit = tmp_path / "full_audit.json"
    full_audit.write_text(
        json.dumps({"status": "full_cohort", "complete_source": True, "source_revision_sha": "a" * 40}),
        encoding="utf-8",
    )

    # 1. Full mode rejected on pilot audit
    monkeypatch.setattr(
        "sys.argv",
        ["train.py", "--features", str(feat_root), "--etl-audit", str(pilot_audit), "--mode", "full"],
    )
    with pytest.raises(SystemExit) as exc_full_on_pilot:
        train.main()
    assert exc_full_on_pilot.value.code == 2

    # 2. Pilot mode rejected on full audit
    monkeypatch.setattr(
        "sys.argv",
        ["train.py", "--features", str(feat_root), "--etl-audit", str(full_audit), "--mode", "pilot"],
    )
    with pytest.raises(SystemExit) as exc_pilot_on_full:
        train.main()
    assert exc_pilot_on_full.value.code == 2

    # 3. Full mode rejected when row counts != (992_931, 970_960)
    monkeypatch.setattr(
        "sys.argv",
        ["train.py", "--features", str(feat_root), "--etl-audit", str(full_audit), "--mode", "full"],
    )
    with pytest.raises(RuntimeError, match="Full feature row counts do not match official labels"):
        train.main()

    # 4. Single-class split rejected
    one_class_root = tmp_path / "features_one_class"
    feb_zero = feb_df.copy()
    feb_zero["is_churn"] = 0
    _write_hive_features(one_class_root, feb_zero, mar_df)
    monkeypatch.setattr(
        "sys.argv",
        ["train.py", "--features", str(one_class_root), "--etl-audit", str(pilot_audit), "--mode", "pilot"],
    )
    with pytest.raises(RuntimeError, match="Each split must contain both churn classes"):
        train.main()

    # 5. Too few rows (< 100) rejected
    tiny_root = tmp_path / "features_tiny"
    _write_hive_features(tiny_root, feb_df.iloc[:50], mar_df.iloc[:50])
    monkeypatch.setattr(
        "sys.argv",
        ["train.py", "--features", str(tiny_root), "--etl-audit", str(pilot_audit), "--mode", "pilot"],
    )
    with pytest.raises(RuntimeError, match="Too few feature rows"):
        train.main()


def test_train_pilot_end_to_end_pipeline_and_mlflow_logging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feat_root = tmp_path / "features"
    feb_df = _build_synthetic_period_df("2017-02", "2017-01-31", 160, seed=10)
    mar_df = _build_synthetic_period_df("2017-03", "2017-02-28", 120, seed=20)
    _write_hive_features(feat_root, feb_df, mar_df)

    audit_path = tmp_path / "audit.json"
    rev_sha = "a0f48c28e392e9a60d4d6fc62f1bbf3d848277d3"
    audit_path.write_text(
        json.dumps({"status": "pilot", "complete_source": False, "source_revision_sha": rev_sha}),
        encoding="utf-8",
    )
    out_dir = tmp_path / "models"
    report_path = tmp_path / "model_report.json"
    db_uri = f"sqlite:///{(out_dir / 'mlflow.db').resolve().as_posix()}"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", db_uri)
    monkeypatch.setattr(
        "sys.argv",
        [
            "train.py",
            "--features", str(feat_root),
            "--etl-audit", str(audit_path),
            "--output", str(out_dir),
            "--report", str(report_path),
            "--mode", "pilot",
        ],
    )
    train.main()

    assert (out_dir / "pilot_model.joblib").exists()
    assert (out_dir / "model_metadata.json").exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "pilot"
    assert report["model"] in {"logistic_regression", "xgboost"}
    assert report["model_version"].startswith("pilot-")
    assert report["feature_version"] == FEATURE_VERSION
    assert report["source_revision_sha"] == rev_sha
    assert report["feature_columns"] == FEATURE_COLUMNS
    assert report["train_rows"] + report["validation_rows"] == 160
    assert report["test_rows"] == 120
    assert set(report["candidate_validation"].keys()) == {"logistic_regression", "xgboost"}
    assert report["warning"] is not None

    # Verify deterministic blake2b validation split count
    expected_val = sum(
        int.from_bytes(hashlib.blake2b(k.encode(), digest_size=8).digest(), "big") % 5 == 0
        for k in feb_df["subscriber_key"]
    )
    assert report["validation_rows"] == expected_val


def test_feast_definitions_and_prepare_feast_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert feast_defs.snapshot.name == "snapshot_key"
    assert feast_defs.feature_view.name == "kkbox_churn_features"
    schema_names = [field.name for field in feast_defs.feature_view.schema]
    assert len(schema_names) == 12
    assert set(schema_names) == set(FEATURE_COLUMNS)

    feat_root = tmp_path / "features"
    feb_df = _build_synthetic_period_df("2017-02", "2017-01-31", 15, seed=7)
    mar_df = _build_synthetic_period_df("2017-03", "2017-02-28", 10, seed=8)
    _write_hive_features(feat_root, feb_df, mar_df)

    repo_dir = tmp_path / "kkbox_feast"
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "feature_store.yaml").write_text(
        Path("data/kkbox_feast/feature_store.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    temp_source = FileSource(
        name="kkbox_feature_source",
        path=(repo_dir / "churn_features.parquet").as_posix(),
        timestamp_field="event_timestamp",
    )
    temp_fv = FeatureView(
        name="kkbox_churn_features",
        entities=[feast_defs.snapshot],
        ttl=None,
        online=True,
        offline=True,
        source=temp_source,
        schema=feast_defs.feature_view.schema,
    )
    monkeypatch.setattr(feast_defs, "source", temp_source)
    monkeypatch.setattr(feast_defs, "feature_view", temp_fv)

    report_path = tmp_path / "feast_report.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepare_feast.py",
            "--features", str(feat_root),
            "--repo", str(repo_dir),
            "--report", str(report_path),
        ],
    )
    prepare_feast.main()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["rows"] == 25
    assert report["unique_snapshot_keys"] == 25
    assert report["online_write_rows"] == 25
    assert report["online_lookup_populated_features"] >= 8
    assert report["historical_lookup_rows"] == 1
    assert report["feature_count"] == 12
    assert (repo_dir / "data" / "online_store.db").exists()
    assert (repo_dir / "data" / "registry.db").exists()

    # Verify duplicate snapshot_key rejection in prepare_feast
    dup_root = tmp_path / "features_dup"
    dup_df = pd.concat([feb_df.iloc[:5], feb_df.iloc[:5]], ignore_index=True)
    _write_hive_features(dup_root, dup_df, mar_df.iloc[:5])
    monkeypatch.setattr(
        "sys.argv",
        ["prepare_feast.py", "--features", str(dup_root), "--repo", str(repo_dir), "--report", str(report_path)],
    )
    with pytest.raises(RuntimeError, match="Feast source contains duplicate snapshot keys"):
        prepare_feast.main()
