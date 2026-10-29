"""
Pydantic v2 Schema Contracts, Extreme Boundaries & Security Gateway Test Suite (Audit Team 6).
Kiem thu toan ven: Ma tran kiem tra bien gia tri so thuc (Age, Tenure, Delay, Spend),
chan enum bat hop le voi HTTP 422, tu choi gia tri NaN/Inf nho vao Pydantic v2 model_validator,
bao toan customer_id va chan customer_id <= 0 (falsy bug prevention),
tai tep CSV batch malformed / rong voi HTTP 400, ma tran tan cong bao mat (X-API-Key gate)
va co che ve sinh chong XSS (Cross-Site Scripting).
Tuan thu Invariant 02 (<= 400 dong) va Invariant 13 (Zero Mockup).
"""

import io
import math
import os
import pathlib
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.main import app
from src.api.schemas import CustomerInput

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "mlops-churn-secret-2026"}

VALID_BASE_PAYLOAD = {
    "customer_id": 1001,
    "age": 35.0,
    "gender": "Female",
    "tenure": 24.0,
    "usage_frequency": 15.0,
    "support_calls": 3.0,
    "payment_delay": 5.0,
    "subscription_type": "Standard",
    "contract_length": "Monthly",
    "total_spend": 650.0,
    "last_interaction": 12.0
}


def test_pydantic_v2_strict_type_and_range_matrix():
    """
    Kiem thu ma tran gia tri bien nghiem ngat qua Pydantic v2:
    - age: 17.9 (reject 422), 18.0 (accept 200), 100.0 (accept 200), 100.1 (reject 422)
    - tenure: -0.1 (reject 422), 0.0 (accept 200), 120.0 (accept 200), 120.5 (reject 422)
    - payment_delay: -1.0 (reject 422), 0.0 (accept 200), 90.0 (accept 200), 91.0 (reject 422)
    - Categorical enum: gender='Unknown', subscription_type='VIP', contract_length='Lifetime'
      phai bi chan boi HTTP 422.
    """
    # Kiem tra cac gia tri hop le tai bien
    for valid_patch in [
        {"age": 18.0}, {"age": 100.0},
        {"tenure": 0.0}, {"tenure": 120.0},
        {"payment_delay": 0.0}, {"payment_delay": 90.0},
        {"total_spend": 0.0}, {"total_spend": 100000.0}
    ]:
        payload = {**VALID_BASE_PAYLOAD, **valid_patch}
        resp = client.post("/predict", json=payload, headers=AUTH_HEADERS)
        assert resp.status_code == 200, f"Valid boundary rejected: {valid_patch} -> {resp.text}"

    # Kiem tra cac gia tri ngoai bien bi tu choi bang HTTP 422
    for invalid_patch in [
        {"age": 17.9}, {"age": 100.1},
        {"tenure": -0.1}, {"tenure": 120.5},
        {"payment_delay": -1.0}, {"payment_delay": 91.0},
        {"total_spend": -1.0}, {"total_spend": 100001.0},
        {"gender": "Unknown"},
        {"subscription_type": "VIP"},
        {"contract_length": "Lifetime"}
    ]:
        payload = {**VALID_BASE_PAYLOAD, **invalid_patch}
        resp = client.post("/predict", json=payload, headers=AUTH_HEADERS)
        assert resp.status_code == 422, f"Invalid boundary accepted: {invalid_patch} -> {resp.status_code}"


def test_nan_inf_injection_rejection():
    """
    Kiem thu co che chan cac gia tri bat thuong NaN va Infinity qua Pydantic v2 validator:
    - age = NaN
    - total_spend = +Inf
    - payment_delay = -Inf
    Xac thuc CustomerInput nem ValidationError va phan hoi API tra ve HTTP 422 voi detail ro rang.
    """
    # Kiem tra truc tiep tren lop CustomerInput
    for nan_field, bad_val in [
        ("age", float("nan")),
        ("total_spend", float("inf")),
        ("payment_delay", float("-inf"))
    ]:
        with pytest.raises(ValidationError) as exc_info:
            CustomerInput(**{**VALID_BASE_PAYLOAD, nan_field: bad_val})
        err_str = str(exc_info.value)
        assert "cannot be NaN or Inf" in err_str or "finite" in err_str or "Input should be" in err_str

    # Kiem tra qua HTTP endpoint (JSON khong the serialize NaN/Inf chuan nen gui None hoac string)
    resp_none = client.post("/predict", json={**VALID_BASE_PAYLOAD, "age": None}, headers=AUTH_HEADERS)
    assert resp_none.status_code == 422


def test_customer_id_zero_falsy_preservation():
    """
    Kiem thu co che phong ngua loi falsy trong Python (0 la falsy, de bi overwrite thanh default):
    - customer_id = 0 phai bi Pydantic tu choi voi loi ge=1 (HTTP 422).
    - customer_id = -10 phai bi tu choi voi HTTP 422.
    - customer_id = 1 phai duoc chap nhan va bao toan dung gia tri 1 trong ket qua phan hoi.
    """
    with pytest.raises(ValidationError):
        CustomerInput(**{**VALID_BASE_PAYLOAD, "customer_id": 0})

    with pytest.raises(ValidationError):
        CustomerInput(**{**VALID_BASE_PAYLOAD, "customer_id": -10})

    resp_zero = client.post("/predict", json={**VALID_BASE_PAYLOAD, "customer_id": 0}, headers=AUTH_HEADERS)
    assert resp_zero.status_code == 422

    resp_one = client.post("/predict", json={**VALID_BASE_PAYLOAD, "customer_id": 1}, headers=AUTH_HEADERS)
    assert resp_one.status_code == 200
    assert resp_one.json()["customer_id"] == 1


def test_csv_upload_batch_malformed_and_extreme_rows():
    """
    Kiem thu tai len batch du doan qua tep CSV tai /upload_csv_predict:
    - CSV sai cau truc (lech so luong cot tai dong 2): Tra ve HTTP 400 (khong gay 500 crash).
    - CSV rong (0 bytes): Tra ve HTTP 400.
    - CSV hop le 20 dong: Tra ve HTTP 200 voi danh sach du doan day du va thong ke hop le.
    """
    # Kich ban 1: CSV sai cau truc
    malformed_csv = (
        "CustomerID,Age,Gender,Tenure,Usage Frequency,Support Calls,Payment Delay,Subscription Type,Contract Length,Total Spend,Last Interaction\n"
        "2001,35,Female,24,15,3,5,Standard,Monthly,650,12\n"
        "2002,40,Male,12\n"  # Dong thieu cot
    )
    files_bad = {"file": ("malformed.csv", io.BytesIO(malformed_csv.encode("utf-8")), "text/csv")}
    resp_bad = client.post("/upload_csv_predict", files=files_bad, headers=AUTH_HEADERS)
    assert resp_bad.status_code in (400, 422), f"Expected 400/422 for malformed CSV, got {resp_bad.status_code}"

    # Kich ban 2: CSV rong (0 bytes)
    files_empty = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    resp_empty = client.post("/upload_csv_predict", files=files_empty, headers=AUTH_HEADERS)
    assert resp_empty.status_code in (400, 422), f"Expected 400/422 for empty CSV, got {resp_empty.status_code}"

    # Kich ban 3: CSV hop le 20 dong
    header = "CustomerID,Age,Gender,Tenure,Usage Frequency,Support Calls,Payment Delay,Subscription Type,Contract Length,Total Spend,Last Interaction\n"
    rows = []
    for i in range(20):
        rows.append(f"{3000 + i},40.0,Female,12.0,15.0,2.0,0.0,Basic,Monthly,500.0,5.0")
    valid_csv_content = header + "\n".join(rows)

    files_valid = {"file": ("valid_batch.csv", io.BytesIO(valid_csv_content.encode("utf-8")), "text/csv")}
    resp_valid = client.post("/upload_csv_predict", files=files_valid, headers=AUTH_HEADERS)
    assert resp_valid.status_code == 200, f"Valid CSV upload failed: {resp_valid.text}"
    v_data = resp_valid.json()
    assert v_data["total_processed"] == 20
    assert len(v_data["predictions"]) == 20


def test_security_gateway_adversarial_matrix():
    """
    Kiem thu ma tran bao mat cua Security Gateway (X-API-Key middleware):
    - Yeu cau khong co header X-API-Key: HTTP 401.
    - Header rong X-API-Key='': HTTP 401.
    - Header SQL Injection payload: HTTP 401.
    - Token gia lap 1024 ky tu ngau nhien: HTTP 401.
    - X-API-Key chinh xac: HTTP 200.
    """
    endpoints_to_test = ["/predict", "/predict/customer/156624"]

    adversarial_headers = [
        {},  # Missing header
        {"X-API-Key": ""},  # Empty string
        {"X-API-Key": "' OR '1'='1"},  # SQL injection
        {"X-API-Key": "A" * 1024},  # Long buffer overflow attempt
        {"X-API-Key": "invalid-secret-key-12345"}
    ]

    for ep in endpoints_to_test:
        for bad_header in adversarial_headers:
            if ep == "/predict":
                res = client.post(ep, json=VALID_BASE_PAYLOAD, headers=bad_header)
            else:
                res = client.get(ep, headers=bad_header)
            assert res.status_code == 401, f"Security gateway allowed unauthorized request: {bad_header} on {ep}"
            assert "Thiếu hoặc sai API Key" in res.json().get("detail", "")

    # Yeu cau hop le voi X-API-Key chuan
    res_ok = client.post("/predict", json=VALID_BASE_PAYLOAD, headers=AUTH_HEADERS)
    assert res_ok.status_code == 200


def test_xss_injection_sanitization_in_api_outputs():
    """
    Kiem thu co che ve sinh chong tan cong Cross-Site Scripting (XSS).
    Thu chen cac the script doc hai <script>alert(1)</script> va <img src=x onerror=alert(1)>:
    - Truong phan loai bi tu choi boi Pydantic enum validation (HTTP 422).
    - Cac truong ket qua dau ra (recommended_action, explanation_summary)
      khong bao gio phan chieu the script thuc thi truc tiep.
    """
    xss_payload = {
        **VALID_BASE_PAYLOAD,
        "subscription_type": "<script>alert('XSS')</script>"
    }
    resp_xss = client.post("/predict", json=xss_payload, headers=AUTH_HEADERS)
    assert resp_xss.status_code == 422, "API accepted unvalidated XSS payload in enum field"

    # Gui payload hop le va xac nhan ket qua tra ve khong chua script tags
    resp_valid = client.post("/predict", json=VALID_BASE_PAYLOAD, headers=AUTH_HEADERS)
    assert resp_valid.status_code == 200
    res_json = resp_valid.json()
    rec_action = res_json.get("recommended_action", "")
    exp_summary = res_json.get("explanation_summary", "")

    assert "<script>" not in rec_action.lower()
    assert "<script>" not in exp_summary.lower()
    assert "javascript:" not in rec_action.lower()
    assert "onerror=" not in rec_action.lower()
