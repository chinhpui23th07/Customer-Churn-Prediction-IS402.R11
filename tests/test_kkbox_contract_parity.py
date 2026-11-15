"""WQR 2025-2026 Test Maintenance & Contract Parity Verification Suite.

Mitigates the #1 QA bottleneck (53% test maintenance from UI/API churn)
by enforcing automated contract parity across 4 project layers:
1. Feature Store Contract (`contracts/feature_contract.md`).
2. Serving API Contract (`contracts/api_contract.md`).
3. FastAPI Request/Response Schemas (`src/kkbox/api.py`).
4. Web UI Demo Console (`src/kkbox/web/index.html`).
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest

from src.kkbox import api
from src.kkbox.contract import ALLOWED_CUTOFFS, FEATURE_COLUMNS, FEATURE_VERSION

ROOT_DIR = Path(__file__).resolve().parent.parent
FEATURE_CONTRACT_PATH = ROOT_DIR / "contracts" / "feature_contract.md"
API_CONTRACT_PATH = ROOT_DIR / "contracts" / "api_contract.md"
WEB_HTML_PATH = ROOT_DIR / "src" / "kkbox" / "web" / "index.html"


def test_feature_contract_file_exists_and_contains_12_features() -> None:
    """Verify contracts/feature_contract.md defines exactly the 12 canonical KKBox features."""
    assert FEATURE_CONTRACT_PATH.exists(), f"Missing {FEATURE_CONTRACT_PATH}"
    content = FEATURE_CONTRACT_PATH.read_text(encoding="utf-8")

    # Extract backtick feature names from markdown table
    table_features = re.findall(r"\|\s*`([a-z0-9_]+)`\s*\|\s*(?:integer|float|0/1)", content)
    assert len(table_features) == 12, f"Expected 12 features in contract table, found {len(table_features)}"
    assert table_features == list(FEATURE_COLUMNS), (
        f"Contract table features do not match python FEATURE_COLUMNS:\n"
        f"Contract: {table_features}\nPython:   {list(FEATURE_COLUMNS)}"
    )


def test_api_contract_cutoffs_parity() -> None:
    """Verify contracts/api_contract.md enforces exactly 2017-01-31 and 2017-02-28 cutoffs."""
    assert API_CONTRACT_PATH.exists(), f"Missing {API_CONTRACT_PATH}"
    content = API_CONTRACT_PATH.read_text(encoding="utf-8")

    assert "2017-01-31" in content
    assert "2017-02-28" in content
    assert set(ALLOWED_CUTOFFS) == {"2017-01-31", "2017-02-28"}


def test_fastapi_schema_contract_parity() -> None:
    """Verify FastAPI Pydantic models strictly match contract feature definitions."""
    # 1. Feature version parity
    assert FEATURE_VERSION == "kkbox-v1"

    # 2. PredictionRequest validator enforces canonical decimal string within uint64
    valid_req = api.PredictionRequest(subscriber_key="1234567890123456789", as_of_date="2017-02-28")
    assert valid_req.subscriber_key == "1234567890123456789"
    assert valid_req.as_of_date == "2017-02-28"

    # 3. ManualPredictionRequest requires exact set of 12 features
    features_dict = {col: 1.0 for col in FEATURE_COLUMNS}
    manual_req = api.ManualPredictionRequest(features=features_dict)
    assert len(manual_req.features) == 12
    assert set(manual_req.features.keys()) == set(FEATURE_COLUMNS)


def test_web_ui_console_form_parity() -> None:
    """Verify Web Demo console (index.html) matches API cutoffs and input requirements."""
    assert WEB_HTML_PATH.exists(), f"Missing {WEB_HTML_PATH}"
    content = WEB_HTML_PATH.read_text(encoding="utf-8")

    # Check cutoffs select options in HTML
    assert "2017-01-31" in content, "Web console missing 2017-01-31 cutoff option"
    assert "2017-02-28" in content, "Web console missing 2017-02-28 cutoff option"

    # Check subscriber key input
    assert 'id="subscriber_key"' in content or 'name="subscriber_key"' in content, (
        "Web console missing subscriber_key input element"
    )

    # Check API endpoints referenced in frontend JS
    assert "/v1/predictions" in content, "Web console must target /v1/predictions endpoint"


def test_uint64_decimal_string_ieee754_precision_preservation() -> None:
    """Ensure subscriber keys exceeding 2^53 (JS MAX_SAFE_INTEGER) retain string integrity."""
    safe_int_max_plus_one = str(2**53 + 1)  # 9007199254740993
    max_uint64_str = str(2**64 - 1)         # 18446744073709551615

    # Should validate cleanly as string
    req1 = api.PredictionRequest(subscriber_key=safe_int_max_plus_one, as_of_date="2017-02-28")
    assert req1.subscriber_key == safe_int_max_plus_one
    assert isinstance(req1.subscriber_key, str)

    req2 = api.PredictionRequest(subscriber_key=max_uint64_str, as_of_date="2017-02-28")
    assert req2.subscriber_key == max_uint64_str
    assert isinstance(req2.subscriber_key, str)


def test_zero_synthetic_fallbacks_in_feature_contract() -> None:
    """Verify contract explicitly prohibits synthetic mockups or target leakage."""
    content = FEATURE_CONTRACT_PATH.read_text(encoding="utf-8")
    assert "Cấm dùng làm feature" in content
    assert "is_churn" in content
    assert "subscriber_key" in content
