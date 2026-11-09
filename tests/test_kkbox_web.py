"""Axis 7: KKBox Signal Lab Web UI & Frontend-Backend Contract Parity."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app as main_app
from src.kkbox.api import app as kkbox_app
from src.kkbox.contract import ALLOWED_CUTOFFS, FEATURE_COLUMNS


def test_demo_routes_and_static_assets_on_both_apps() -> None:
    html_headers = {"accept": "text/html,application/xhtml+xml"}
    for target_app in (kkbox_app, main_app):
        client = TestClient(target_app)

        demo = client.get("/demo")
        assert demo.status_code == 200
        assert "text/html" in demo.headers["content-type"]
        assert "KKBox Signal Lab" in demo.text
        assert 'id="prediction-form"' in demo.text
        assert 'id="manual-form"' in demo.text
        assert 'id="batch-form"' in demo.text
        assert 'id="api-key"' in demo.text
        assert 'type="password"' in demo.text
        assert 'autocomplete="off"' in demo.text

        css = client.get("/demo/assets/style.css")
        assert css.status_code == 200
        assert ".page-shell" in css.text
        assert ".workspace-grid" in css.text
        for banned_purple in ("#8b5cf6", "#a855f7", "#7c3aed", "#9333ea"):
            assert banned_purple not in css.text.lower()

        js = client.get("/demo/assets/app.js")
        assert js.status_code == 200
        assert "validSubscriberKey" in js.text

        favicon = client.get("/demo/assets/favicon.svg")
        assert favicon.status_code == 200
        root = ET.fromstring(favicon.text)
        assert root.tag.endswith("svg")

    # Root content negotiation on unified main_app
    main_client = TestClient(main_app)
    redirect_html = main_client.get("/", headers=html_headers, follow_redirects=False)
    assert redirect_html.status_code == 307
    assert redirect_html.headers["location"] == "/demo"

    redirect_json = main_client.get("/", headers={"accept": "application/json"}, follow_redirects=False)
    assert redirect_json.status_code == 307
    assert redirect_json.headers["location"] == "/docs"


def test_frontend_js_and_html_strict_contract_parity() -> None:
    web_dir = Path("src/kkbox/web")
    html_text = (web_dir / "index.html").read_text(encoding="utf-8")
    js_text = (web_dir / "app.js").read_text(encoding="utf-8")

    # 1. Extract featureLabels keys in exact order and compare to FEATURE_COLUMNS
    match = re.search(r"const\s+featureLabels\s*=\s*\{([^}]+)\}", js_text, flags=re.DOTALL)
    assert match is not None
    js_features = re.findall(r"([a-z0-9_]+)\s*:", match.group(1))
    assert js_features == FEATURE_COLUMNS

    # 2. Verify select options in index.html match ALLOWED_CUTOFFS
    select_match = re.search(r'<select id="as-of-date"[^>]*>(.*?)</select>', html_text, flags=re.DOTALL)
    assert select_match is not None
    html_cutoffs = set(re.findall(r'<option value="([^"]+)"', select_match.group(1)))
    assert html_cutoffs == ALLOWED_CUTOFFS

    # 3. Verify uint64 BigInt bound and canonical decimal regex in JS
    assert "const maxUint64 = 18446744073709551615n;" in js_text
    assert "/^(0|[1-9][0-9]*)$/.test(value)" in js_text
    assert "BigInt(value) <= maxUint64" in js_text
    assert 'pattern="0|[1-9][0-9]*"' in html_text
    assert 'maxlength="20"' in html_text

    # 4. Verify batch CSV contract and size limits in JS
    assert "subscriber_key,as_of_date" in js_text
    assert "lines.length > 100" in js_text
    assert "256 * 1024" in js_text

    # 5. Verify all backend routes referenced in app.js are registered on kkbox_app and main_app
    kkbox_openapi_paths = set(kkbox_app.openapi()["paths"].keys())
    main_openapi_paths = set(main_app.openapi()["paths"].keys())
    for endpoint in ("/health", "/v1/features", "/v1/predictions", "/v1/predictions/manual", "/v1/predictions/batch"):
        assert endpoint in js_text
        assert endpoint in kkbox_openapi_paths
        assert endpoint in main_openapi_paths

    # 6. Verify no credential persistence in browser storage
    assert "localStorage.setItem" not in js_text
    assert "sessionStorage.setItem" not in js_text
