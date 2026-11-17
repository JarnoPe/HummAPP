import pytest

from app.models import NfcEvent, VideoClip, WaterMeasurement, utc_now

PAGES = ["/", "/web/horses", "/web/horses/1", "/web/nfc-events", "/web/water", "/web/air", "/web/system"]


@pytest.fixture
def web_client(client, admin_token, db_session):
    event = NfcEvent(horse_id=1, nfc_uid="04A31B92C56F80", phone_timestamp=utc_now(), status="READY")
    db_session.add(event)
    db_session.commit()
    db_session.add(VideoClip(nfc_event_id=event.id, relative_file_path="1/a.mp4", status="READY", is_mock=True))
    db_session.add(WaterMeasurement(horse_id=1, external_measurement_id="W1", external_water_id="X",
                                    measured_at=utc_now(), liters=5.0))
    db_session.commit()
    client.cookies.set("access_token", f"Bearer {admin_token}")
    return client


def test_unauthenticated_pages_redirect_to_login(client):
    for page in PAGES:
        r = client.get(page, follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == "/web/login", page


@pytest.mark.parametrize("page", PAGES)
def test_logged_in_pages_render(web_client, page):
    """Alkuperäisessä versiossa web-kirjautuminen ei toiminut lainkaan (aina uudelleenohjaus)."""
    r = web_client.get(page, follow_redirects=False)
    assert r.status_code == 200, page


def test_mock_clip_is_labelled(web_client):
    assert "TESTIVIDEO" in web_client.get("/web/nfc-events").text


def test_web_login_form_sets_cookie(client):
    r = client.post("/web/login", data={"username": "admin", "password": "testpass123"}, follow_redirects=False)
    assert r.status_code == 302
    assert "access_token" in r.headers.get("set-cookie", "")
