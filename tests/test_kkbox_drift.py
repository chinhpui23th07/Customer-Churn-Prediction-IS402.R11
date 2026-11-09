"""Axis 5: KKBox Drift Detection (PSI 3 Binning Regimes, KS Two-Sample, Missing-Rate Delta & CLI)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.kkbox import drift
from src.kkbox.contract import FEATURE_COLUMNS, FEATURE_VERSION


def test_psi_all_three_binning_regimes_and_empty_inputs() -> None:
    # 1. Empty or all-NaN / Inf arrays return None
    assert drift.population_stability_index(np.array([]), np.array([1.0, 2.0])) is None
    assert drift.population_stability_index(np.array([np.nan, np.inf]), np.array([1.0, 2.0])) is None
    assert drift.population_stability_index(np.array([1.0, 2.0]), np.array([np.nan])) is None

    # 2. Constant reference regime (len(unique) == 1)
    ref_const = np.zeros(200)
    cur_const_same = np.zeros(200)
    cur_const_shift = np.ones(200)
    psi_const_same = drift.population_stability_index(ref_const, cur_const_same)
    psi_const_shift = drift.population_stability_index(ref_const, cur_const_shift)
    assert psi_const_same is not None and psi_const_same < 1e-6
    assert psi_const_shift is not None and psi_const_shift > 5.0

    # 3. Discrete/categorical regime (1 < len(unique) <= 10)
    ref_disc = np.array([0, 1, 2, 3] * 100, dtype=float)
    cur_disc_same = np.array([0, 1, 2, 3] * 100, dtype=float)
    cur_disc_shift = np.array([3, 3, 3, 2] * 100, dtype=float)
    psi_disc_same = drift.population_stability_index(ref_disc, cur_disc_same)
    psi_disc_shift = drift.population_stability_index(ref_disc, cur_disc_shift)
    assert psi_disc_same is not None and psi_disc_same < 1e-9
    assert psi_disc_shift is not None and psi_disc_shift >= 0.2

    # 4. Continuous decile regime (len(unique) > 10)
    rng = np.random.default_rng(42)
    ref_cont = rng.normal(loc=100.0, scale=15.0, size=1000)
    cur_cont_same = rng.normal(loc=100.5, scale=15.0, size=1000)
    cur_cont_shift = rng.normal(loc=135.0, scale=15.0, size=1000)
    psi_cont_same = drift.population_stability_index(ref_cont, cur_cont_same)
    psi_cont_shift = drift.population_stability_index(ref_cont, cur_cont_shift)
    assert psi_cont_same is not None and psi_cont_same < 0.05
    assert psi_cont_shift is not None and psi_cont_shift > 0.5


def test_compare_feature_drift_flag_thresholds_and_missing_rates() -> None:
    rng = np.random.default_rng(7)
    base = rng.normal(50.0, 10.0, size=500)
    stable = rng.normal(50.2, 10.0, size=500)
    shifted = rng.normal(80.0, 10.0, size=500)

    res_stable = drift.compare_feature(base, stable)
    assert res_stable["drift_flag"] is False
    assert res_stable["psi"] < 0.2
    assert abs(res_stable["missing_rate_delta"]) < 0.05
    assert 0.0 <= res_stable["ks_statistic"] < 0.15

    res_psi_flagged = drift.compare_feature(base, shifted)
    assert res_psi_flagged["drift_flag"] is True
    assert res_psi_flagged["psi"] >= 0.2
    assert res_psi_flagged["ks_statistic"] > 0.5

    # Missing-rate delta >= 0.05 triggers drift_flag even when valid values are identical
    cur_missing = base.copy()
    cur_missing[:40] = np.nan  # 40 / 500 = 0.08 missing rate delta
    res_missing_flagged = drift.compare_feature(base, cur_missing)
    assert res_missing_flagged["reference_missing_rate"] == 0.0
    assert res_missing_flagged["current_missing_rate"] == pytest.approx(0.08)
    assert res_missing_flagged["missing_rate_delta"] == pytest.approx(0.08)
    assert res_missing_flagged["psi"] < 0.02
    assert res_missing_flagged["drift_flag"] is True

    # All-null edge case
    all_nan = np.full(100, np.nan)
    res_nan = drift.compare_feature(all_nan, all_nan)
    assert res_nan["psi"] is None
    assert res_nan["ks_statistic"] is None
    assert res_nan["ks_p_value"] is None
    assert res_nan["reference_missing_rate"] == 1.0
    assert res_nan["current_missing_rate"] == 1.0
    assert res_nan["drift_flag"] is False


def _write_drift_parquet(root: Path, count: int) -> Path:
    rng = np.random.default_rng(99)
    for period, shift in (("2017-02", 0.0), ("2017-03", 1.0)):
        part_dir = root / f"label_period={period}"
        part_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame({
            "snapshot_key": [f"{1000 + i}|2017-01-31" for i in range(count)],
            "txn_count_30d": rng.integers(1, 4, size=count),
            "paid_amount_30d": rng.normal(149.0 + shift * 200.0, 10.0, size=count),
            "cancel_count_90d": np.zeros(count, dtype=int),
            "days_since_last_txn": rng.integers(1, 28, size=count),
            "last_auto_renew": np.ones(count, dtype=int),
            "days_until_expiry": rng.integers(1, 30, size=count),
            "active_days_30d": rng.integers(5, 25, size=count),
            "listening_secs_30d": rng.normal(3600.0, 300.0, size=count),
            "days_since_last_listen": rng.integers(0, 10, size=count),
            "registration_tenure_days": rng.integers(100, 900, size=count),
            "has_txn_history": np.ones(count, dtype=int),
            "has_listening_history": np.ones(count, dtype=int),
        })
        pq.write_table(pa.Table.from_pandas(df, preserve_index=False), part_dir / "data.parquet")
    return root


def test_drift_cli_end_to_end_and_validation_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feat_root = _write_drift_parquet(tmp_path / "features", count=130)
    pilot_audit = tmp_path / "pilot_audit.json"
    pilot_audit.write_text(
        json.dumps({"status": "pilot", "complete_source": False, "source_revision_sha": "b" * 40}),
        encoding="utf-8",
    )
    full_audit = tmp_path / "full_audit.json"
    full_audit.write_text(
        json.dumps({"status": "full_cohort", "complete_source": True, "source_revision_sha": "b" * 40}),
        encoding="utf-8",
    )
    report_path = tmp_path / "drift_report.json"

    # 1. Reject --sample-cap < 100
    monkeypatch.setattr("sys.argv", ["drift.py", "--sample-cap", "50"])
    with pytest.raises(SystemExit) as exc_cap:
        drift.main()
    assert exc_cap.value.code == 2

    # 2. Reject --require-full on pilot audit
    monkeypatch.setattr(
        "sys.argv",
        ["drift.py", "--features", str(feat_root), "--audit", str(pilot_audit), "--require-full"],
    )
    with pytest.raises(SystemExit) as exc_req_full:
        drift.main()
    assert exc_req_full.value.code == 2

    # 3. Reject < 100 rows in period
    small_root = _write_drift_parquet(tmp_path / "features_small", count=40)
    monkeypatch.setattr(
        "sys.argv",
        ["drift.py", "--features", str(small_root), "--audit", str(pilot_audit), "--report", str(report_path)],
    )
    with pytest.raises(RuntimeError, match="Need at least 100 snapshots in both periods"):
        drift.main()

    # 4. Succeed in full_cohort mode with --require-full
    monkeypatch.setattr(
        "sys.argv",
        [
            "drift.py",
            "--features", str(feat_root),
            "--audit", str(full_audit),
            "--report", str(report_path),
            "--sample-cap", "120",
            "--require-full",
        ],
    )
    drift.main()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "full_cohort"
    assert report["feature_version"] == FEATURE_VERSION
    assert report["reference_rows_sampled"] == 120
    assert report["current_rows_sampled"] == 120
    assert set(report["features"].keys()) == set(FEATURE_COLUMNS)
    assert "paid_amount_30d" in report["flagged_features"]
    assert "Historical cohort comparison" in report["warning"]
