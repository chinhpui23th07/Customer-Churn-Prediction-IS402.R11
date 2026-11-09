"""Publish label-free KKBox features to Feast offline and online stores."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd
from feast import FeatureStore

from src.kkbox.contract import FEATURE_COLUMNS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/kkbox_processed/features"))
    parser.add_argument("--repo", type=Path, default=Path("data/kkbox_feast"))
    parser.add_argument("--report", type=Path, default=Path("docs/experiments/kkbox_feast_report.json"))
    args = parser.parse_args()
    from data.kkbox_feast.definitions import feature_view, snapshot, source

    pattern = str(args.features / "**" / "*.parquet")
    destination = args.repo / "churn_features.parquet"
    destination.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    connection.execute("SET memory_limit='3GB'")
    columns = ", ".join(FEATURE_COLUMNS)
    connection.execute(
        f"""COPY (
            SELECT snapshot_key,
                   CAST(as_of_date AS TIMESTAMP) + INTERVAL '23 hours 59 minutes 59 seconds' AS event_timestamp,
                   {columns}
            FROM read_parquet(?, hive_partitioning=true)
        ) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)""",
        [pattern, str(destination)],
    )
    row_count, unique_keys = connection.execute(
        "SELECT count(*), count(DISTINCT snapshot_key) FROM read_parquet(?)", [str(destination)]
    ).fetchone()
    if row_count != unique_keys:
        raise RuntimeError("Feast source contains duplicate snapshot keys")

    store = FeatureStore(repo_path=str(args.repo.resolve()))
    store.apply([snapshot, source, feature_view])
    cursor = connection.execute("SELECT * FROM read_parquet(?)", [str(destination)])
    written = 0
    while True:
        batch = cursor.fetch_df_chunk(10)
        if batch.empty:
            break
        store.write_to_online_store("kkbox_churn_features", batch)
        written += len(batch)
    if written != row_count:
        raise RuntimeError(f"Feast online write count mismatch: {written} != {row_count}")
    sample_key, sample_timestamp = connection.execute(
        "SELECT snapshot_key, event_timestamp FROM read_parquet(?) LIMIT 1", [str(destination)]
    ).fetchone()
    result = store.get_online_features(
        features=[f"kkbox_churn_features:{name}" for name in FEATURE_COLUMNS],
        entity_rows=[{"snapshot_key": sample_key}],
    ).to_dict()
    populated = sum(result.get(name, result.get(f"kkbox_churn_features:{name}", [None]))[0] is not None
                    for name in FEATURE_COLUMNS)
    if populated < 8:
        raise RuntimeError("Feast online lookup returned too few populated features")
    historical = store.get_historical_features(
        entity_df=pd.DataFrame({
            "snapshot_key": [sample_key],
            "event_timestamp": [pd.Timestamp(sample_timestamp, tz="UTC")],
        }),
        features=[f"kkbox_churn_features:{name}" for name in FEATURE_COLUMNS],
    ).to_df()
    if len(historical) != 1:
        raise RuntimeError("Feast historical lookup did not return one snapshot")
    report = {
        "source_parquet": str(destination),
        "source_bytes": destination.stat().st_size,
        "rows": row_count,
        "unique_snapshot_keys": unique_keys,
        "online_write_rows": written,
        "online_write_method": "Feast write_to_online_store in batches",
        "online_lookup_populated_features": populated,
        "historical_lookup_rows": len(historical),
        "feature_count": len(FEATURE_COLUMNS),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
