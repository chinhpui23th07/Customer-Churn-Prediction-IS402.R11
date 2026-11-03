"""Validate observed KKBox churn labels without publishing customer rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/kkbox_raw"))
    parser.add_argument("--output", type=Path, default=Path("docs/experiments/kkbox_label_quality.json"))
    args = parser.parse_args()
    files = sorted((args.root / "churn_label").glob("window=*/data.parquet"))
    if len(files) != 2:
        raise RuntimeError(f"Expected two label windows, found {len(files)}")
    connection = duckdb.connect()
    connection.execute("SET memory_limit='1GB'")
    connection.execute("SET threads=2")
    summaries = []
    label_window_map = {"2017-02": "train", "2017-03": "train_v2"}
    for file in files:
        period = file.parent.name.removeprefix("window=")
        source_window = label_window_map[period]
        count, churn, distinct_keys, null_keys, invalid_labels, wrong_window = connection.execute(
            """SELECT count(*), sum(CAST(is_churn AS BIGINT)),
                      count(DISTINCT subscriber_key),
                      count(*) FILTER (WHERE subscriber_key IS NULL),
                      count(*) FILTER (WHERE is_churn NOT IN (0, 1) OR is_churn IS NULL),
                      count(*) FILTER (WHERE label_window != ? OR label_window IS NULL)
               FROM read_parquet(?)""",
            [source_window, str(file)],
        ).fetchone()
        if null_keys or invalid_labels or wrong_window or distinct_keys != count:
            raise RuntimeError(f"Invalid label rows in {period}")
        summaries.append({
            "label_window": period,
            "source_label_window": source_window,
            "rows": count,
            "unique_subscribers": distinct_keys,
            "churn_1": churn,
            "churn_0": count - churn,
            "churn_rate": round(churn / count, 6),
            "null_keys": null_keys,
            "invalid_labels": invalid_labels,
        })
    report = {"source": "local downloaded official Parquet", "windows": summaries}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
