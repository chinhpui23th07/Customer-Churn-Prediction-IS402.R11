"""Comprehensive Concurrency and Decoupled Producer-Job Tests.

Verifies distributed locking (Redis / File TTL), concurrency rejection (HTTP 409),
asynchronous job execution (HTTP 202), artifact persistence, and hot-reload.
"""
import os
import shutil
import tempfile
import threading
import time
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes_management import JOB_MANAGER
from src.models.retraining_job import (
    DistributedRetrainLock,
    RetrainingJobManager,
    RetrainingJobTicket,
)
from src.resilience.azurite_adapter import AzuriteStorageAdapter

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "mlops-churn-secret-2026"}


@pytest.fixture(autouse=True)
def clean_job_manager_lock():
    """Ensure global JOB_MANAGER lock is released and workers joined before and after each test."""
    JOB_MANAGER.lock.force_release()
    yield
    for th in threading.enumerate():
        if th.name.startswith("RetrainJobWorker-") and th.is_alive():
            th.join(timeout=1.0)
    JOB_MANAGER.lock.force_release()


@pytest.fixture
def temp_env():
    """Create isolated temporary directory for lock and jobs storage."""
    temp_dir = tempfile.mkdtemp(prefix="churnguard_test_")
    lock_file = os.path.join(temp_dir, "test_lock.json")
    jobs_dir = os.path.join(temp_dir, "jobs")
    os.makedirs(jobs_dir, exist_ok=True)
    yield {"temp_dir": temp_dir, "lock_file": lock_file, "jobs_dir": jobs_dir}
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_distributed_lock_acquire_and_release(temp_env):
    """Verify lock acquisition returns token and release cleans up."""
    lock = DistributedRetrainLock(lock_file=temp_env["lock_file"])
    assert not lock.is_locked()

    token = lock.acquire(ttl_seconds=30)
    assert token is not None
    assert lock.is_locked()
    assert lock.current_token == token

    info = lock.get_lock_info()
    assert info["locked"] is True
    assert info["remaining_ttl_seconds"] > 0

    assert lock.release(token) is True
    assert not lock.is_locked()


def test_distributed_lock_concurrency_rejection(temp_env):
    """Verify second replica is rejected when lock is held."""
    lock1 = DistributedRetrainLock(lock_file=temp_env["lock_file"])
    lock2 = DistributedRetrainLock(lock_file=temp_env["lock_file"])

    token1 = lock1.acquire(ttl_seconds=60)
    assert token1 is not None

    token2 = lock2.acquire(ttl_seconds=60)
    assert token2 is None, "Second lock acquisition should fail while first is active"

    # Mismatched token release must fail
    assert lock2.release("bogus-token") is False

    # Proper release enables subsequent acquisition
    assert lock1.release(token1) is True
    token2_retry = lock2.acquire(ttl_seconds=60)
    assert token2_retry is not None
    lock2.release(token2_retry)


def test_distributed_lock_ttl_expiration(temp_env):
    """Verify stale lock with expired TTL is automatically reclaimed."""
    lock = DistributedRetrainLock(lock_file=temp_env["lock_file"])
    token = lock.acquire(ttl_seconds=1)
    assert token is not None
    assert lock.is_locked()

    time.sleep(1.15)
    # Lock should now be considered expired
    assert not lock.is_locked()

    # New acquisition must succeed despite stale lock file
    new_token = lock.acquire(ttl_seconds=10)
    assert new_token is not None
    lock.release(new_token)


def test_distributed_lock_force_release(temp_env):
    """Verify emergency force release clears held lock."""
    lock = DistributedRetrainLock(lock_file=temp_env["lock_file"])
    token = lock.acquire(ttl_seconds=100)
    assert token is not None
    assert lock.is_locked()

    assert lock.force_release() is True
    assert not lock.is_locked()


def test_job_ticket_persistence_and_retrieval(temp_env):
    """Verify ticket state is persisted to disk and queryable."""
    ticket = RetrainingJobTicket(
        ticket_id="ticket-001",
        status="PENDING",
        created_at="2026-11-02 12:00:00 UTC",
        mode="production",
    )
    ticket.save(jobs_dir=temp_env["jobs_dir"])

    manager = RetrainingJobManager(jobs_dir=temp_env["jobs_dir"])
    loaded = manager.get_job("ticket-001")
    assert loaded is not None
    assert loaded.ticket_id == "ticket-001"
    assert loaded.status == "PENDING"
    assert loaded.mode == "production"


def test_decoupled_retrain_endpoint_returns_202_accepted():
    """Verify triggering decoupled retrain returns HTTP 202 with ticket."""
    JOB_MANAGER.lock.force_release()
    response = client.post("/api/v1/trigger_retrain?force=true&decoupled=true&dry_run=true", headers=AUTH_HEADERS)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ACCEPTED"
    assert "ticket_id" in data
    assert "status_endpoint" in data
    ticket_id = data["ticket_id"]

    # Poll status endpoint until background worker completes to prevent race condition
    final_status = None
    for _ in range(40):
        status_res = client.get(f"/api/v1/retrain_jobs/{ticket_id}", headers=AUTH_HEADERS)
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["ticket_id"] == ticket_id
        final_status = status_data["status"]
        if final_status in ["COMPLETED", "FAILED"]:
            break
        time.sleep(0.05)

    assert final_status in ["COMPLETED", "RUNNING", "PENDING"]


def test_decoupled_retrain_concurrency_returns_409():
    """Verify simultaneous trigger attempts return HTTP 409 Conflict."""
    JOB_MANAGER.lock.force_release()
    # Lock manually to guarantee conflict state
    token = JOB_MANAGER.lock.acquire(ttl_seconds=60)
    assert token is not None

    try:
        response = client.post("/api/v1/trigger_retrain?force=true&decoupled=true&dry_run=true", headers=AUTH_HEADERS)
        assert response.status_code == 409
        detail = response.json().get("detail", "")
        assert "lock active" in detail or "running" in detail.lower()
    finally:
        JOB_MANAGER.lock.release(token)
        JOB_MANAGER.lock.force_release()


def test_retrain_lock_status_endpoint():
    """Verify lock diagnostics endpoint reports active state."""
    JOB_MANAGER.lock.force_release()
    res1 = client.get("/api/v1/retrain_lock/status", headers=AUTH_HEADERS)
    assert res1.status_code == 200
    assert res1.json()["locked"] is False

    token = JOB_MANAGER.lock.acquire(ttl_seconds=60)
    try:
        res2 = client.get("/api/v1/retrain_lock/status", headers=AUTH_HEADERS)
        assert res2.status_code == 200
        assert res2.json()["locked"] is True
        assert res2.json()["remaining_ttl_seconds"] > 0
    finally:
        JOB_MANAGER.lock.release(token)


def test_retrain_job_not_found_returns_404():
    """Verify unknown ticket ID returns HTTP 404."""
    response = client.get("/api/v1/retrain_jobs/invalid-ticket-99999", headers=AUTH_HEADERS)
    assert response.status_code == 404


def test_storage_adapter_ticket_persistence(temp_env):
    """Verify ticket syncs to AzuriteStorageAdapter container."""
    adapter = AzuriteStorageAdapter(force_fallback=True)
    ticket = RetrainingJobTicket(
        ticket_id="ticket-azurite-01",
        status="COMPLETED",
        created_at="2026-11-02 14:00:00 UTC",
        mode="production",
    )
    ticket.save(jobs_dir=temp_env["jobs_dir"], storage_adapter=adapter)

    # Confirm blob exists in fallback store
    raw_data = adapter.download_blob("retrain-jobs", "ticket-azurite-01.json")
    assert b"ticket-azurite-01" in raw_data


def test_hot_reload_hook_signaled(temp_env):
    """Verify hot-reload callback is triggered when job worker completes."""
    reloaded = []

    def mock_reload():
        reloaded.append(True)

    lock = DistributedRetrainLock(lock_file=temp_env["lock_file"])
    manager = RetrainingJobManager(lock=lock, jobs_dir=temp_env["jobs_dir"])
    manager.reload_hook = mock_reload

    ticket, reason = manager.start_job(dry_run=True, force=True)
    assert reason == "ACCEPTED"
    assert ticket is not None

    # Wait briefly for worker thread to finish dry run
    for _ in range(30):
        time.sleep(0.1)
        check = manager.get_job(ticket.ticket_id)
        if check and check.status in ["COMPLETED", "FAILED"]:
            break

    assert len(reloaded) == 1
    assert check.hot_reload_signaled is True
