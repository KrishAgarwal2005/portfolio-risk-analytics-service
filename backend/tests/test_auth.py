def test_register_and_login(client):
    register = client.post(
        "/auth/register", json={"email": "new@example.com", "password": "hunter2pass"}
    )
    assert register.status_code == 201
    assert register.json()["email"] == "new@example.com"

    login = client.post(
        "/auth/login", data={"username": "new@example.com", "password": "hunter2pass"}
    )
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_register_duplicate_email_conflicts(client):
    client.post("/auth/register", json={"email": "dupe@example.com", "password": "pw1"})
    second = client.post("/auth/register", json={"email": "dupe@example.com", "password": "pw2"})
    assert second.status_code == 409


def test_login_wrong_password_unauthorized(client):
    client.post("/auth/register", json={"email": "user@example.com", "password": "correctpw"})
    response = client.post(
        "/auth/login", data={"username": "user@example.com", "password": "wrongpw"}
    )
    assert response.status_code == 401


def test_protected_endpoint_requires_token(client):
    response = client.get("/portfolios")
    assert response.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    response = client.get("/portfolios", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
