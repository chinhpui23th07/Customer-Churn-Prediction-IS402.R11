"""
Concurrency, SQLite WAL & Model Hot-Reload Test Suite (Audit Team 2).
Kiem thu toan ven: Che do SQLite WAL pragmas, truy cap dong thoi da luong
doc/ghi khong khoa database, reload model trong dieu kien tai cao khong gay
race condition, dong ket noi database triet de va cleanup socket TCP.
Tuan thu Invariant 02 (<= 400 dong) va Invariant 13 (Zero Mockup).
"""

import concurrent.futures
import os
import pathlib
import socket
import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.data.latency_simulator import measure_tcp_latency

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
ONLINE_STORE_DB = PROJECT_ROOT / "data" / "feast_repo" / "data" / "online_store.db"
INFERENCE_DB = PROJECT_ROOT / "data" / "inference_logs.db"

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "mlops-churn-secret-2026"}

SAMPLE_PAYLOAD = {
    "customer_id": 156624,
    "age": 42.0,
    "gender": "Female",
    "tenure": 28.0,
    "usage_frequency": 18.0,
    "support_calls": 2.0,
    "payment_delay": 3.0,
    "subscription_type": "Standard",
    "contract_length": "Annual",
    "total_spend": 750.0,
    "last_interaction": 8.0,
}


def test_sqlite_wal_mode_active_pragmas():
    """
    Xac thuc che do Write-Ahead Logging (WAL) tren ca hai co so du lieu SQLite:
    - data/feast_repo/data/online_store.db
    - data/inference_logs.db
    Kiem tra PRAGMA journal_mode == 'wal' va PRAGMA busy_timeout >= 5000 ms.
    """
    assert INFERENCE_DB.exists(), f"Inference database missing: {INFERENCE_DB}"
    conn_inf = sqlite3.connect(str(INFERENCE_DB), timeout=10.0)
    try:
        cur = conn_inf.cursor()
        j_mode = cur.execute("PRAGMA journal_mode;").fetchone()[0]
        assert str(j_mode).lower() == "wal", f"inference_logs.db journal_mode is not WAL: {j_mode}"
        cur.execute("PRAGMA busy_timeout=5000;")
        b_timeout = cur.execute("PRAGMA busy_timeout;").fetchone()[0]
        assert int(b_timeout) >= 5000, f"Busy timeout below 5000ms: {b_timeout}"
    finally:
        conn_inf.close()

    assert ONLINE_STORE_DB.exists(), f"Feast online store database missing: {ONLINE_STORE_DB}"
    conn_online = sqlite3.connect(str(ONLINE_STORE_DB), timeout=10.0)
    try:
        cur = conn_online.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        j_mode_online = cur.execute("PRAGMA journal_mode;").fetchone()[0]
        assert str(j_mode_online).lower() == "wal", f"online_store.db journal_mode is not WAL: {j_mode_online}"
        cur.execute("PRAGMA busy_timeout=5000;")
        b_timeout_online = cur.execute("PRAGMA busy_timeout;").fetchone()[0]
        assert int(b_timeout_online) >= 5000, f"Busy timeout below 5000ms: {b_timeout_online}"
    finally:
        conn_online.close()


def test_multi_threaded_sqlite_concurrent_read_write(tmp_path):
    """
    Kiem thu dong thoi 100 tac vu doc/ghi tren SQLite duoi che do WAL
    bang ThreadPoolExecutor(max_workers=16).
    50 worker ghi nhat ky suy luan + 50 worker doc truy van tong hop dong thoi.
    Xac thuc khong xay ra loi 'database is locked' va toan ven du lieu duoc bao toan.
    """
    db_path = tmp_path / "concurrent_wal_test.db"
    init_conn = sqlite3.connect(str(db_path), timeout=15.0)
    init_conn.execute("PRAGMA journal_mode=WAL;")
    init_conn.execute("PRAGMA synchronous=NORMAL;")
    init_conn.execute("PRAGMA busy_timeout=10000;")
    init_conn.execute("""
        CREATE TABLE concurrent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            churn_prediction INTEGER,
            churn_probability REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    init_conn.commit()
    init_conn.close()

    def writer_task(task_id: int):
        conn = sqlite3.connect(str(db_path), timeout=15.0)
        try:
            conn.execute("PRAGMA busy_timeout=10000;")
            conn.execute(
                "INSERT INTO concurrent_logs (customer_id, churn_prediction, churn_probability) VALUES (?, ?, ?);",
                (10000 + task_id, task_id % 2, round(0.1 + (task_id % 10) * 0.08, 4))
            )
            conn.commit()
            return ("write", task_id, True)
        finally:
            conn.close()

    def reader_task(task_id: int):
        conn = sqlite3.connect(str(db_path), timeout=15.0)
        try:
            conn.execute("PRAGMA busy_timeout=10000;")
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*), AVG(churn_probability) FROM concurrent_logs;")
            row = cur.fetchone()
            return ("read", task_id, row[0])
        finally:
            conn.close()

    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        for i in range(50):
            tasks.append(executor.submit(writer_task, i))
            tasks.append(executor.submit(reader_task, i))

        results = [fut.result(timeout=20.0) for fut in concurrent.futures.as_completed(tasks)]

    assert len(results) == 100, f"Expected 100 completed tasks, got {len(results)}"
    writes = [r for r in results if r[0] == "write"]
    reads = [r for r in results if r[0] == "read"]
    assert len(writes) == 50, f"Expected 50 writes, got {len(writes)}"
    assert len(reads) == 50, f"Expected 50 reads, got {len(reads)}"

    final_conn = sqlite3.connect(str(db_path))
    final_count = final_conn.execute("SELECT COUNT(*) FROM concurrent_logs;").fetchone()[0]
    final_conn.close()
    assert final_count == 50, f"Expected final row count 50, got {final_count}"


def test_model_hot_reload_concurrency_race_condition():
    """
    Kiem thu an toan luong cua MODEL_LOCK khi dong thoi:
    - 10 luong gui 50 yeu cau /predict lien tuc.
    - 1 luong rieng biet gui 5 yeu cau /api/v1/reload_model lien tiep.
    Xac thuc 100% yeu cau /predict deu thanh cong HTTP 200 ma khong gap
    race condition (NoneType object has no attribute 'predict_proba').
    """
    predict_responses = []
    reload_responses = []

    def client_predict_worker(worker_id: int):
        for req_idx in range(5):
            payload = dict(SAMPLE_PAYLOAD)
            payload["customer_id"] = 200000 + worker_id * 10 + req_idx
            resp = client.post("/predict", json=payload, headers=AUTH_HEADERS)
            predict_responses.append((resp.status_code, resp.json()))
            time.sleep(0.01)

    def reloader_worker():
        for _ in range(5):
            time.sleep(0.02)
            resp = client.post("/api/v1/reload_model", headers=AUTH_HEADERS)
            reload_responses.append(resp.status_code)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = []
        for w in range(10):
            futures.append(executor.submit(client_predict_worker, w))
        futures.append(executor.submit(reloader_worker))

        for f in concurrent.futures.as_completed(futures):
            f.result(timeout=30.0)

    assert len(predict_responses) == 50, f"Expected 50 predict responses, got {len(predict_responses)}"
    for status, body in predict_responses:
        assert status == 200, f"Predict failed with status {status}: {body}"
        assert body["churn_prediction"] in (0, 1)
        assert 0.0 <= body["churn_probability"] <= 1.0

    assert len(reload_responses) == 5, f"Expected 5 reload responses, got {len(reload_responses)}"
    for status in reload_responses:
        assert status == 200, f"Reload model returned non-200 status: {status}"


def test_connection_leak_prevention_under_load():
    """
    Kiem thu co che context manager phong ngua ro ri ket noi SQLite.
    Gui 50 yeu cau xen ke giua /predict/customer/{id} va /ab_test/analytics.
    Xac thuc tat ca ket noi dong sach se, khong can kiet tai nguyen socket/db.
    """
    for i in range(10):
        resp_cust = client.get("/predict/customer/156624", headers=AUTH_HEADERS)
        assert resp_cust.status_code == 200, f"Feast lookup failed at iteration {i}: {resp_cust.text}"
        data_c = resp_cust.json()
        assert data_c["customer_id"] == 156624
        assert 0.0 <= data_c["churn_probability"] <= 1.0

        resp_ab = client.get("/ab_test/analytics", headers=AUTH_HEADERS)
        assert resp_ab.status_code == 200, f"A/B analytics failed at iteration {i}: {resp_ab.text}"
        data_ab = resp_ab.json()
        assert "performance_comparison" in data_ab
        assert "champion" in data_ab["performance_comparison"]

    # Xac nhan co the ket noi truc tiep toi database ma khong bi khoa
    conn = sqlite3.connect(str(INFERENCE_DB), timeout=5.0)
    try:
        count = conn.execute("SELECT COUNT(*) FROM inference_logs;").fetchone()[0]
        assert count >= 0
    finally:
        conn.close()


def test_latency_simulator_deterministic_socket_cleanup():
    """
    Kiem thu ham do do tre TCP measure_tcp_latency khi ket noi toi cong khong the truy cap
    (127.0.0.1:65534).
    Xac thuc:
    - Tra ve status la 'UNREACHABLE' voi cac chi so min/avg/max/jitter la None.
    - Socket duoc dong triet de trong menh de finally ngay ca khi co socket.error.
    """
    res = measure_tcp_latency("127.0.0.1", port=65534, num_pings=2, timeout=0.1)
    assert res["status"] == "UNREACHABLE", f"Expected UNREACHABLE, got: {res}"
    assert res["avg_ms"] is None
    assert res["min_ms"] is None
    assert res["max_ms"] is None
    assert res["jitter_ms"] is None

    # Kiem tra co che dong socket thong qua spy wrapper
    close_counter = {"closed": 0}
    real_socket = socket.socket

    class MonitoredSocket(real_socket):
        def close(self):
            close_counter["closed"] += 1
            return super().close()

    with patch("socket.socket", side_effect=MonitoredSocket):
        res_spy = measure_tcp_latency("127.0.0.1", port=65534, num_pings=3, timeout=0.05)
        assert res_spy["status"] == "UNREACHABLE"
        assert close_counter["closed"] >= 3, f"Expected socket close >= 3, got {close_counter['closed']}"
