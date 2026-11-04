"""Run the two-window KKBox feature ETL on Spark, locally or on an Azure VM."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from src.kkbox.features import WINDOWS, build_snapshot


def verify_source(input_root: Path, manifest: dict) -> tuple[int, int, bool]:
    """Check every present Parquet against the pinned manifest before Spark starts."""
    expected = {entry["path"]: entry for entry in manifest["files"]}
    present = {path.relative_to(input_root).as_posix(): path
               for path in input_root.rglob("*.parquet")}
    unexpected = present.keys() - expected.keys()
    if unexpected:
        raise RuntimeError(f"Unexpected source files: {sorted(unexpected)}")
    for name, path in present.items():
        entry = expected[name]
        if path.stat().st_size != entry["bytes"]:
            raise RuntimeError(f"Source byte mismatch: {name}")
        if pq.read_metadata(path).num_rows != entry["rows"]:
            raise RuntimeError(f"Source row-count mismatch: {name}")
        fields = {field.name: str(field.type) for field in pq.read_schema(path)}
        if fields != entry["fields"]:
            raise RuntimeError(f"Source schema mismatch: {name}")
    input_bytes = sum(path.stat().st_size for path in present.values())
    return len(present), input_bytes, present.keys() == expected.keys()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/kkbox_raw"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/experiments/kkbox_parquet_manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("data/kkbox_processed/features"))
    parser.add_argument("--audit", type=Path, default=Path("docs/experiments/kkbox_etl_audit.json"))
    parser.add_argument("--sample-modulus", type=int, default=1,
                        help="Deterministic 1/N label cohort for pilot; 1 means full cohort")
    parser.add_argument("--shuffle-partitions", type=int, default=32)
    parser.add_argument("--master", default="local[2]", help="Spark master for a single Azure VM pilot/full run")
    parser.add_argument("--driver-memory", default="3g")
    args = parser.parse_args()
    if args.sample_modulus < 1:
        parser.error("--sample-modulus must be >= 1")
    for family in ("member", "subscription_transaction", "listening_day", "churn_label"):
        if not (args.input / family).is_dir():
            parser.error(f"Missing input family: {family}")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    input_file_count, input_bytes, complete_source = verify_source(args.input, manifest)
    complete_source = (complete_source
                       and input_file_count == manifest["total_published_parquet_files"]
                       and input_bytes == manifest["total_published_parquet_bytes"])
    if args.sample_modulus == 1 and not complete_source:
        parser.error("Full cohort run requires all 32 source files and matching 7.52 GB byte count")

    started = time.perf_counter()
    spark = (SparkSession.builder.master(args.master).appName("kkbox-churn-cutoff-etl")
             .config("spark.driver.memory", args.driver_memory)
             .config("spark.ui.showConsoleProgress", "false")
             .config("spark.sql.shuffle.partitions", str(args.shuffle_partitions))
             .config("spark.sql.session.timeZone", "UTC")
             .getOrCreate())
    try:
        labels = spark.read.parquet(str(args.input / "churn_label"))
        members = spark.read.parquet(str(args.input / "member"))
        transactions = spark.read.parquet(str(args.input / "subscription_transaction"))
        listening = spark.read.parquet(str(args.input / "listening_day"))
        snapshots = [build_snapshot(labels, members, transactions, listening, period,
                                    args.sample_modulus) for period in WINDOWS]
        result = snapshots[0].unionByName(snapshots[1])
        result.write.mode("overwrite").partitionBy("label_period").parquet(str(args.output))
        saved = spark.read.parquet(str(args.output))
        rows = saved.groupBy("label_period").agg(
            F.count("*").alias("rows"),
            F.sum("is_churn").alias("churn_1"),
            F.countDistinct("snapshot_key").alias("unique_snapshots"),
        ).collect()
        windows = {row["label_period"]: {
            "rows": row["rows"], "churn_1": row["churn_1"],
            "unique_snapshots": row["unique_snapshots"],
        } for row in rows}
        if set(windows) != set(WINDOWS):
            raise RuntimeError(f"Missing label period in output: {set(WINDOWS) - set(windows)}")
        if any(value["rows"] != value["unique_snapshots"] for value in windows.values()):
            raise RuntimeError("Duplicate snapshot keys in ETL output")
        audit = {
            "status": "pilot" if args.sample_modulus > 1 else "full_cohort",
            "input": str(args.input), "output": str(args.output),
            "source_revision_sha": manifest["revision_sha"],
            "input_file_count": input_file_count, "input_bytes": input_bytes,
            "complete_source": complete_source,
            "output_parquet_bytes": sum(path.stat().st_size for path in args.output.rglob("*.parquet")),
            "sample_modulus": args.sample_modulus,
            "windows": windows,
            "duration_seconds": round(time.perf_counter() - started, 3),
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        args.audit.parent.mkdir(parents=True, exist_ok=True)
        args.audit.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(audit, indent=2))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
