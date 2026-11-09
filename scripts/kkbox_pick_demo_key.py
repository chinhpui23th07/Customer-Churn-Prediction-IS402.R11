"""Print one locally available subscriber key for a historical replay demo.

Use this only on a private machine. Do not commit the key or include it in
public screenshots; it is a pseudonymized record identifier from the dataset.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/kkbox_processed/pilot_features"))
    parser.add_argument("--cutoff", choices=["2017-01-31", "2017-02-28"],
                        default="2017-02-28")
    args = parser.parse_args()
    pattern = str(args.features / "**" / "*.parquet")
    if not args.features.exists():
        parser.error(f"Feature directory missing: {args.features}")
    with duckdb.connect() as connection:
        row = connection.execute(
            "SELECT CAST(subscriber_key AS VARCHAR) FROM read_parquet(?, hive_partitioning=true) "
            "WHERE snapshot_key LIKE ? LIMIT 1",
            [pattern, "%|" + args.cutoff],
        ).fetchone()
    if row is None:
        parser.error(f"No feature snapshot at {args.cutoff}")
    print(row[0])


if __name__ == "__main__":
    main()
