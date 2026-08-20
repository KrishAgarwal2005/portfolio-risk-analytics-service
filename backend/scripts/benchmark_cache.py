"""Measure the Redis cache's effect on /risk latency.

Run `seed_demo_data.py` first. This hits the same portfolio's risk endpoint
twice: once with a fresh as_of_date bust (forces a DB scan + NumPy compute)
and once repeated (served from Redis), and prints both timings so the
before/after latency numbers in the writeup reflect a real measurement.

Usage:
    python scripts/benchmark_cache.py [--base-url http://localhost:8000] [--runs 20]
"""

from __future__ import annotations

import argparse
import statistics
import time

import httpx


def timed_get(client: httpx.Client, url: str, headers: dict, params: dict) -> float:
    start = time.perf_counter()
    resp = client.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return (time.perf_counter() - start) * 1000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default="demo@tradesense.dev")
    parser.add_argument("--password", default="demo-pass-1234")
    parser.add_argument("--runs", type=int, default=20)
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url, timeout=30.0)

    login = client.post("/auth/login", data={"username": args.email, "password": args.password})
    login.raise_for_status()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    portfolios = client.get("/portfolios", headers=headers).json()
    if not portfolios:
        raise SystemExit("No portfolios found -- run scripts/seed_demo_data.py first")
    portfolio_id = portfolios[0]["id"]
    url = f"/portfolios/{portfolio_id}/risk"

    cold_ms = []
    warm_ms = []
    for i in range(args.runs):
        params = {"confidence": 0.9 + (i % 5) * 0.01}  # unique cache key each iteration
        cold_ms.append(timed_get(client, url, headers, params))
        warm_ms.append(timed_get(client, url, headers, params))

    print(f"Cache MISS (Postgres scan + NumPy compute): median {statistics.median(cold_ms):.1f} ms")
    print(f"Cache HIT  (served from Redis):              median {statistics.median(warm_ms):.1f} ms")
    speedup = statistics.median(cold_ms) / max(statistics.median(warm_ms), 0.001)
    print(f"Speedup: {speedup:.1f}x")


if __name__ == "__main__":
    main()
