"""Evidence tools must not label partial reads as full source processing."""

import pytest

from scripts.kkbox_benchmark_read import read_once, select_files
from scripts.kkbox_latency_probe import percentile


def test_read_benchmark_requires_all_manifest_files_for_full(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "one.parquet").write_bytes(b"example")
    manifest = {"files": [{"path": "one.parquet", "bytes": 7},
                          {"path": "missing.parquet", "bytes": 9}]}
    with pytest.raises(ValueError, match="requires all 32"):
        select_files(raw, manifest, "full", 0)
    selected = select_files(raw, manifest, "available", 0)
    assert read_once(selected)["read_bytes"] == 7


def test_latency_percentile_is_interpolated():
    assert percentile([40, 10, 20, 30], .5) == 25
