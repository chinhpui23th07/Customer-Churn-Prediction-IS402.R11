"""Measure the same KKBox prediction request from one client to one/two regions.

The subscriber key and API key come only from environment variables and are
never written to the aggregate report. Use two endpoints for rubric evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests


def percentile(values: list[float], fraction: float) -> float:
    sorted_values = sorted(values)
    position = (len(sorted_values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def probe(label: str, url: str, payload: dict, api_key: str, warmup: int, count: int,
          timeout: float) -> dict:
    timings = []
    versions = set()
    predictions = set()
    errors = []
    with requests.Session() as session:
        for index in range(warmup + count):
            started = time.perf_counter()
            try:
                response = session.post(
                    url.rstrip("/") + "/v1/predictions", json=payload,
                    headers={"x-api-key": api_key}, timeout=timeout,
                )
                elapsed_ms = (time.perf_counter() - started) * 1000
                response.raise_for_status()
                data = response.json()
                if not 0 <= float(data["churn_probability"]) <= 1:
                    raise ValueError("Invalid probability")
                if index >= warmup:
                    timings.append(elapsed_ms)
                    versions.add((str(data["model_version"]), str(data["feature_version"])))
                    predictions.add((int(data["prediction"]), round(float(data["churn_probability"]), 6)))
            except (requests.RequestException, KeyError, ValueError) as exc:
                if index >= warmup:
                    errors.append(type(exc).__name__)
    if not timings:
        raise RuntimeError(f"No successful measured requests for {label}")
    return {
        "label": label,
        "url_origin": url.rstrip("/"),
        "requested": count,
        "successful": len(timings),
        "errors": len(errors),
        "error_types": sorted(set(errors)),
        "median_ms": round(statistics.median(timings), 3),
        "p95_ms": round(percentile(timings, .95), 3),
        "p99_ms": round(percentile(timings, .99), 3),
        "min_ms": round(min(timings), 3),
        "max_ms": round(max(timings), 3),
        "versions": sorted(versions),
        "_prediction_values": sorted(predictions),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", action="append", required=True,
                        help="label=https://host; repeat for each region")
    parser.add_argument("--cutoff", choices=["2017-01-31", "2017-02-28"],
                        default="2017-02-28")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--client-label", required=True,
                        help="Same client location and network for every endpoint")
    parser.add_argument("--report", type=Path, default=Path("scratch/kkbox_latency.json"))
    args = parser.parse_args()
    if args.requests < 1 or args.warmup < 0 or args.timeout <= 0:
        parser.error("Invalid request, warmup or timeout value")
    key = os.getenv("KKBOX_DEMO_SUBSCRIBER_KEY")
    api_key = os.getenv("KKBOX_API_KEY")
    if not key or not api_key:
        parser.error("Set KKBOX_DEMO_SUBSCRIBER_KEY and KKBOX_API_KEY in the local environment")
    if not key.isascii() or not key.isdecimal() or (len(key) > 1 and key[0] == "0") or int(key) >= 2**64:
        parser.error("KKBOX_DEMO_SUBSCRIBER_KEY must be a canonical uint64 decimal string")
    endpoints = []
    for item in args.endpoint:
        if "=" not in item:
            parser.error("Each --endpoint must be label=url")
        label, url = item.split("=", 1)
        if not label or not url.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
            parser.error("Use HTTPS except for a local smoke test")
        parsed = urlsplit(url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            parser.error("Endpoint must be an origin without credentials, path, query or fragment")
        endpoints.append((label, url))
    if len({label for label, _ in endpoints}) != len(endpoints):
        parser.error("Endpoint labels must be unique")
    payload = {"subscriber_key": key, "as_of_date": args.cutoff}
    results = [probe(label, url, payload, api_key, args.warmup, args.requests, args.timeout)
               for label, url in endpoints]
    versions = {tuple(version) for result in results for version in result["versions"]}
    predictions = {tuple(value) for result in results for value in result["_prediction_values"]}
    comparable = all(result["errors"] == 0 for result in results) and len(versions) == 1 and len(predictions) == 1
    for result in results:
        del result["_prediction_values"]
    report = {
        "analysis": "single_client_end_to_end_http_latency",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "client_label": args.client_label,
        "client_platform": platform.platform(),
        "cutoff": args.cutoff,
        "warmup_per_endpoint": args.warmup,
        "measured_requests_per_endpoint": args.requests,
        "comparable_model_and_payload": comparable,
        "region_comparison_ready": comparable and len(endpoints) >= 2,
        "results": results,
        "note": "The key and API secret are omitted. Record client network, VM SKU, region and run ID separately.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not comparable:
        raise SystemExit("Endpoints returned errors or different model/prediction values; comparison invalid")


if __name__ == "__main__":
    main()
