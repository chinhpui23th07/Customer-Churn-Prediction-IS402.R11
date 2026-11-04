"""Compare cutoff-safe KKBox feature distributions across the two label periods."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import ks_2samp

from src.kkbox.contract import FEATURE_COLUMNS, FEATURE_VERSION


def population_stability_index(reference: np.ndarray, current: np.ndarray) -> float | None:
    """PSI using bins learned only from the reference distribution."""
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    reference = reference[np.isfinite(reference)]
    current = current[np.isfinite(current)]
    if not len(reference) or not len(current):
        return None
    unique = np.unique(reference)
    if len(unique) == 1:
        value = unique[0]
        edges = np.array([-np.inf, np.nextafter(value, -np.inf),
                          np.nextafter(value, np.inf), np.inf])
    elif len(unique) <= 10:
        edges = np.r_[-np.inf, (unique[:-1] + unique[1:]) / 2, np.inf]
    else:
        edges = np.r_[-np.inf, np.unique(np.quantile(reference, np.linspace(0, 1, 11)))[1:-1], np.inf]
    ref_counts = np.histogram(reference, bins=edges)[0]
    cur_counts = np.histogram(current, bins=edges)[0]
    ref_share = np.maximum(ref_counts / len(reference), 1e-6)
    cur_share = np.maximum(cur_counts / len(current), 1e-6)
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def compare_feature(reference: np.ndarray, current: np.ndarray) -> dict:
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    valid_ref = reference[np.isfinite(reference)]
    valid_cur = current[np.isfinite(current)]
    psi = population_stability_index(valid_ref, valid_cur)
    ks = ks_2samp(valid_ref, valid_cur, method="asymp") if len(valid_ref) and len(valid_cur) else None
    ref_missing = 1 - len(valid_ref) / len(reference)
    cur_missing = 1 - len(valid_cur) / len(current)
    return {
        "reference_non_null": len(valid_ref), "current_non_null": len(valid_cur),
        "reference_missing_rate": round(ref_missing, 6),
        "current_missing_rate": round(cur_missing, 6),
        "missing_rate_delta": round(cur_missing - ref_missing, 6),
        "psi": round(psi, 6) if psi is not None else None,
        "ks_statistic": round(float(ks.statistic), 6) if ks is not None else None,
        "ks_p_value": float(ks.pvalue) if ks is not None else None,
        "drift_flag": bool((psi is not None and psi >= 0.2)
                           or abs(cur_missing - ref_missing) >= 0.05),
    }


def load_period(connection: duckdb.DuckDBPyConnection, pattern: str, period: str, cap: int):
    columns = ", ".join(FEATURE_COLUMNS)
    return connection.execute(
        f"SELECT {columns} FROM read_parquet(?, hive_partitioning=true) "
        "WHERE label_period = ? ORDER BY hash(snapshot_key) LIMIT ?",
        [pattern, period, cap],
    ).fetchdf()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/kkbox_processed/features"))
    parser.add_argument("--audit", type=Path, default=Path("docs/experiments/kkbox_etl_audit.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/experiments/kkbox_drift_report.json"))
    parser.add_argument("--sample-cap", type=int, default=100_000)
    parser.add_argument("--require-full", action="store_true")
    args = parser.parse_args()
    if args.sample_cap < 100:
        parser.error("--sample-cap must be at least 100")
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    if args.require_full and (audit["status"] != "full_cohort" or not audit["complete_source"]):
        parser.error("Full drift report requires a complete-source ETL audit")
    connection = duckdb.connect()
    pattern = str(args.features / "**" / "*.parquet")
    reference = load_period(connection, pattern, "2017-02", args.sample_cap)
    current = load_period(connection, pattern, "2017-03", args.sample_cap)
    if len(reference) < 100 or len(current) < 100:
        raise RuntimeError("Need at least 100 snapshots in both periods")
    features = {
        name: compare_feature(reference[name].to_numpy(), current[name].to_numpy())
        for name in FEATURE_COLUMNS
    }
    report = {
        "analysis": "historical_feature_replay",
        "mode": "pilot" if audit["status"] == "pilot" else "full_cohort",
        "feature_version": FEATURE_VERSION,
        "source_revision_sha": audit["source_revision_sha"],
        "reference_period": "2017-02", "current_period": "2017-03",
        "reference_rows_sampled": len(reference), "current_rows_sampled": len(current),
        "sample_cap_per_period": args.sample_cap,
        "flag_rule": "PSI >= 0.2 or absolute missing-rate delta >= 0.05",
        "flagged_features": [name for name, detail in features.items() if detail["drift_flag"]],
        "features": features,
        "warning": "Pilot source history is incomplete; this report is only a pipeline check."
        if audit["status"] == "pilot" else
        "Historical cohort comparison, not production or performance drift.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "mode", "reference_rows_sampled", "current_rows_sampled", "flagged_features")}, indent=2))


if __name__ == "__main__":
    main()
