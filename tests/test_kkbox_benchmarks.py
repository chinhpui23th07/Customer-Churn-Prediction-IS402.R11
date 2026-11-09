"""Axis 8A: KKBox Read Benchmark, Multi-Region Latency Probe, Pick Demo Key, DVC & CI Pipeline Contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from scripts import kkbox_benchmark_read, kkbox_latency_probe, kkbox_pick_demo_key


def test_read_benchmark_selection_execution_and_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file_path = tmp_path / "raw" / "member" / "data.parquet"
    file_path.parent.mkdir(parents=True)
    file_path.write_bytes(b"x" * 2048)
    manifest = {
        "revision_sha": "a" * 40,
        "files": [
            {"path": "member/data.parquet", "bytes": 2048},
            {"path": "churn_label/window=2017-02/data.parquet", "bytes": 1024},
        ],
    }

    selected = kkbox_benchmark_read.select_files(tmp_path / "raw", manifest, "available", 0)
    assert len(selected) == 1
    run = kkbox_benchmark_read.read_once(selected)
    assert run["read_bytes"] == 2048
    assert run["throughput_MBps"] > 0

    with pytest.raises(ValueError, match="Full benchmark requires all 32 files"):
        kkbox_benchmark_read.select_files(tmp_path / "raw", manifest, "full", 0)

    # Byte size mismatch
    with pytest.raises(ValueError, match="File size differs from pinned manifest"):
        kkbox_benchmark_read.select_files(
            tmp_path / "raw",
            {"files": [{"path": "member/data.parquet", "bytes": 999}]},
            "available",
            0,
        )

    # End-to-end CLI execution
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    report_file = tmp_path / "bench_report.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "kkbox_benchmark_read.py",
            "--raw-dir", str(tmp_path / "raw"),
            "--manifest", str(manifest_file),
            "--scope", "available",
            "--repeats", "2",
            "--cache-state", "warm",
            "--machine-label", "local-test-rig",
            "--report", str(report_file),
        ],
    )
    kkbox_benchmark_read.main()
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["machine_label"] == "local-test-rig"
    assert report["cache_state_declared"] == "warm"
    assert report["input_file_count"] == 1
    assert report["expected_input_bytes"] == 2048
    assert report["complete_source"] is False
    assert len(report["runs"]) == 2

    # Full scope cannot combine with --max-files
    monkeypatch.setattr(
        "sys.argv",
        [
            "kkbox_benchmark_read.py",
            "--scope", "full",
            "--max-files", "1",
            "--machine-label", "local-test-rig",
        ],
    )
    with pytest.raises(SystemExit) as exc_full_max:
        kkbox_benchmark_read.main()
    assert exc_full_max.value.code == 2


class _FakeProbeResponse:
    def __init__(self, data: dict, status_code: int = 200) -> None:
        self._data = data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._data


def test_latency_probe_percentiles_multi_region_and_secret_redaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = [10.0, 20.0, 30.0, 40.0, 100.0]
    assert kkbox_latency_probe.percentile(values, 0.50) == 30.0
    assert kkbox_latency_probe.percentile(values, 0.95) > 40.0

    secret_sub_key = "18446744073709551615"
    secret_api_key = "super-secret-api-token-999"
    monkeypatch.setenv("KKBOX_DEMO_SUBSCRIBER_KEY", secret_sub_key)
    monkeypatch.setenv("KKBOX_API_KEY", secret_api_key)

    class _FakeSession:
        def __enter__(self) -> _FakeSession:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, json: dict, headers: dict, timeout: float) -> _FakeProbeResponse:
            assert headers["x-api-key"] == secret_api_key
            return _FakeProbeResponse({
                "prediction": 1,
                "churn_probability": 0.742,
                "model_version": "3",
                "feature_version": "kkbox-v1",
            })

    monkeypatch.setattr("requests.Session", _FakeSession)
    report_path = tmp_path / "latency.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "kkbox_latency_probe.py",
            "--endpoint", "southeastasia=https://sea.example.com",
            "--endpoint", "eastus=https://eus.example.com",
            "--requests", "5",
            "--warmup", "2",
            "--client-label", "hcmc-fiber",
            "--report", str(report_path),
        ],
    )
    kkbox_latency_probe.main()

    raw_text = report_path.read_text(encoding="utf-8")
    assert secret_sub_key not in raw_text
    assert secret_api_key not in raw_text
    report = json.loads(raw_text)
    assert report["comparable_model_and_payload"] is True
    assert report["region_comparison_ready"] is True
    assert len(report["results"]) == 2
    assert report["results"][0]["successful"] == 5

    # Divergent predictions between regions must fail comparability check
    class _DivergentSession(_FakeSession):
        def post(self, url: str, json: dict, headers: dict, timeout: float) -> _FakeProbeResponse:
            prob = 0.8 if "sea" in url else 0.2
            return _FakeProbeResponse({
                "prediction": int(prob >= 0.5),
                "churn_probability": prob,
                "model_version": "3",
                "feature_version": "kkbox-v1",
            })

    monkeypatch.setattr("requests.Session", _DivergentSession)
    with pytest.raises(SystemExit, match="comparison invalid"):
        kkbox_latency_probe.main()

    # Non-HTTPS non-localhost endpoint rejected
    monkeypatch.setattr(
        "sys.argv",
        [
            "kkbox_latency_probe.py",
            "--endpoint", "insecure=http://remote.example.com",
            "--client-label", "hcmc-fiber",
        ],
    )
    with pytest.raises(SystemExit) as exc_http:
        kkbox_latency_probe.main()
    assert exc_http.value.code == 2


def test_pick_demo_key_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    feat_dir = tmp_path / "features" / "label_period=2017-03"
    feat_dir.mkdir(parents=True)
    pd.DataFrame({
        "subscriber_key": ["9876543210123456789"],
        "snapshot_key": ["9876543210123456789|2017-02-28"],
    }).to_parquet(feat_dir / "part.parquet", index=False)

    monkeypatch.setattr(
        "sys.argv",
        ["kkbox_pick_demo_key.py", "--features", str(tmp_path / "features"), "--cutoff", "2017-02-28"],
    )
    kkbox_pick_demo_key.main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "9876543210123456789"

    monkeypatch.setattr(
        "sys.argv",
        ["kkbox_pick_demo_key.py", "--features", str(tmp_path / "features"), "--cutoff", "2017-01-31"],
    )
    with pytest.raises(SystemExit) as exc_missing_cutoff:
        kkbox_pick_demo_key.main()
    assert exc_missing_cutoff.value.code == 2


def test_dvc_yaml_and_github_workflows_kkbox_stages() -> None:
    dvc_data = yaml.safe_load(Path("dvc.yaml").read_text(encoding="utf-8"))
    stages = dvc_data["stages"]
    expected_kkbox_stages = {
        "kkbox_download_full",
        "kkbox_etl_full",
        "kkbox_train_full",
        "kkbox_feast_full",
        "kkbox_drift_full",
        "kkbox_figures_full",
    }
    assert expected_kkbox_stages.issubset(stages.keys())

    ci_wf = Path(".github/workflows/kkbox_ci.yml").read_text(encoding="utf-8")
    assert "pytest tests/test_kkbox_*.py" in ci_wf

    full_wf = Path(".github/workflows/kkbox_full_runner.yml").read_text(encoding="utf-8")
    assert "dvc repro kkbox_train_full" in full_wf
    assert "dvc repro kkbox_feast_full" in full_wf
    assert "dvc repro kkbox_drift_full" in full_wf
    assert "dvc repro kkbox_figures_full" in full_wf
