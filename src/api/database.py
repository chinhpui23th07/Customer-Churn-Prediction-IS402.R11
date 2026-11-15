"""
Module quản lý kết nối SQLite tập trung với chế độ WAL (Write-Ahead Logging)
và cơ chế đóng kết nối an toàn trong khối try...finally.
"""
import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator, Union
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INFERENCE_DB = os.path.join(BASE_DIR, "data", "inference_logs.db")


def get_db_connection(db_path: Union[str, Path] = INFERENCE_DB, timeout: float = 10.0) -> sqlite3.Connection:
    """
    Khởi tạo kết nối SQLite với cấu hình đồng thời cao (WAL mode, busy_timeout).
    """
    os.makedirs(os.path.dirname(str(db_path)), exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def ensure_inference_schema(conn: sqlite3.Connection) -> None:
    """Ensure inference_logs has model_version and latency_ms columns."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(inference_logs)").fetchall()}
    if "model_version" not in cols:
        conn.execute("ALTER TABLE inference_logs ADD COLUMN model_version TEXT DEFAULT 'v2.0.0-champion'")
    if "latency_ms" not in cols:
        conn.execute("ALTER TABLE inference_logs ADD COLUMN latency_ms REAL DEFAULT 0.0")
    conn.commit()


@contextmanager
def sqlite_connection(db_path: Union[str, Path] = INFERENCE_DB, timeout: float = 10.0) -> Iterator[sqlite3.Connection]:
    """
    Context manager quản lý vòng đời kết nối SQLite an toàn với WAL mode
    và đảm bảo giải phóng tài nguyên qua khối try...finally: conn.close().
    """
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=timeout)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        yield conn
    finally:
        if conn is not None:
            conn.close()
