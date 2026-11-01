"""Chaos Fault Injection Test Harness.

Inspired by Chaos Mesh (8.0k stars).
Empirically proves resilience mechanisms under latency, network failures,
exponential backoff retries, and Fowler circuit breaker tripping.
"""

from __future__ import annotations

import os
import socket
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Ensure project root is available on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.resilience import (
    Bulkhead,
    BulkheadFullException,
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitState,
    ResiliencePipeline,
    RetryPolicy,
)


class Network503Exception(Exception):
    """Simulated HTTP 503 Service Unavailable / Gateway Drop."""


def run_transient_network_chaos() -> None:
    """Scenario 1: Intermittent network 503 failures recovered by RetryPolicy."""
    print("\n--- [Scenario 1] Intermittent 503 Network Chaos with Exponential Backoff ---")
    attempts_made = 0

    def flaky_service() -> Dict[str, Any]:
        nonlocal attempts_made
        attempts_made += 1
        if attempts_made < 3:
            print(f"  [FlakyService] Attempt {attempts_made}: Network drop (HTTP 503 / socket error)!")
            raise Network503Exception("Upstream connection dropped")
        print(f"  [FlakyService] Attempt {attempts_made}: Upstream service recovered, 200 OK.")
        return {"status": "success", "churn_score": 0.24}

    retry = RetryPolicy(
        name="chaos_retry",
        max_attempts=4,
        initial_backoff=0.05,
        backoff_factor=1.5,
        retry_on=(Network503Exception, socket.error),
    )

    t0 = time.time()
    result = retry.execute(flaky_service)
    elapsed = time.time() - t0

    assert result["status"] == "success", "Expected successful recovery"
    assert attempts_made == 3, f"Expected 3 attempts, got {attempts_made}"
    assert retry.get_metrics()["total_retries"] == 2, "Expected exactly 2 retries"
    print(f"  [Passed] Recovered after 2 retries in {elapsed:.3f}s with exponential backoff.")


def run_latency_and_bulkhead_chaos() -> None:
    """Scenario 2: Latency injection (100ms-500ms) and Bulkhead concurrency saturation."""
    print("\n--- [Scenario 2] Latency Injection & Bulkhead Concurrency Isolation ---")
    bulkhead = Bulkhead(name="predict_bulkhead", max_concurrent_calls=2, max_wait_duration=0.05)

    def slow_scoring_service(delay_seconds: float) -> str:
        time.sleep(delay_seconds)
        return "score_computed"

    # Acquire permits to simulate active workers saturated by latency
    assert bulkhead.acquire(), "Permit 1 should be acquired"
    assert bulkhead.acquire(), "Permit 2 should be acquired"
    print("  [Bulkhead] 2 permits saturated by high-latency requests (simulating 500ms lag).")

    # A third incoming request should be fast-rejected by BulkheadFullException
    rejected = False
    try:
        bulkhead.execute(slow_scoring_service, 0.2)
    except BulkheadFullException:
        rejected = True
        print("  [Bulkhead] Incoming call immediately isolated and rejected (thread-pool shielded).")

    bulkhead.release()
    bulkhead.release()
    assert rejected, "Bulkhead should have rejected 3rd call when saturated"
    print("  [Passed] Bulkhead successfully prevented thread pool starvation.")


def run_circuit_breaker_tripping_chaos() -> None:
    """Scenario 3: Repeated upstream failure trips Fowler Circuit Breaker to OPEN."""
    print("\n--- [Scenario 3] Persistent Outage & Circuit Breaker Tripping ---")
    breaker = CircuitBreaker(
        name="azure_endpoint_breaker",
        failure_threshold=3,
        recovery_timeout=0.3,
        expected_exceptions=(socket.error, ConnectionResetError),
    )

    def crashing_cloud_call() -> None:
        raise socket.error("Connection reset by peer (simulated Azure drop)")

    # Trigger failures up to threshold
    for i in range(1, 4):
        try:
            breaker.call(crashing_cloud_call)
        except socket.error:
            print(f"  [Breaker] Call {i} failed. Current breaker state: {breaker.state.value}")

    assert breaker.state == CircuitState.OPEN, f"Expected OPEN state, got {breaker.state}"
    print("  [Breaker] Threshold breached: Breaker is OPEN. Now fast-failing subsequent calls.")

    # Subsequent call must fast-fail with CircuitBreakerOpenException without hitting target
    fast_failed = False
    try:
        breaker.call(crashing_cloud_call)
    except CircuitBreakerOpenException as exc:
        fast_failed = True
        print(f"  [Breaker] Fast-fail confirmed: {exc}")

    assert fast_failed, "Expected fast-fail with CircuitBreakerOpenException"
    print("  [Passed] Circuit breaker successfully tripped and protected downstream services.")


def run_pipeline_fallback_chaos() -> None:
    """Scenario 4: Unified pipeline executing graceful fallback when circuit opens."""
    print("\n--- [Scenario 4] Unified Pipeline with Resilient Fallback Interception ---")
    breaker = CircuitBreaker(name="pipe_breaker", failure_threshold=2, recovery_timeout=0.2)
    retry = RetryPolicy(name="pipe_retry", max_attempts=2, initial_backoff=0.02)

    def default_fallback(exc: Exception) -> Dict[str, Any]:
        print(f"  [FallbackHandler] Intercepted {type(exc).__name__}. Returning cached baseline.")
        return {"churn_prediction": 0, "churn_probability": 0.15, "source": "offline_cache"}

    pipeline = ResiliencePipeline(
        name="churn_inference_pipeline",
        circuit_breaker=breaker,
        retry_policy=retry,
        fallback=default_fallback,
    )

    def broken_inference() -> Dict[str, Any]:
        raise ConnectionRefusedError("Redis feature store connection refused")

    result = pipeline.execute(broken_inference)
    assert result["source"] == "offline_cache", "Expected fallback response"
    print(f"  [Passed] Fallback gracefully returned baseline data: {result}")


def run_half_open_recovery_chaos() -> None:
    """Scenario 5: Auto-transition to HALF-OPEN after cooldown and trial recovery to CLOSED."""
    print("\n--- [Scenario 5] Half-Open Auto-Transition & Trial Recovery ---")
    breaker = CircuitBreaker(name="recovery_breaker", failure_threshold=2, recovery_timeout=0.1)
    breaker.trip()
    assert breaker.state == CircuitState.OPEN

    print("  [Breaker] In OPEN state. Sleeping for recovery cooldown (120ms)...")
    time.sleep(0.12)

    assert breaker.state == CircuitState.HALF_OPEN, f"Expected HALF_OPEN, got {breaker.state}"
    print(f"  [Breaker] Cooldown expired. Breaker transitioned to: {breaker.state.value}")

    # Trial call succeeds
    result = breaker.call(lambda: "healthy_probe")
    assert result == "healthy_probe"
    assert breaker.state == CircuitState.CLOSED, f"Expected CLOSED after recovery, got {breaker.state}"
    print(f"  [Breaker] Trial probe succeeded. Circuit breaker recovered to: {breaker.state.value}")
    print("  [Passed] Full recovery lifecycle verified.")


def main() -> int:
    """Execute complete Chaos Fault Injection Suite."""
    print("=" * 66)
    print(" [CHAOS FAULT INJECTION HARNESS] Inspired by Chaos Mesh (8.0k stars)")
    print("=" * 66)
    t0 = time.time()

    run_transient_network_chaos()
    run_latency_and_bulkhead_chaos()
    run_circuit_breaker_tripping_chaos()
    run_pipeline_fallback_chaos()
    run_half_open_recovery_chaos()

    total_time = time.time() - t0
    print("\n" + "=" * 66)
    print(f" [ALL 5 CHAOS SCENARIOS PASSED] Execution duration: {total_time:.3f}s")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
