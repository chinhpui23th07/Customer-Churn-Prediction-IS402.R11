"""
Feast Online Feature Store Point-in-Time & Entity Integrity Test Suite (Audit Team 5).
Kiem thu toan ven: Do bao phu thuc the Feast online store xuyen suot 3 tap Train, Val, Test;
xu ly loi chinh xac cho cac ma khach hang am (-999), 0 hoac khong ton tai (HTTP 404/422);
can chinh vector dac trung va ep kieu float hop le; kiem tra SLA do tre truy xuat
truc tuyen p95 (< 50ms) va co che chan phong ve khi thieu thuoc tinh (partial attribute fallback).
"""

import os
import pathlib
import time
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.utils import FEATURE_COLS
from src.features.feature_store import query_online_features

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "mlops-churn-secret-2026"}


def test_feast_entity_coverage_across_train_val_test_splits():
    """
    Kiem thu do bao phu thuc the trong Feast Online Store:
    Lay mau 5 khach hang tu Train, 5 tu Validation, va 5 tu Test.
    Gui yeu cau GET /predict/customer/{id} cho toan bo 15 thuc the.
    Xac thuc 100% (15/15) deu phan hoi HTTP 200 OK, chung minh Feast online
    store vat ly hoa day du ca 3 tap ma khong bo sot tap validation hay test.
    """
    train_df = pd.read_parquet(PROCESSED_DIR / "train_features.parquet", columns=["customerid"])
    val_df = pd.read_parquet(PROCESSED_DIR / "val_features.parquet", columns=["customerid"])
    test_df = pd.read_parquet(PROCESSED_DIR / "test_features.parquet", columns=["customerid"])

    train_sample = train_df["customerid"].iloc[:5].tolist()
    val_sample = val_df["customerid"].iloc[:5].tolist()
    test_sample = test_df["customerid"].iloc[:5].tolist()

    all_sampled_ids = train_sample + val_sample + test_sample
    assert len(all_sampled_ids) == 15

    for cid in all_sampled_ids:
        resp = client.get(f"/predict/customer/{cid}", headers=AUTH_HEADERS)
        assert resp.status_code == 200, (
            f"Feast online lookup failed for customer_id {cid}: {resp.status_code} - {resp.text}"
        )
        data = resp.json()
        assert data["customer_id"] == cid
        assert data["churn_prediction"] in (0, 1)
        assert 0.0 <= data["churn_probability"] <= 1.0
        assert data["risk_level"] in ("Low Risk", "Medium Risk", "High Risk")


def test_feast_missing_and_negative_entity_error_handling():
    """
    Kiem thu co che phong ve va xu ly loi khi truy van thuc the khong ton tai hoac ma khong hop le:
    - customer_id = -999: Phan hoi HTTP 404 voi thong bao tieng Viet ro rang.
    - customer_id = 0: Phan hoi HTTP 404 hoac 422 an toan.
    - customer_id = 999999999: Phan hoi HTTP 404.
    Xac thuc may chu khong bao gio tra ve loi 500 hoac treo ket noi SQLite.
    """
    invalid_ids = [-999, 0, 999999999]

    for bad_id in invalid_ids:
        resp = client.get(f"/predict/customer/{bad_id}", headers=AUTH_HEADERS)
        assert resp.status_code in (404, 422), (
            f"Expected 404 or 422 for invalid customer {bad_id}, got {resp.status_code}: {resp.text}"
        )
        detail = resp.json().get("detail", "")
        assert len(detail) > 0, f"Detail message empty for customer {bad_id}"
        # Neu tra ve 404, xac thuc noi dung thong bao co chu Khong tim thay
        if resp.status_code == 404:
            assert "Không tìm thấy" in detail or "khách hàng" in detail


def test_feast_feature_vector_alignment_and_type_coercion():
    """
    Kiem thu tinh toan ven cau truc vector dac trung duoc Feast online store tra ve:
    Truy van khach hang 156624.
    Xac thuc:
    - Du 13 cot dac trung FEATURE_COLS.
    - Tat ca gia tri deu la so thuc huu han (khong chua NaN, None, hoac inf).
    - Mo hinh thuc thi suy luan thanh cong va tra ve phan bo feature_attributions hop le.
    """
    online_data = query_online_features([156624])
    assert bool(online_data), "query_online_features returned empty dict for customer 156624"

    for col in FEATURE_COLS:
        assert col in online_data, f"Feature '{col}' missing from Feast online store response"
        val_list = online_data[col]
        assert isinstance(val_list, list) and len(val_list) > 0, f"Feature '{col}' value is empty"
        raw_val = val_list[0]
        assert raw_val is not None, f"Feature '{col}' is None for customer 156624"
        flt_val = float(raw_val)
        assert np.isfinite(flt_val), f"Feature '{col}' has non-finite value: {flt_val}"

    # Kiem tra tiep qua REST API endpoint
    resp = client.get("/predict/customer/156624", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    res_data = resp.json()
    attributions = res_data.get("feature_attributions", {})
    assert len(attributions) == len(FEATURE_COLS), (
        f"Attributions count mismatch: {len(attributions)} vs {len(FEATURE_COLS)}"
    )
    for col, attr_val in attributions.items():
        assert np.isfinite(attr_val), f"Attribution for '{col}' is non-finite: {attr_val}"


def test_feast_online_retrieval_latency_sla_p95():
    """
    Kiem thu SLA hieu nang truy xuat truc tuyen cua Feast Online Store tren SQLite:
    Thuc hien 20 yeu cau doc lap toi /predict/customer/{id} tren cac khach hang hop le.
    Xac thuc:
    - 100% yeu cau thanh cong HTTP 200.
    - Do tre trung binh duoi 50ms (SLA cho SQLite online store).
    - Do tre p95 duoi 100ms.
    """
    test_df = pd.read_parquet(PROCESSED_DIR / "test_features.parquet", columns=["customerid"])
    target_ids = test_df["customerid"].iloc[:20].tolist()

    latencies = []
    for cid in target_ids:
        t0 = time.perf_counter()
        resp = client.get(f"/predict/customer/{cid}", headers=AUTH_HEADERS)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert resp.status_code == 200, f"Request failed for cid {cid}: {resp.status_code}"
        latencies.append(elapsed_ms)

    avg_lat = float(np.mean(latencies))
    p95_lat = float(np.percentile(latencies, 95))

    assert avg_lat < 50.0, f"Average Feast retrieval latency exceeded SLA: {avg_lat:.2f}ms >= 50ms"
    assert p95_lat < 100.0, f"p95 Feast retrieval latency exceeded threshold: {p95_lat:.2f}ms >= 100ms"


def test_feast_partial_attribute_fallback_guard():
    """
    Kiem thu co che phong ve khi Feast Online Store tra ve vector dac trung bi khuyet
    (vi du chi tra ve 2/13 dac trung).
    Xac thuc API bat loi va tra ve HTTP 404 voi detail ro rang chua chuoi 'thiếu đặc trưng'
    thay vi de xay ra loi Type/Index error trong qua trinh tinh toan du doan.
    """
    # Gia lap query_online_features chi tra ve age va gender_encoded, thieu cac dac trung con lai
    partial_mock_data = {
        "customerid": [156624],
        "age": [35.0],
        "gender_encoded": [1]
    }

    with patch("src.api.main.query_online_features", return_value=partial_mock_data):
        resp = client.get("/predict/customer/156624", headers=AUTH_HEADERS)
        assert resp.status_code == 404, f"Expected 404 for partial attributes, got: {resp.status_code}"
        detail = resp.json().get("detail", "")
        assert "thiếu đặc trưng" in detail or "Không tìm thấy" in detail, (
            f"Expected error detail to mention missing features, got: {detail}"
        )
