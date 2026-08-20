from datetime import date, timedelta


def _seed_prices(client, headers, symbol: str, start: date, n_days: int, start_price: float, step: float):
    prices = []
    price = start_price
    for i in range(n_days):
        prices.append({"symbol": symbol, "price_date": (start + timedelta(days=i)).isoformat(), "close_price": price})
        price += step
    client.post("/prices", json={"prices": prices}, headers=headers)


def test_risk_endpoint_single_asset_book(client, auth_headers):
    start = date(2024, 1, 1)
    _seed_prices(client, auth_headers, "AAPL", start, 30, 100.0, 0.5)

    portfolio = client.post("/portfolios", json={"name": "Book"}, headers=auth_headers).json()
    client.post(
        f"/portfolios/{portfolio['id']}/positions",
        json={"symbol": "AAPL", "quantity": 10, "avg_cost": 100.0},
        headers=auth_headers,
    )

    response = client.get(f"/portfolios/{portfolio['id']}/risk", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["cached"] is False
    assert len(body["exposures"]) == 1
    assert body["exposures"][0]["weight"] == 1.0
    assert body["historical_var_pct"] >= 0
    assert body["parametric_var_pct"] >= 0


def test_risk_endpoint_is_cached_on_second_call(client, auth_headers):
    start = date(2024, 1, 1)
    _seed_prices(client, auth_headers, "AAPL", start, 30, 100.0, 0.5)

    portfolio = client.post("/portfolios", json={"name": "Book"}, headers=auth_headers).json()
    client.post(
        f"/portfolios/{portfolio['id']}/positions",
        json={"symbol": "AAPL", "quantity": 10, "avg_cost": 100.0},
        headers=auth_headers,
    )

    first = client.get(f"/portfolios/{portfolio['id']}/risk", headers=auth_headers).json()
    second = client.get(f"/portfolios/{portfolio['id']}/risk", headers=auth_headers).json()

    assert first["cached"] is False
    assert second["cached"] is True
    assert first["historical_var_value"] == second["historical_var_value"]


def test_risk_endpoint_multi_asset_book(client, auth_headers):
    start = date(2024, 1, 1)
    _seed_prices(client, auth_headers, "AAPL", start, 40, 100.0, 0.3)
    _seed_prices(client, auth_headers, "MSFT", start, 40, 300.0, -0.4)

    portfolio = client.post("/portfolios", json={"name": "Book"}, headers=auth_headers).json()
    client.post(
        f"/portfolios/{portfolio['id']}/positions",
        json={"symbol": "AAPL", "quantity": 10, "avg_cost": 100.0},
        headers=auth_headers,
    )
    client.post(
        f"/portfolios/{portfolio['id']}/positions",
        json={"symbol": "MSFT", "quantity": 4, "avg_cost": 300.0},
        headers=auth_headers,
    )

    response = client.get(
        f"/portfolios/{portfolio['id']}/risk",
        params={"confidence": 0.99, "lookback_days": 30},
        headers=auth_headers,
    )
    body = response.json()
    assert response.status_code == 200
    assert {e["symbol"] for e in body["exposures"]} == {"AAPL", "MSFT"}
    assert body["confidence"] == 0.99


def test_risk_endpoint_sparse_history_does_not_error(client, auth_headers):
    start = date(2024, 1, 1)
    _seed_prices(client, auth_headers, "THIN", start, 2, 50.0, 1.0)

    portfolio = client.post("/portfolios", json={"name": "Book"}, headers=auth_headers).json()
    client.post(
        f"/portfolios/{portfolio['id']}/positions",
        json={"symbol": "THIN", "quantity": 3, "avg_cost": 50.0},
        headers=auth_headers,
    )

    response = client.get(f"/portfolios/{portfolio['id']}/risk", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["portfolio_value"] > 0


def test_risk_endpoint_no_price_history_returns_zeroed_metrics(client, auth_headers):
    portfolio = client.post("/portfolios", json={"name": "Empty Book"}, headers=auth_headers).json()
    client.post(
        f"/portfolios/{portfolio['id']}/positions",
        json={"symbol": "NODATA", "quantity": 1, "avg_cost": 1.0},
        headers=auth_headers,
    )

    response = client.get(f"/portfolios/{portfolio['id']}/risk", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["portfolio_value"] == 0.0
    assert body["exposures"] == []


def test_risk_endpoint_requires_ownership(client, auth_headers):
    portfolio = client.post("/portfolios", json={"name": "Book"}, headers=auth_headers).json()

    client.post("/auth/register", json={"email": "intruder@example.com", "password": "pw12345"})
    other_login = client.post(
        "/auth/login", data={"username": "intruder@example.com", "password": "pw12345"}
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    response = client.get(f"/portfolios/{portfolio['id']}/risk", headers=other_headers)
    assert response.status_code == 404
