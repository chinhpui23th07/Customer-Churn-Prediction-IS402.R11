"""High-Throughput Load Testing & SLO Verification Runner.

Inspired by grafana/k6 (24.5k stars).
Executes high-concurrency performance verification against FastAPI `/health` and
`/predict` endpoints, evaluating strict cloud SLOs:
- Error rate < 1.0%
- p95 latency < 150.0 ms
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure project root is available on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SAMPLE_PAYLOAD = {
    "customer_id": 10452,
    "age": 38.0,
    "gender": "Female",
    "tenure": 12.0,
    "usage_frequency": 18.0,
    "support_calls": 2.0,
    "payment_delay": 1.0,
    "subscription_type": "Standard",
    "contract_length": "Monthly",
    "total_spend": 620.5,
    "last_interaction": 8.0,
}

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": os.getenv("API_KEY", "mlops-churn-secret-2026"),
    "X-Requested-With": "XMLHttpRequest",
}


def find_k6_executable() -> str | None:
    """Locate authentic k6 executable in tools/ or system PATH."""
    local_k6 = PROJECT_ROOT / "tools" / "k6" / "k6.exe"
    if local_k6.exists():
        return str(local_k6)
    return shutil.which("k6")


def run_k6_binary(k6_bin: str) -> int:
    """Execute authentic k6 CLI."""
    k6_script = PROJECT_ROOT / "scripts" / "k6_load_test.js"
    summary_path = PROJECT_ROOT / "reports" / "k6_real_benchmark.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [k6_bin, "run", str(k6_script), "--summary-export", str(summary_path)]
    print(f"[k6 Runner] Executing authentic k6 binary: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def run_native_load_benchmark(total_requests: int = 150, concurrency: int = 10) -> int:
    """Execute concurrent Python load test harness evaluating p95 and error SLOs."""
    from fastapi.testclient import TestClient
    from src.api.main import app, load_artifacts

    load_artifacts()
    client = TestClient(app)

    print("=" * 66)
    print(" [K6-STYLE CONCURRENT LOAD TEST RUNNER] (grafana/k6 24k+ stars)")
    print(f" Target: /predict & /health | Requests: {total_requests} | Concurrency: {concurrency}")
    print("=" * 66)

    latencies_ms: List[float] = []
    errors: int = 0
    t_start = time.perf_counter()

    def make_request(idx: int) -> Tuple[bool, float]:
        t0 = time.perf_counter()
        try:
            if idx % 2 == 0:
                res = client.get("/health")
                ok = res.status_code == 200
            else:
                res = client.post("/predict", json=SAMPLE_PAYLOAD, headers=HEADERS)
                ok = res.status_code == 200 and "churn_prediction" in res.json()
            latency = (time.perf_counter() - t0) * 1000.0
            return ok, latency
        except Exception:
            latency = (time.perf_counter() - t0) * 1000.0
            return False, latency

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request, i) for i in range(total_requests)]
        for fut in concurrent.futures.as_completed(futures):
            ok, lat = fut.result()
            latencies_ms.append(lat)
            if not ok:
                errors += 1

    total_duration = time.perf_counter() - t_start
    rps = total_requests / total_duration if total_duration > 0 else 0.0
    sorted_lat = sorted(latencies_ms)
    n = len(sorted_lat)

    p50 = sorted_lat[int(0.50 * n)]
    p90 = sorted_lat[int(0.90 * n)]
    p95 = sorted_lat[int(0.95 * n)]
    p99 = sorted_lat[min(n - 1, int(0.99 * n))]
    error_rate = (errors / total_requests) * 100.0

    print("\n" + "-" * 66)
    print(" PERFORMANCE & SLO VERIFICATION SUMMARY")
    print("-" * 66)
    print(f" Total Requests Completed : {total_requests}")
    print(f" Total Duration (sec)     : {total_duration:.3f} s")
    print(f" Throughput (RPS)         : {rps:.2f} req/s")
    print(f" Error Rate (%)           : {error_rate:.2f}% (SLO Target: < 1.0%)")
    print(f" Latency Median (p50)     : {p50:.2f} ms")
    print(f" Latency 90th (p90)       : {p90:.2f} ms")
    print(f" Latency 95th (p95)       : {p95:.2f} ms (SLO Target: < 150.0 ms)")
    print(f" Latency 99th (p99)       : {p99:.2f} ms")
    print("-" * 66)

    # Formal SLO code assertions
    slo_passed = True
    if error_rate >= 1.0:
        print(f"[FAIL] Error rate breached SLO threshold: {error_rate:.2f}% >= 1.0%")
        slo_passed = False
    else:
        print(f"[PASS] Error rate complies with SLO: {error_rate:.2f}% < 1.0%")

    if p95 >= 150.0:
        print(f"[FAIL] p95 latency breached SLO threshold: {p95:.2f} ms >= 150.0 ms")
        slo_passed = False
    else:
        print(f"[PASS] p95 latency complies with SLO: {p95:.2f} ms < 150.0 ms")

    print("=" * 66)
    return 0 if slo_passed else 1


def main() -> int:
    """Dispatch to real k6 binary if present, or native high-concurrency runner."""
    k6_bin = find_k6_executable()
    if k6_bin:
        return run_k6_binary(k6_bin)
    return run_native_load_benchmark()


if __name__ == "__main__":
    sys.exit(main())
