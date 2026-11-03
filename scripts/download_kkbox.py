"""Stream a pinned KKBox release to local/VM storage; never commit raw rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from urllib.parse import quote

import requests


def copy_file(session: requests.Session, repo: str, revision: str, entry: dict, root: Path) -> dict:
    path = entry["path"]
    expected_size = entry["bytes"]
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    if target.exists() and target.stat().st_size == expected_size:
        return {"path": path, "bytes": expected_size, "status": "existing"}
    if target.exists():
        raise RuntimeError(f"Wrong size in existing file: {target}")
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > expected_size:
        raise RuntimeError(f"Partial file exceeds expected size: {partial}")
    url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{quote(path, safe='/=')}"
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    with session.get(url, headers=headers, stream=True, timeout=90) as response:
        response.raise_for_status()
        if offset and response.status_code != 206:
            raise RuntimeError(f"Server did not honor resume Range for {path}")
        mode = "ab" if offset else "wb"
        with partial.open(mode) as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)
    if partial.stat().st_size != expected_size:
        raise RuntimeError(f"Incomplete download: {path}")
    partial.replace(target)
    digest = hashlib.sha256()
    with target.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": path, "bytes": expected_size, "sha256": digest.hexdigest(), "status": "downloaded"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("docs/experiments/kkbox_parquet_manifest.json"))
    parser.add_argument("--dest", type=Path, default=Path("data/kkbox_raw"))
    parser.add_argument("--scope", choices=["labels", "pilot", "full"], default="labels")
    parser.add_argument("--report", type=Path, default=Path("docs/experiments/kkbox_download_report.json"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("scope") != "all":
        raise RuntimeError("Full source manifest required")
    pilot_paths = {
        "member/data.parquet",
        "subscription_transaction/part=0/data.parquet",
        "listening_day/source_version=v1/activity_month=201701/data.parquet",
        "listening_day/source_version=v1/activity_month=201702/data.parquet",
    }
    entries = [
        entry for entry in manifest["files"]
        if args.scope == "full" or entry["path"].startswith("churn_label/")
        or (args.scope == "pilot" and entry["path"] in pilot_paths)
    ]
    required = sum(entry["bytes"] for entry in entries)
    args.dest.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(args.dest).free
    if free < required + 10 * 1024**3:
        raise RuntimeError(f"Need {required:,} bytes plus 10 GiB free disk reserve")
    session = requests.Session()
    completed = []
    for index, entry in enumerate(entries, 1):
        result = copy_file(session, manifest["dataset"], manifest["revision_sha"], entry, args.dest)
        completed.append(result)
        print(f"[{index}/{len(entries)}] {result['status']}: {result['path']}", flush=True)
    report = {
        "dataset": manifest["dataset"],
        "revision_sha": manifest["revision_sha"],
        "scope": args.scope,
        "file_count": len(completed),
        "bytes": sum(result["bytes"] for result in completed),
        "files": completed,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
