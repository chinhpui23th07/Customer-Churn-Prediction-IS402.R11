"""Inspect published Parquet footers without downloading the KKBox corpus."""

from __future__ import annotations

import argparse
import io
import json
import re
import struct
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import pyarrow.parquet as pq
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REPO = "vaibhavkhurana/subscriber-retention-intelligence"
API = f"https://huggingface.co/api/datasets/{REPO}"
MAX_FOOTER_BYTES = 16 * 1024 * 1024


def session_with_retries() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def range_bytes(session: requests.Session, url: str, spec: str) -> tuple[bytes, int]:
    with session.get(url, headers={"Range": f"bytes={spec}"}, stream=True, timeout=40) as response:
        response.raise_for_status()
        if response.status_code != 206:
            raise RuntimeError(f"Server ignored Range request for {url}")
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
        if not match:
            raise RuntimeError(f"Invalid Content-Range for {url}")
        start, end, total = (int(part) for part in match.groups())
        if end - start + 1 > MAX_FOOTER_BYTES + 8:
            raise RuntimeError(f"Range too large for {url}")
        body = response.content
        if len(body) != end - start + 1:
            raise RuntimeError(f"Incomplete Range response for {url}")
        return body, total


def inspect_parquet(session: requests.Session, path: str, expected_size: int, revision: str) -> dict:
    url = f"https://huggingface.co/datasets/{REPO}/resolve/{revision}/{quote(path, safe='/=')}"
    trailer, size = range_bytes(session, url, "-8")
    footer_length = struct.unpack("<I", trailer[:4])[0]
    if trailer[4:] != b"PAR1" or footer_length > MAX_FOOTER_BYTES:
        raise RuntimeError(f"Bad Parquet footer: {path}")
    if size != expected_size:
        raise RuntimeError(f"Published size mismatch: {path} ({size} != {expected_size})")
    footer, _ = range_bytes(session, url, f"{size - footer_length - 8}-{size - 1}")
    metadata = pq.read_metadata(io.BytesIO(b"PAR1" + footer))
    fields = {field.name: str(field.type) for field in metadata.schema.to_arrow_schema()}
    codecs = sorted({
        metadata.row_group(i).column(j).compression
        for i in range(metadata.num_row_groups)
        for j in range(metadata.row_group(i).num_columns)
    })
    return {
        "path": path,
        "bytes": size,
        "rows": metadata.num_rows,
        "row_groups": metadata.num_row_groups,
        "compression": codecs,
        "fields": fields,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/experiments/kkbox_parquet_manifest.json"))
    parser.add_argument("--limit", type=int, default=0, help="Inspect only first N files for a quick probe")
    args = parser.parse_args()

    session = session_with_retries()
    info = session.get(API, timeout=30).json()
    info_sha = info["sha"]
    tree_response = session.get(f"{API}/tree/{info_sha}?recursive=true", timeout=30)
    tree_response.raise_for_status()
    files = sorted(
        ((entry["path"], entry["size"]) for entry in tree_response.json()
         if entry.get("type") == "file" and entry["path"].endswith(".parquet")),
        key=lambda item: item[0],
    )
    if not files:
        raise RuntimeError("No Parquet files found")
    selected = files[:args.limit] if args.limit else files
    entries = []
    for index, (path, size) in enumerate(selected, 1):
        entry = inspect_parquet(session, path, size, info_sha)
        entries.append(entry)
        print(f"[{index}/{len(selected)}] {path}: {entry['rows']:,} rows, {size:,} bytes")

    families = defaultdict(lambda: {"rows": 0, "bytes": 0, "file_count": 0, "schemas": []})
    for entry in entries:
        family = entry["path"].split("/", 1)[0]
        bucket = families[family]
        bucket["rows"] += entry["rows"]
        bucket["bytes"] += entry["bytes"]
        bucket["file_count"] += 1
        if entry["fields"] not in bucket["schemas"]:
            bucket["schemas"].append(entry["fields"])

    manifest = {
        "dataset": REPO,
        "revision_sha": info_sha,
        "inspected_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "all" if not args.limit else f"first_{len(selected)}",
        "total_published_parquet_files": len(files),
        "total_published_parquet_bytes": sum(size for _, size in files),
        "inspected_rows": sum(entry["rows"] for entry in entries),
        "families": dict(families),
        "files": entries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Manifest: {args.output}")


if __name__ == "__main__":
    main()
