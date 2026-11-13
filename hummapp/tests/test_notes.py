def test_add_and_get_horse_notes(client, auth_headers):
    """Testaa hevoskohtaisen muistiinpanon lisääminen ja haku."""
    # Haetaan Anteron ID
    horses = client.get("/api/horses", headers=auth_headers).json()
    antero_id = horses[0]["id"]

    # Lisätään muistiinpano
    add_resp = client.post(
        f"/api/horses/{antero_id}/notes",
        json={"content": "Antero söi aamuheinät hyvällä ruokahalulla."},
        headers=auth_headers,
    )
    assert add_resp.status_code == 201
    assert add_resp.json()["content"] == "Antero söi aamuheinät hyvällä ruokahalulla."

    # Haetaan muistiinpanot
    list_resp = client.get(f"/api/horses/{antero_id}/notes", headers=auth_headers)
    assert list_resp.status_code == 200
    notes = list_resp.json()
    assert len(notes) == 1
    assert notes[0]["content"] == "Antero söi aamuheinät hyvällä ruokahalulla."
