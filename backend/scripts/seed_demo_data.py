"""Populate a running instance with a demo user, price history, and a
sample portfolio so /docs can be explored with real numbers immediately.

Usage:
    python scripts/seed_demo_data.py [--base-url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import datetime as dt

import httpx
import numpy as np

DEMO_EMAIL = "demo@tradesense.dev"
DEMO_PASSWORD = "demo-pass-1234"

ASSETS = {
    "AAPL": (190.0, 0.0004, 0.016),
    "MSFT": (420.0, 0.0003, 0.014),
    "GOOG": (175.0, 0.0002, 0.017),
    "TSLA": (250.0, 0.0001, 0.032),
}

LOOKBACK_DAYS = 400


def synthetic_prices(start_price: float, drift: float, vol: float, n: int, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    daily_returns = rng.normal(loc=drift, scale=vol, size=n)
    return list(start_price * np.cumprod(1 + daily_returns))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url, timeout=30.0)

    register = client.post("/auth/register", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    if register.status_code not in (201, 409):
        register.raise_for_status()

    login = client.post("/auth/login", data={"username": DEMO_EMAIL, "password": DEMO_PASSWORD})
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print(f"Logged in as {DEMO_EMAIL}")

    start_date = dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)
    price_points = []
    for i, (symbol, (start_price, drift, vol)) in enumerate(ASSETS.items()):
        prices = synthetic_prices(start_price, drift, vol, LOOKBACK_DAYS, seed=100 + i)
        for offset, price in enumerate(prices):
            price_points.append(
                {
                    "symbol": symbol,
                    "price_date": (start_date + dt.timedelta(days=offset)).isoformat(),
                    "close_price": round(price, 4),
                }
            )

    for i in range(0, len(price_points), 500):
        chunk = price_points[i : i + 500]
        resp = client.post("/prices", json={"prices": chunk}, headers=headers)
        resp.raise_for_status()

    print(f"Seeded {len(price_points)} price points across {len(ASSETS)} symbols")

    portfolios = client.get("/portfolios", headers=headers).json()
    portfolio = next((p for p in portfolios if p["name"] == "Demo Growth Book"), None)
    if portfolio is None:
        portfolio = client.post(
            "/portfolios", json={"name": "Demo Growth Book"}, headers=headers
        ).json()

    portfolio_id = portfolio["id"]
    existing_symbols = {
        p["symbol"] for p in client.get(f"/portfolios/{portfolio_id}/positions", headers=headers).json()
    }

    quantities = {"AAPL": 25, "MSFT": 10, "GOOG": 15, "TSLA": 8}
    for symbol, qty in quantities.items():
        if symbol in existing_symbols:
            continue
        avg_cost = ASSETS[symbol][0]
        client.post(
            f"/portfolios/{portfolio_id}/positions",
            json={"symbol": symbol, "quantity": qty, "avg_cost": avg_cost},
            headers=headers,
        ).raise_for_status()

    print(f"Portfolio ready: id={portfolio_id}")

    risk = client.get(f"/portfolios/{portfolio_id}/risk", headers=headers)
    risk.raise_for_status()
    print("\nRisk snapshot:")
    for key, value in risk.json().items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
