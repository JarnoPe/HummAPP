def test_login_success(client):
    """Testaa onnistunut kirjautuminen oikealla salasanalla."""
    response = client.post("/api/login", json={"username": "admin", "password": "testpass123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["username"] == "admin"


def test_login_wrong_password(client):
    """Testaa virheellinen salasana -> 401 Unauthorized."""
    response = client.post("/api/login", json={"username": "admin", "password": "vaara-salasana"})
    assert response.status_code == 401
    assert "Virheellinen käyttäjätunnus tai salasana" in response.json()["detail"]


def test_unauthenticated_access_blocked(client):
    """Testaa suojatun reitin estäminen ilman tokenia."""
    response = client.get("/api/horses")
    assert response.status_code == 401
