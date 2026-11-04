"""Measure sequential reads of the same KKBox Parquet files on local/VM disk.

This measures filesystem throughput, not Spark transform time or Blob download.
Run on both machines with the same manifest paths, repeat count and cache note.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def select_files(raw_dir: Path, manifest: dict, scope: str, max_files: int) -> list[tuple[Path, int]]:
    selected = []
    missing = []
    for entry in manifest["files"]:
        path = raw_dir / entry["path"]
        if not path.is_file():
            missing.append(entry["path"])
            continue
        expected = int(entry["bytes"])
        if path.stat().st_size != expected:
            raise ValueError(f"File size differs from pinned manifest: {entry['path']}")
        selected.append((path, expected))
    if scope == "full" and (missing or len(selected) != 32):
        raise ValueError(f"Full benchmark requires all 32 files; missing {len(missing)}")
    if not selected:
        raise ValueError("No matching local Parquet files")
    if max_files:
        selected = selected[:max_files]
    return selected


def read_once(files: list[tuple[Path, int]]) -> dict:
    started_at = now_utc()
    start = time.perf_counter()
    bytes_read = 0
    for path, expected in files:
        file_bytes = 0
        with path.open("rb") as source:
            while block := source.read(8 * 1024 * 1024):
                file_bytes += len(block)
        if file_bytes != expected:
            raise ValueError(f"Read count changed during benchmark: {path}")
        bytes_read += file_bytes
    elapsed = time.perf_counter() - start
    return {
        "started_at_utc": started_at,
        "finished_at_utc": now_utc(),
        "read_bytes": bytes_read,
        "elapsed_seconds": round(elapsed, 6),
        "throughput_MBps": round(bytes_read / 1_000_000 / max(elapsed, 1e-9), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/kkbox_raw"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/experiments/kkbox_parquet_manifest.json"))
    parser.add_argument("--scope", choices=["available", "full"], default="available")
    parser.add_argument("--max-files", type=int, default=0, help="Local smoke only; 0 means every available file")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--cache-state", choices=["cold", "warm", "unknown"], default="unknown")
    parser.add_argument("--machine-label", required=True, help="Example: local-laptop or azure-vm-southeastasia")
    parser.add_argument("--report", type=Path, default=Path("scratch/kkbox_read_benchmark.json"))
    args = parser.parse_args()
    if args.repeats < 1 or args.max_files < 0:
        parser.error("repeats must be >=1 and max-files must be >=0")
    if args.scope == "full" and args.max_files:
        parser.error("Full scope cannot use --max-files")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    files = select_files(args.raw_dir, manifest, args.scope, args.max_files)
    report = {
        "analysis": "filesystem_sequential_read_only",
        "machine_label": args.machine_label,
        "platform": platform.platform(),
        "cache_state_declared": args.cache_state,
        "source_revision_sha": manifest["revision_sha"],
        "source_scope": args.scope,
        "input_file_count": len(files),
        "expected_input_bytes": sum(expected for _, expected in files),
        "complete_source": len(files) == 32 and not args.max_files,
        "runs": [read_once(files) for _ in range(args.repeats)],
        "note": "This includes OS cache effects. Record CPU/RAM/disk and cache protocol separately.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in
                      ("analysis", "machine_label", "input_file_count", "expected_input_bytes",
                       "complete_source", "runs")}, indent=2))


if __name__ == "__main__":
    main()
