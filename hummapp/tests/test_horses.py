def test_list_horses(client, auth_headers):
    """Testaa hevosten hakeminen."""
    response = client.get("/api/horses", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(h["name"] == "Antero" for h in data)


def test_create_horse(client, auth_headers):
    """Testaa uuden hevosen luominen."""
    response = client.post("/api/horses", json={"name": "Valo"}, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Valo"

    # Yritetään luoda sama nimi uudelleen -> virhe
    dup_resp = client.post("/api/horses", json={"name": "Valo"}, headers=auth_headers)
    assert dup_resp.status_code == 400


def test_assign_nfc_tag(client, auth_headers):
    """Testaa NFC-tagin yhdistäminen hevoseen."""
    # Haetaan Antero
    horses_resp = client.get("/api/horses", headers=auth_headers)
    antero_id = [h["id"] for h in horses_resp.json() if h["name"] == "Antero"][0]

    # Yhdistetään uusi tagi Anteroon (pienillä kirjaimilla ja välilyönneillä)
    tag_resp = client.post(
        f"/api/horses/{antero_id}/nfc-tag",
        json={"nfc_uid": "04 b1 22 aa bb cc dd"},
        headers=auth_headers,
    )
    assert tag_resp.status_code == 201
    data = tag_resp.json()
    assert data["nfc_uid"] == "04B122AABBCCDD"  # Normalisoitu heksamuotoon
    assert data["horse_id"] == antero_id
