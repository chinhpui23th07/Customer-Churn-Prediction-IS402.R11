"""Integration and Verification Tests for Cloud Resilience Architecture.

Tests Circuit Breaker Fowler state machine, Retry Policy with Full Jitter,
Bulkhead concurrency limiter, Azurite dual-mode storage adapter, and
Testcontainers ephemeral Docker containers (with Docker offline guard).
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from src.resilience.azurite_adapter import AzuriteStorageAdapter, InMemoryBlobStore
from src.resilience.bulkhead import Bulkhead, BulkheadFullException
from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitState,
)
from src.resilience.resilience_pipeline import ResiliencePipelineBuilder
from src.resilience.retry_policy import MaxRetriesExceededException, RetryPolicy


def is_docker_running() -> bool:
    """Check if Docker Desktop engine is online without throwing unhandled exceptions."""
    try:
        import docker
        client = docker.from_env(timeout=1)
        client.ping()
        return True
    except Exception:
        return False


def test_circuit_breaker_fowler_state_transitions() -> None:
    """Test CLOSED -> OPEN on failure threshold -> HALF-OPEN on recovery -> CLOSED."""
    breaker = CircuitBreaker(
        name="test_breaker",
        failure_threshold=3,
        recovery_timeout=0.05,
        half_open_trials=1,
    )
    assert breaker.state == CircuitState.CLOSED
    assert breaker.is_call_permitted() is True

    # 1. Successful execution
    res = breaker.call(lambda x: x * 2, 21)
    assert res == 42
    assert breaker.state == CircuitState.CLOSED

    # 2. Trigger failures until threshold breached
    def _faulty_call() -> None:
        raise ConnectionResetError("Remote Azure service dropped connection")

    for _ in range(3):
        with pytest.raises(ConnectionResetError):
            breaker.call(_faulty_call)

    assert breaker.state == CircuitState.OPEN

    # 3. Fast-fail while OPEN
    with pytest.raises(CircuitBreakerOpenException) as exc_info:
        breaker.call(lambda: "should_not_run")
    assert "is OPEN" in str(exc_info.value)

    # 4. Wait for recovery timeout to transition to HALF-OPEN
    time.sleep(0.06)
    assert breaker.state == CircuitState.HALF_OPEN

    # 5. Successful half-open execution recovers breaker to CLOSED
    recovered_res = breaker.call(lambda: "recovered")
    assert recovered_res == "recovered"
    assert breaker.state == CircuitState.CLOSED


def test_circuit_breaker_half_open_failure_reopens() -> None:
    """Test HALF-OPEN reverts to OPEN when trial execution fails."""
    breaker = CircuitBreaker(name="trial_breaker", failure_threshold=1, recovery_timeout=0.04)
    with pytest.raises(RuntimeError):
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))

    assert breaker.state == CircuitState.OPEN
    time.sleep(0.05)
    assert breaker.state == CircuitState.HALF_OPEN

    # Trial fails -> back to OPEN
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError("trial failed")))
    assert breaker.state == CircuitState.OPEN


def test_circuit_breaker_manual_controls() -> None:
    """Test manual trip and reset capabilities."""
    breaker = CircuitBreaker(name="manual_breaker")
    assert breaker.state == CircuitState.CLOSED
    breaker.trip()
    assert breaker.state == CircuitState.OPEN
    breaker.reset()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.get_metrics()["state"] == "CLOSED"


def test_retry_policy_exponential_backoff_and_jitter() -> None:
    """Test retry policy execution, jitter range, and max retry exhaustion."""
    policy = RetryPolicy(
        name="test_retry",
        max_attempts=3,
        initial_backoff=0.01,
        backoff_factor=2.0,
        max_backoff=0.05,
    )

    # Verify jitter calculation is bounded
    for attempt in range(1, 5):
        delay = policy.calculate_delay(attempt)
        assert 0.0 <= delay <= 0.05

    # Test transient failure with recovery on 2nd attempt
    attempts_recorded = []

    def _flaky_service() -> str:
        attempts_recorded.append(time.time())
        if len(attempts_recorded) < 2:
            raise TimeoutError("Transient Redis socket timeout")
        return "online_feature_retrieved"

    result = policy.execute(_flaky_service)
    assert result == "online_feature_retrieved"
    assert len(attempts_recorded) == 2

    # Test persistent failure exhausts retries
    def _permanent_failure() -> None:
        raise ConnectionRefusedError("Redis down")

    with pytest.raises(MaxRetriesExceededException) as exc_info:
        policy.execute(_permanent_failure)
    assert "exhausted all 3 attempts" in str(exc_info.value)


def test_bulkhead_concurrency_isolation() -> None:
    """Test bounded semaphore bulkhead prevents thread starvation."""
    bulkhead = Bulkhead(name="test_bulkhead", max_concurrent_calls=2, max_wait_duration=0.05)
    started_event = threading.Event()
    release_event = threading.Event()
    results = []

    def _slow_task(task_id: int) -> None:
        with bulkhead:
            results.append(f"task_{task_id}_active")
            if len(results) >= 2:
                started_event.set()
            release_event.wait(timeout=1.0)

    # Launch 2 background threads to saturate the bulkhead
    t1 = threading.Thread(target=_slow_task, args=(1,), daemon=True)
    t2 = threading.Thread(target=_slow_task, args=(2,), daemon=True)
    t1.start()
    t2.start()

    started_event.wait(timeout=1.0)
    assert bulkhead.active_calls == 2

    # 3rd thread attempt must be rejected with BulkheadFullException
    with pytest.raises(BulkheadFullException):
        with bulkhead:
            pass

    # Release workers
    release_event.set()
    t1.join(timeout=1.0)
    t2.join(timeout=1.0)
    assert bulkhead.active_calls == 0


def test_azurite_adapter_in_memory_fallback() -> None:
    """Test Azurite storage adapter offline in-memory fallback semantics."""
    adapter = AzuriteStorageAdapter(force_fallback=True)
    assert adapter.is_using_fallback is True

    container = "churnguard-datasets"
    blob_name = "test_features.parquet"
    test_data = b"churn-features-mock-parquet-data"

    # 1. Upload blob
    assert adapter.upload_blob(container, blob_name, test_data) is True
    assert adapter.exists(container, blob_name) is True

    # 2. Download blob
    retrieved = adapter.download_blob(container, blob_name)
    assert retrieved == test_data

    # 3. List blobs
    blobs = adapter.list_blobs(container)
    assert blob_name in blobs

    # 4. Delete blob
    assert adapter.delete_blob(container, blob_name) is True
    assert adapter.exists(container, blob_name) is False

    # 5. Non-existent download raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        adapter.download_blob(container, "nonexistent.bin")


def test_resilience_pipeline_end_to_end() -> None:
    """Test unified pipeline combining Bulkhead, Breaker, Retry, and Fallback."""
    breaker = CircuitBreaker(name="pipe_cb", failure_threshold=2, recovery_timeout=0.05)
    retry = RetryPolicy(name="pipe_retry", max_attempts=2, initial_backoff=0.01)
    bulkhead = Bulkhead(name="pipe_bh", max_concurrent_calls=5)

    pipeline = (
        ResiliencePipelineBuilder("churn_serving_pipeline")
        .add_bulkhead(bulkhead)
        .add_circuit_breaker(breaker)
        .add_retry_policy(retry)
        .with_fallback(lambda exc: {"status": "degraded", "prediction": 0.5, "fallback": True})
        .build()
    )

    # 1. Healthy execution
    res = pipeline.execute(lambda x: {"status": "success", "prediction": x}, 0.85)
    assert res["status"] == "success"
    assert res["prediction"] == 0.85

    # 2. Failing execution gracefully handled by Fallback
    def _failing_api() -> Any:
        raise ConnectionError("Upstream MLflow Model Registry unreachable")

    fallback_res = pipeline.execute(_failing_api)
    assert fallback_res["status"] == "degraded"
    assert fallback_res["fallback"] is True


@pytest.mark.skipif(not is_docker_running(), reason="Docker daemon is offline; skipping ephemeral container test")
def test_testcontainers_live_container() -> None:
    """Integration test against disposable Testcontainers container (when Docker daemon is online)."""
    from testcontainers.core.container import DockerContainer
    with DockerContainer("redis:alpine").with_exposed_ports(6379) as container:
        port = container.get_exposed_port(6379)
        assert port is not None
        assert int(port) > 0
