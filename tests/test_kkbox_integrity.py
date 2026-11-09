"""Axis 1: KKBox 7.52 GB Source Manifest, Parquet Integrity, Download, Label Validation & ETL CLI Gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts import download_kkbox, inspect_kkbox_source, validate_kkbox_labels
from src.kkbox.run_etl import main as run_etl_main
from src.kkbox.run_etl import verify_source


def _write_sample_parquet(path: Path, rows: list[int] | None = None) -> tuple[Path, dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    values = rows if rows is not None else [1, 2, 3]
    table = pa.table({"subscriber_key": pa.array(values, type=pa.uint64())})
    pq.write_table(table, path)
    return path, {
        "path": "member/data.parquet",
        "family": "member",
        "bytes": path.stat().st_size,
        "rows": len(values),
        "row_groups": 1,
        "columns": ["subscriber_key"],
        "fields": {"subscriber_key": "uint64"},
    }


def test_real_published_parquet_manifest_contract() -> None:
    manifest_path = Path("docs/experiments/kkbox_parquet_manifest.json")
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["dataset"] == "vaibhavkhurana/subscriber-retention-intelligence"
    assert manifest["revision_sha"] == "a0f48c28e392e9a60d4d6fc62f1bbf3d848277d3"
    assert manifest["scope"] == "all"
    assert manifest["total_published_parquet_files"] == 32
    assert manifest["total_published_parquet_bytes"] == 7_522_254_856
    assert manifest["inspected_rows"] == 442_211_685
    assert len(manifest["files"]) == 32

    sum_bytes = sum(entry["bytes"] for entry in manifest["files"])
    sum_rows = sum(entry["rows"] for entry in manifest["files"])
    assert sum_bytes == manifest["total_published_parquet_bytes"]
    assert sum_rows == manifest["inspected_rows"]

    expected_counts = {
        "member": 1,
        "subscription_transaction": 2,
        "listening_day": 27,
        "churn_label": 2,
    }
    for family, count in expected_counts.items():
        assert manifest["families"][family]["file_count"] == count
        family_files = [f for f in manifest["files"] if f["path"].startswith(f"{family}/")]
        assert len(family_files) == count

    assert manifest["families"]["churn_label"]["rows"] == 1_963_891
    assert manifest["families"]["churn_label"]["schemas"][0] == {
        "subscriber_key": "uint64",
        "label_window": "string",
        "is_churn": "uint8",
    }


def test_verify_source_accepts_matching_and_incomplete_subset(tmp_path: Path) -> None:
    file_path = tmp_path / "member" / "data.parquet"
    _, entry = _write_sample_parquet(file_path)
    manifest = {"files": [entry, {**entry, "path": "member/extra.parquet"}]}

    count, total_bytes, is_complete = verify_source(tmp_path, manifest)
    assert count == 1
    assert total_bytes == entry["bytes"]
    assert is_complete is False

    manifest_single = {"files": [entry]}
    count_full, bytes_full, is_complete_full = verify_source(tmp_path, manifest_single)
    assert count_full == 1
    assert bytes_full == entry["bytes"]
    assert is_complete_full is True


def test_verify_source_rejects_unexpected_byte_row_and_schema_mismatches(tmp_path: Path) -> None:
    file_path = tmp_path / "member" / "data.parquet"
    _, entry = _write_sample_parquet(file_path)

    with pytest.raises(RuntimeError, match="Source byte mismatch"):
        verify_source(tmp_path, {"files": [{**entry, "bytes": entry["bytes"] + 1}]})

    with pytest.raises(RuntimeError, match="Source row-count mismatch"):
        verify_source(tmp_path, {"files": [{**entry, "rows": entry["rows"] + 1}]})

    with pytest.raises(RuntimeError, match="Source schema mismatch"):
        verify_source(tmp_path, {"files": [{**entry, "fields": {"subscriber_key": "int64"}}]})

    rogue = tmp_path / "member" / "rogue.parquet"
    _write_sample_parquet(rogue)
    with pytest.raises(RuntimeError, match="Unexpected source files"):
        verify_source(tmp_path, {"files": [entry]})


def test_run_etl_cli_pre_spark_validation_gates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file_path = tmp_path / "raw" / "member" / "data.parquet"
    _, entry = _write_sample_parquet(file_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({
            "revision_sha": "a" * 40,
            "total_published_parquet_files": 32,
            "total_published_parquet_bytes": 7_522_254_856,
            "files": [entry],
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr("sys.argv", ["run_etl.py", "--sample-modulus", "0"])
    with pytest.raises(SystemExit) as exc_bad_mod:
        run_etl_main()
    assert exc_bad_mod.value.code == 2

    monkeypatch.setattr(
        "sys.argv",
        ["run_etl.py", "--input", str(tmp_path / "raw"), "--manifest", str(manifest_path), "--sample-modulus", "2"],
    )
    with pytest.raises(SystemExit) as exc_missing_family:
        run_etl_main()
    assert exc_missing_family.value.code == 2

    for family in ("member", "subscription_transaction", "listening_day", "churn_label"):
        (tmp_path / "raw" / family).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "sys.argv",
        ["run_etl.py", "--input", str(tmp_path / "raw"), "--manifest", str(manifest_path), "--sample-modulus", "1"],
    )
    with pytest.raises(SystemExit) as exc_incomplete_full:
        run_etl_main()
    assert exc_incomplete_full.value.code == 2


def _write_label_window(root: Path, period: str, keys: list[int | None], churns: list[int | None], windows: list[str]) -> Path:
    path = root / "churn_label" / f"window={period}" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table({
        "subscriber_key": pa.array(keys, type=pa.uint64()),
        "label_window": pa.array(windows, type=pa.string()),
        "is_churn": pa.array(churns, type=pa.int64()),
    })
    pq.write_table(table, path)
    return path


def test_validate_kkbox_labels_success_and_violation_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = tmp_path / "raw"
    report_path = tmp_path / "label_quality.json"
    _write_label_window(raw_root, "2017-02", [101, 102], [0, 1], ["train", "train"])
    _write_label_window(raw_root, "2017-03", [101, 103], [1, 0], ["train_v2", "train_v2"])

    monkeypatch.setattr(
        "sys.argv",
        ["validate_kkbox_labels.py", "--root", str(raw_root), "--output", str(report_path)],
    )
    validate_kkbox_labels.main()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert len(report["windows"]) == 2
    assert report["windows"][0]["label_window"] == "2017-02"
    assert report["windows"][0]["rows"] == 2
    assert report["windows"][1]["label_window"] == "2017-03"
    assert report["windows"][1]["source_label_window"] == "train_v2"

    # Duplicate subscriber_key in 2017-02
    _write_label_window(raw_root, "2017-02", [101, 101], [0, 1], ["train", "train"])
    with pytest.raises(RuntimeError, match="Invalid label rows in 2017-02"):
        validate_kkbox_labels.main()

    # Invalid is_churn value (2)
    _write_label_window(raw_root, "2017-02", [101, 102], [0, 2], ["train", "train"])
    with pytest.raises(RuntimeError, match="Invalid label rows in 2017-02"):
        validate_kkbox_labels.main()

    # Wrong label_window string
    _write_label_window(raw_root, "2017-02", [101, 102], [0, 1], ["train", "wrong_win"])
    with pytest.raises(RuntimeError, match="Invalid label rows in 2017-02"):
        validate_kkbox_labels.main()

    # Missing second window
    (raw_root / "churn_label" / "window=2017-03" / "data.parquet").unlink()
    with pytest.raises(RuntimeError, match="Expected two label windows"):
        validate_kkbox_labels.main()


class _FakeStreamResponse:
    def __init__(self, payload: bytes, status_code: int = 200, headers: dict[str, str] | None = None) -> None:
        self.content = payload
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 1024 * 1024):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i : i + chunk_size]

    def __enter__(self) -> _FakeStreamResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _FakeSession:
    def __init__(self, handler) -> None:
        self._handler = handler
        self.seen_headers: list[dict] = []

    def get(self, url: str, headers: dict | None = None, stream: bool = True, timeout: int = 90) -> _FakeStreamResponse:
        self.seen_headers.append(headers or {})
        return self._handler(url, headers or {})


def test_download_kkbox_copy_resume_and_manifest_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"PAR1-kkbox-test-payload-PAR1"
    expected_sha = hashlib.sha256(payload).hexdigest()
    entry = {"path": "churn_label/window=2017-02/data.parquet", "bytes": len(payload)}
    dest = tmp_path / "dl"

    session = _FakeSession(lambda url, hdrs: _FakeStreamResponse(payload, status_code=200))
    res = download_kkbox.copy_file(session, "repo/name", "sha123", entry, dest)
    assert res["status"] == "downloaded"
    assert res["sha256"] == expected_sha

    res_existing = download_kkbox.copy_file(session, "repo/name", "sha123", entry, dest)
    assert res_existing["status"] == "existing"

    with pytest.raises(RuntimeError, match="Wrong size in existing file"):
        download_kkbox.copy_file(session, "repo/name", "sha123", {**entry, "bytes": len(payload) + 4}, dest)

    # Partial file resume via HTTP 206 Range
    resume_entry = {"path": "member/data.parquet", "bytes": len(payload)}
    part_path = dest / "member" / "data.parquet.part"
    part_path.parent.mkdir(parents=True, exist_ok=True)
    part_path.write_bytes(payload[:10])
    resume_session = _FakeSession(lambda url, hdrs: _FakeStreamResponse(payload[10:], status_code=206))
    res_resumed = download_kkbox.copy_file(resume_session, "repo/name", "sha123", resume_entry, dest)
    assert resume_session.seen_headers == [{"Range": "bytes=10-"}]
    assert res_resumed["status"] == "downloaded"
    assert res_resumed["sha256"] == expected_sha
    assert not part_path.exists()

    # Server ignoring Range (returns 200 instead of 206)
    bad_entry = {"path": "member/bad.parquet", "bytes": len(payload)}
    bad_part = dest / "member" / "bad.parquet.part"
    bad_part.write_bytes(payload[:5])
    bad_session = _FakeSession(lambda url, hdrs: _FakeStreamResponse(payload, status_code=200))
    with pytest.raises(RuntimeError, match="Server did not honor resume Range"):
        download_kkbox.copy_file(bad_session, "repo/name", "sha123", bad_entry, dest)


def test_inspect_kkbox_source_footer_parsing(tmp_path: Path) -> None:
    parquet_file, entry = _write_sample_parquet(tmp_path / "sample.parquet", [10, 20, 30, 40])
    raw_bytes = parquet_file.read_bytes()
    total = len(raw_bytes)

    def _range_handler(url: str, hdrs: dict) -> _FakeStreamResponse:
        spec = hdrs["Range"].removeprefix("bytes=")
        if spec == "-8":
            start, end = total - 8, total - 1
        else:
            start_s, end_s = spec.split("-")
            start, end = int(start_s), int(end_s)
        chunk = raw_bytes[start : end + 1]
        return _FakeStreamResponse(
            chunk,
            status_code=206,
            headers={"Content-Range": f"bytes {start}-{end}/{total}"},
        )

    session = _FakeSession(_range_handler)
    info = inspect_kkbox_source.inspect_parquet(session, entry["path"], total, "rev123")
    assert info["rows"] == 4
    assert info["bytes"] == total
    assert info["fields"] == {"subscriber_key": "uint64"}

    with pytest.raises(RuntimeError, match="Published size mismatch"):
        inspect_kkbox_source.inspect_parquet(session, entry["path"], total + 10, "rev123")
