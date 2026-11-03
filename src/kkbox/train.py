"""Train KKBox churn models on cutoff-safe snapshots and track them in MLflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import duckdb
import joblib
import mlflow
import mlflow.sklearn
import numpy as np
from mlflow.tracking import MlflowClient
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, confusion_matrix, f1_score, precision_recall_curve,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.kkbox.contract import FEATURE_COLUMNS, FEATURE_VERSION


def load_period(connection: duckdb.DuckDBPyConnection, pattern: str, period: str):
    columns = ", ".join(["subscriber_key", "is_churn", *FEATURE_COLUMNS])
    return connection.execute(
        f"SELECT {columns} FROM read_parquet(?, hive_partitioning=true) WHERE label_period = ?",
        [pattern, period],
    ).fetchdf()


def feature_matrix(frame):
    return frame[FEATURE_COLUMNS].to_numpy(dtype=np.float32, copy=True)


def metrics(y, probabilities, threshold: float) -> dict:
    predictions = (probabilities >= threshold).astype(np.int8)
    return {
        "roc_auc": round(float(roc_auc_score(y, probabilities)), 6),
        "pr_auc": round(float(average_precision_score(y, probabilities)), 6),
        "f1": round(float(f1_score(y, predictions)), 6),
        "confusion_matrix": confusion_matrix(y, predictions, labels=[0, 1]).tolist(),
    }


def f1_threshold(y, probabilities) -> float:
    precision, recall, thresholds = precision_recall_curve(y, probabilities)
    scores = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)
    return float(thresholds[int(np.argmax(scores))])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/kkbox_processed/features"))
    parser.add_argument("--etl-audit", type=Path, default=Path("docs/experiments/kkbox_etl_audit.json"))
    parser.add_argument("--output", type=Path, default=Path("data/kkbox_models"))
    parser.add_argument("--report", type=Path, default=Path("docs/experiments/kkbox_model_report.json"))
    parser.add_argument("--mode", choices=["pilot", "full"], default="pilot")
    args = parser.parse_args()

    audit = json.loads(args.etl_audit.read_text(encoding="utf-8"))
    if args.mode == "full" and (audit["status"] != "full_cohort" or not audit["complete_source"]):
        parser.error("Full model needs ETL audit proving all 32 files and 7.52 GB input")
    if args.mode == "pilot" and audit["status"] != "pilot":
        parser.error("Pilot mode requires pilot ETL output")
    pattern = str(args.features / "**" / "*.parquet")
    connection = duckdb.connect()
    connection.execute("SET memory_limit='3GB'")
    feb = load_period(connection, pattern, "2017-02")
    mar = load_period(connection, pattern, "2017-03")
    if len(feb) < 100 or len(mar) < 100:
        raise RuntimeError("Too few feature rows for train/test smoke run")
    if args.mode == "full" and (len(feb) != 992_931 or len(mar) != 970_960):
        raise RuntimeError("Full feature row counts do not match official labels")
    validation_mask = np.array([
        int.from_bytes(hashlib.blake2b(key.encode(), digest_size=8).digest(), "big") % 5 == 0
        for key in feb["subscriber_key"].astype(str)
    ])
    x_train = feature_matrix(feb.loc[~validation_mask])
    x_val = feature_matrix(feb.loc[validation_mask])
    x_test = feature_matrix(mar)
    y_train = feb.loc[~validation_mask, "is_churn"].to_numpy(dtype=np.int8)
    y_val = feb.loc[validation_mask, "is_churn"].to_numpy(dtype=np.int8)
    y_test = mar["is_churn"].to_numpy(dtype=np.int8)
    if any(len(np.unique(y)) < 2 for y in (y_train, y_val, y_test)):
        raise RuntimeError("Each split must contain both churn classes")

    args.output.mkdir(parents=True, exist_ok=True)
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{(args.output / 'mlflow.db').resolve().as_posix()}")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("KKBox_Churn_v1")
    candidates = {
        "logistic_regression": make_pipeline(
            SimpleImputer(strategy="constant", fill_value=-1, keep_empty_features=True),
            StandardScaler(), LogisticRegression(max_iter=500, class_weight="balanced")),
        "xgboost": make_pipeline(
            SimpleImputer(strategy="constant", fill_value=-1, keep_empty_features=True),
            XGBClassifier(n_estimators=180, max_depth=4, learning_rate=0.06,
                          subsample=0.8, colsample_bytree=0.8, tree_method="hist",
                          n_jobs=2, random_state=42, eval_metric="logloss")),
    }
    runs = {}
    for name, pipeline in candidates.items():
        with mlflow.start_run(run_name=f"{args.mode}-{name}") as run:
            mlflow.log_params({"algorithm": name, "mode": args.mode,
                               "feature_version": FEATURE_VERSION,
                               "source_revision": audit["source_revision_sha"]})
            pipeline.fit(x_train, y_train)
            probabilities = pipeline.predict_proba(x_val)[:, 1]
            threshold = f1_threshold(y_val, probabilities)
            val_metrics = metrics(y_val, probabilities, threshold)
            mlflow.log_metrics({f"validation_{key}": value for key, value in val_metrics.items()
                                if isinstance(value, float)})
            model_info = mlflow.sklearn.log_model(
                pipeline, artifact_path="model", serialization_format="cloudpickle")
            runs[name] = {"pipeline": pipeline, "run_id": run.info.run_id,
                          "model_uri": model_info.model_uri,
                          "threshold": threshold, "validation": val_metrics}

    winner_name = max(runs, key=lambda name: runs[name]["validation"]["pr_auc"])
    winner = runs[winner_name]
    test_probabilities = winner["pipeline"].predict_proba(x_test)[:, 1]
    test_metrics = metrics(y_test, test_probabilities, winner["threshold"])
    val_probabilities = winner["pipeline"].predict_proba(x_val)[:, 1]
    risk_medium, risk_high = (float(value) for value in np.quantile(val_probabilities, [0.5, 0.9]))
    model_version = f"pilot-{winner['run_id'][:8]}"
    if args.mode == "full":
        registered = mlflow.register_model(winner["model_uri"], "KKBoxChurn")
        client = MlflowClient()
        version_tags = {
            "feature_version": FEATURE_VERSION,
            "source_revision_sha": audit["source_revision_sha"],
            "classification_threshold": str(winner["threshold"]),
            "risk_medium_threshold": str(risk_medium),
            "risk_high_threshold": str(risk_high),
        }
        for key, value in version_tags.items():
            client.set_model_version_tag("KKBoxChurn", registered.version, key, value)
        client.set_registered_model_alias("KKBoxChurn", "champion", registered.version)
        model_version = registered.version
    artifact_name = "pilot_model.joblib" if args.mode == "pilot" else "champion_model.joblib"
    joblib.dump(winner["pipeline"], args.output / artifact_name)
    report = {
        "mode": args.mode, "model": winner_name, "model_version": model_version,
        "mlflow_run_id": winner["run_id"], "feature_version": FEATURE_VERSION,
        "source_revision_sha": audit["source_revision_sha"],
        "feature_columns": FEATURE_COLUMNS,
        "classification_threshold": winner["threshold"],
        "risk_medium_threshold": risk_medium, "risk_high_threshold": risk_high,
        "train_rows": len(y_train), "validation_rows": len(y_val), "test_rows": len(y_test),
        "candidate_validation": {name: run["validation"] for name, run in runs.items()},
        "test": test_metrics,
        "warning": "Pilot metrics are a plumbing smoke test on incomplete source history; do not report as final accuracy."
        if args.mode == "pilot" else None,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.output / "model_metadata.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("mode", "model", "model_version", "train_rows", "validation_rows", "test_rows")}, indent=2))


if __name__ == "__main__":
    main()
