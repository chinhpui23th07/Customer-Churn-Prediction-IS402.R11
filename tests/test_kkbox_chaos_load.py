"""WAF Reliability (RE:08 & RE:09) Chaos Engineering & Concurrent Load Testing.

Tests KKBox Subscriber Churn Prediction pipeline under concurrent traffic
combined with active fault injection (transient failures, network storms,
and upstream Redis / Feast outages).
Validates Fowler Circuit Breaker state transitions, Bulkhead isolation,
exponential backoff retry policies, and graceful fallback degradation.
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
from typing import Any, Dict, List

import pytest

from src.resilience.azurite_adapter import (
    configure_azurite_testcontainer,
    get_azurite_docker_command,
)
from src.resilience.bulkhead import Bulkhead, BulkheadFullException
from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitState,
)
from src.resilience.resilience_pipeline import ResiliencePipelineBuilder
from src.resilience.retry_policy import MaxRetriesExceededException, RetryPolicy


def test_azurite_version_negotiation_command_generation() -> None:
    """Verify Azurite CLI and container commands include --skipApiVersionCheck per WAF guide."""
    cmd = get_azurite_docker_command(host="127.0.0.1", blob_port=10000, skip_api_version_check=True)
    assert "--skipApiVersionCheck" in cmd
    assert "10000:10000" in cmd[4]
    assert "azurite:latest" in cmd[5]

    cmd_no_skip = get_azurite_docker_command(skip_api_version_check=False)
    assert "--skipApiVersionCheck" not in cmd_no_skip

    class MockContainer:
        def __init__(self) -> None:
            self.command: str = ""

        def with_command(self, cmd_str: str) -> MockContainer:
            self.command = cmd_str
            return self

    mock = MockContainer()
    configured = configure_azurite_testcontainer(mock, skip_api_version_check=True)
    assert "--skipApiVersionCheck" in configured.command


def test_chaos_transient_failure_recovery_under_load() -> None:
    """Simulate 16 concurrent KKBox prediction calls under transient network flakiness.

    Verifies RetryPolicy with exponential backoff & full jitter recovers all calls.
    """
    retry_policy = RetryPolicy(
        name="kkbox_transient_retry",
        max_attempts=4,
        initial_backoff=0.01,
        backoff_factor=1.5,
        max_backoff=0.05,
    )

    call_counters: Dict[int, int] = {}
    lock = threading.Lock()

    def _flaky_kkbox_inference(worker_id: int) -> Dict[str, Any]:
        with lock:
            count = call_counters.get(worker_id, 0) + 1
            call_counters[worker_id] = count

        # First 2 attempts fail with simulated Azure network reset
        if count < 3:
            raise ConnectionResetError(f"Worker {worker_id} transient TCP reset on attempt {count}")

        return {
            "worker_id": worker_id,
            "prediction": 1,
            "churn_probability": 0.72,
            "risk_level": "high",
            "recovered_on_attempt": count,
        }

    def _execute_worker(worker_id: int) -> Dict[str, Any]:
        return retry_policy.execute(_flaky_kkbox_inference, worker_id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_execute_worker, i) for i in range(16)]
        results = [f.result(timeout=5.0) for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 16
    for r in results:
        assert r["recovered_on_attempt"] == 3
        assert r["prediction"] == 1
        assert r["risk_level"] == "high"


def test_chaos_storm_circuit_breaker_trip_and_fast_fail() -> None:
    """Simulate upstream Feast feature store outage under high-throughput request storm.

    Verifies CircuitBreaker trips to OPEN after threshold and fast-fails in < 5ms.
    """
    breaker = CircuitBreaker(
        name="kkbox_feature_breaker",
        failure_threshold=4,
        recovery_timeout=0.1,
        half_open_trials=1,
    )
    assert breaker.state == CircuitState.CLOSED

    def _failing_feast_call() -> None:
        raise TimeoutError("Feast online Redis socket timed out under storm")

    # Trip the circuit breaker
    failed_count = 0
    for _ in range(4):
        try:
            breaker.call(_failing_feast_call)
        except TimeoutError:
            failed_count += 1

    assert failed_count == 4
    assert breaker.state == CircuitState.OPEN

    # Fast-fail test: 20 rapid calls must be rejected immediately without locking
    start_time = time.perf_counter()
    fast_fail_count = 0
    for _ in range(20):
        try:
            breaker.call(lambda: "should_never_execute")
        except CircuitBreakerOpenException:
            fast_fail_count += 1
    duration = time.perf_counter() - start_time

    assert fast_fail_count == 20
    assert duration < 0.05, f"Fast-fail exceeded SLA: {duration:.4f}s for 20 calls"


def test_chaos_circuit_breaker_recovery_half_open() -> None:
    """Test automated self-healing from OPEN to HALF_OPEN to CLOSED after recovery window."""
    breaker = CircuitBreaker(
        name="kkbox_healing_breaker",
        failure_threshold=2,
        recovery_timeout=0.06,
        half_open_trials=1,
    )

    for _ in range(2):
        with pytest.raises(RuntimeError):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("Outage")))

    assert breaker.state == CircuitState.OPEN
    time.sleep(0.08)
    assert breaker.state == CircuitState.HALF_OPEN

    # Successful trial call restores circuit to CLOSED
    trial_res = breaker.call(lambda: {"status": "healthy", "features": [1.0] * 12})
    assert trial_res["status"] == "healthy"
    assert breaker.state == CircuitState.CLOSED


def test_chaos_bulkhead_concurrency_saturation() -> None:
    """Test Bulkhead limits thread saturation to prevent server thread pool starvation."""
    bulkhead = Bulkhead(name="kkbox_inference_bulkhead", max_concurrent_calls=3, max_wait_duration=0.04)
    started_count = 0
    started_event = threading.Event()
    release_event = threading.Event()
    lock = threading.Lock()

    def _heavy_inference() -> str:
        nonlocal started_count
        with bulkhead:
            with lock:
                started_count += 1
                if started_count >= 3:
                    started_event.set()
            release_event.wait(timeout=2.0)
        return "inference_done"

    threads = [threading.Thread(target=_heavy_inference, daemon=True) for _ in range(3)]
    for t in threads:
        t.start()

    assert started_event.wait(timeout=2.0) is True
    assert bulkhead.active_calls == 3

    # 4th concurrent request must be rejected with BulkheadFullException
    with pytest.raises(BulkheadFullException):
        with bulkhead:
            pass

    release_event.set()
    for t in threads:
        t.join(timeout=2.0)

    assert bulkhead.active_calls == 0


def test_chaos_pipeline_graceful_degradation_fallback() -> None:
    """End-to-End Resilience Pipeline test combining Bulkhead, Breaker, Retry & Fallback.

    Verifies client receives safe baseline churn prediction when backend fails completely.
    """
    breaker = CircuitBreaker(name="pipe_cb", failure_threshold=2, recovery_timeout=0.05)
    retry = RetryPolicy(name="pipe_retry", max_attempts=2, initial_backoff=0.01)
    bulkhead = Bulkhead(name="pipe_bh", max_concurrent_calls=5)

    def _fallback_handler(exc: Exception) -> Dict[str, Any]:
        return {
            "prediction": 0,
            "churn_probability": 0.5,
            "risk_level": "medium",
            "prediction_mode": "fallback_degraded",
            "reason": str(exc),
            "fallback": True,
        }

    pipeline = (
        ResiliencePipelineBuilder("kkbox_end_to_end_resilience")
        .add_bulkhead(bulkhead)
        .add_circuit_breaker(breaker)
        .add_retry_policy(retry)
        .with_fallback(_fallback_handler)
        .build()
    )

    # 1. Normal execution returns real prediction
    res_normal = pipeline.execute(lambda x: {"prediction": 1, "churn_probability": x, "fallback": False}, 0.88)
    assert res_normal["fallback"] is False
    assert res_normal["prediction"] == 1
    assert res_normal["churn_probability"] == 0.88

    # 2. Total failure triggers graceful fallback without raising unhandled exception
    def _crashed_upstream() -> None:
        raise ConnectionRefusedError("Azure Redis and Azurite endpoints completely offline")

    res_degraded = pipeline.execute(_crashed_upstream)
    assert res_degraded["fallback"] is True
    assert res_degraded["prediction_mode"] == "fallback_degraded"
    assert res_degraded["churn_probability"] == 0.5
    assert "ConnectionRefusedError" in res_degraded["reason"]
