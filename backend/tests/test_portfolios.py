def test_create_and_list_portfolio(client, auth_headers):
    create = client.post("/portfolios", json={"name": "Core Book"}, headers=auth_headers)
    assert create.status_code == 201
    assert create.json()["base_currency"] == "USD"

    listing = client.get("/portfolios", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_cannot_access_other_users_portfolio(client, auth_headers):
    create = client.post("/portfolios", json={"name": "Private Book"}, headers=auth_headers)
    portfolio_id = create.json()["id"]

    client.post("/auth/register", json={"email": "other@example.com", "password": "otherpass"})
    other_login = client.post(
        "/auth/login", data={"username": "other@example.com", "password": "otherpass"}
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    response = client.get(f"/portfolios/{portfolio_id}", headers=other_headers)
    assert response.status_code == 404


def test_add_and_list_positions(client, auth_headers):
    portfolio = client.post("/portfolios", json={"name": "Book"}, headers=auth_headers).json()

    add = client.post(
        f"/portfolios/{portfolio['id']}/positions",
        json={"symbol": "aapl", "quantity": 10, "avg_cost": 150.0},
        headers=auth_headers,
    )
    assert add.status_code == 201
    assert add.json()["symbol"] == "AAPL"

    positions = client.get(f"/portfolios/{portfolio['id']}/positions", headers=auth_headers)
    assert len(positions.json()) == 1


def test_update_and_delete_position(client, auth_headers):
    portfolio = client.post("/portfolios", json={"name": "Book"}, headers=auth_headers).json()
    position = client.post(
        f"/portfolios/{portfolio['id']}/positions",
        json={"symbol": "MSFT", "quantity": 5, "avg_cost": 300.0},
        headers=auth_headers,
    ).json()

    updated = client.patch(
        f"/portfolios/{portfolio['id']}/positions/{position['id']}",
        json={"quantity": 8},
        headers=auth_headers,
    )
    assert updated.json()["quantity"] == 8

    deleted = client.delete(
        f"/portfolios/{portfolio['id']}/positions/{position['id']}", headers=auth_headers
    )
    assert deleted.status_code == 204

    positions = client.get(f"/portfolios/{portfolio['id']}/positions", headers=auth_headers)
    assert positions.json() == []
