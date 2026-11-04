"""The local KKBox demo must serve its own assets and current API contract."""

from fastapi.testclient import TestClient

from src.kkbox.api import app


def test_demo_and_assets_are_served_by_kkbox_app():
    client = TestClient(app)
    page = client.get("/demo")
    style = client.get("/demo/assets/style.css")
    script = client.get("/demo/assets/app.js")
    favicon = client.get("/demo/assets/favicon.svg")

    assert page.status_code == style.status_code == script.status_code == favicon.status_code == 200
    assert 'id="subscriber-key"' in page.text
    assert 'id="as-of-date"' in page.text
    assert 'id="api-key"' in page.text
    assert 'type="number" id="inp-customer-id"' not in page.text
    assert "/v1/predictions" in script.text
    assert "localStorage.setItem" not in script.text
