"""Guard full-source claims and detect a genuine feature distribution shift."""

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.kkbox.drift import compare_feature
from src.kkbox.run_etl import verify_source


def test_source_verification_requires_exact_path_size_and_row_count(tmp_path):
    path = tmp_path / "member" / "data.parquet"
    path.parent.mkdir()
    pq.write_table(pa.table({"subscriber_key": [1, 2]}), path)
    entry = {"path": "member/data.parquet", "bytes": path.stat().st_size,
             "rows": 2, "fields": {"subscriber_key": "int64"}}
    manifest = {"files": [entry]}
    assert verify_source(tmp_path, manifest) == (1, entry["bytes"], True)
    with pytest.raises(RuntimeError, match="byte mismatch"):
        verify_source(tmp_path, {"files": [{**entry, "bytes": entry["bytes"] + 1}]})
    with pytest.raises(RuntimeError, match="row-count mismatch"):
        verify_source(tmp_path, {"files": [{**entry, "rows": 3}]})
    with pytest.raises(RuntimeError, match="schema mismatch"):
        verify_source(tmp_path, {"files": [{**entry, "fields": {"subscriber_key": "uint64"}}]})
    with pytest.raises(RuntimeError, match="Unexpected source"):
        verify_source(tmp_path, {"files": []})


def test_drift_flags_shift_and_missingness():
    reference = np.tile(np.arange(10, dtype=float), 100)
    stable = compare_feature(reference, reference.copy())
    shifted = compare_feature(reference, reference + 100)
    missing = compare_feature(reference, np.r_[reference[:800], np.full(200, np.nan)])
    assert not stable["drift_flag"]
    assert stable["psi"] == 0
    assert shifted["drift_flag"] and shifted["psi"] > 0.2
    assert missing["drift_flag"] and missing["missing_rate_delta"] == 0.2
