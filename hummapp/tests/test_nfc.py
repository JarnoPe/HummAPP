import datetime
from app.models import Horse


def test_known_nfc_tag_reading(client, auth_headers):
    """Testaa tunnetun NFC-tagin lukeminen -> Onnistuu ja yhdistyy Anteroon."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "nfc_uid": "04A31B92C56F80",
        "phone_timestamp": now_iso,
        "location": "kuvausalue-1",
    }
    response = client.post("/api/nfc-events", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["horse_name"] == "Antero"
    assert data["nfc_uid"] == "04A31B92C56F80"
    assert data["status"] in ("RECEIVED", "PROCESSING", "WAITING_FOR_RECORDING", "READY")


def test_unknown_nfc_tag_reading(client, auth_headers, db_session):
    """
    Testaa tuntemattoman NFC-tagin lukeminen:
    - Palauttaa selkeän UNKNOWN_TAG -virheen
    - EI luo uutta hevosta automaattisesti
    """
    horse_count_before = db_session.query(Horse).count()

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "nfc_uid": "DEADBEEF9999",
        "phone_timestamp": now_iso,
        "location": "kuvausalue-1",
    }
    response = client.post("/api/nfc-events", json=payload, headers=auth_headers)
    assert response.status_code == 404
    assert "UNKNOWN_TAG" in response.json()["detail"]

    # Varmistetaan, ettei uutta hevosta ole luotu
    horse_count_after = db_session.query(Horse).count()
    assert horse_count_after == horse_count_before


def test_nfc_duplicate_reading_debounced(client, auth_headers):
    """
    Testaa NFC-kaksoislukemisen estäminen:
    Jos sama tagi lähetetään nopeasti peräkkäin, toinen pyyntö sivuuttaa uuden videoleikkauksen.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "nfc_uid": "04A31B92C56F80",
        "phone_timestamp": now_iso,
        "location": "kuvausalue-1",
    }
    # Ensimmäinen luku
    resp1 = client.post("/api/nfc-events", json=payload, headers=auth_headers)
    assert resp1.status_code == 201
    event_id_1 = resp1.json()["id"]

    # Toinen luku heti perään samalla tagilla
    resp2 = client.post("/api/nfc-events", json=payload, headers=auth_headers)
    assert resp2.status_code in (200, 201)
    event_id_2 = resp2.json()["id"]

    # Molempien tulisi viitata samaan tapahtumaan debouncen takia
    assert event_id_1 == event_id_2
