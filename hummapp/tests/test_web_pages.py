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


def test_no_external_runtime_dependencies(web_client):
    """NAS voi olla ilman internetyhteyttä: sivut eivät saa ladata CDN-tiedostoja."""
    import re
    from pathlib import Path
    templates = Path(__file__).resolve().parent.parent / "app" / "templates"
    css = (templates.parent / "static" / "css" / "style.css").read_text()
    for path in list(templates.glob("*.html")) + [None]:
        text = css if path is None else path.read_text()
        assert not re.search(r"(src|href)=\"https?://|@import url\('https?://", text), path


def test_review_queue_returns_json_for_inline_review(web_client, db_session):
    from app.models import VideoClip
    clip = db_session.query(VideoClip).first()
    r = web_client.post(f"/web/video-clips/{clip.id}/approve", headers={"Accept": "application/json"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "APPROVED" and body["label"] == "Hyväksytty" and body["pending"] == 0


def test_status_labels_are_finnish(web_client):
    text = web_client.get("/web/nfc-events?nayta=kaikki").text
    assert "Odottaa tarkastusta" in text
    assert "WAITING_FOR_RECORDING" not in text and ">READY<" not in text


def test_horse_form_feedback(web_client):
    r = web_client.post("/web/horses/create", data={"name": "Antero"}, follow_redirects=False)
    assert "ilmoitus=hevonen-on-jo" in r.headers["location"]
    assert "Samanniminen hevonen" in web_client.get(r.headers["location"]).text
    r = web_client.post("/web/horses/assign-tag", data={"horse_id": 1, "nfc_uid": "ZZ"}, follow_redirects=False)
    assert "ilmoitus=tagi-virheellinen" in r.headers["location"]


def test_dashboard_lists_pending_review(web_client):
    text = web_client.get("/").text
    assert "1 videoleike odottaa tarkastusta" in text


def test_status_poll_reports_failures_separately(web_client, db_session):
    """Epäonnistunut leikkaus ei saa näyttää valmistuneelta leikkeeltä tarkastusjonossa."""
    from app.models import NfcEvent, utc_now
    ready = NfcEvent(horse_id=1, nfc_uid="04A31B92C56F80", phone_timestamp=utc_now(), status="READY")
    failed = NfcEvent(horse_id=1, nfc_uid="04A31B92C56F80", phone_timestamp=utc_now(), status="FAILED")
    working = NfcEvent(horse_id=1, nfc_uid="04A31B92C56F80", phone_timestamp=utc_now(), status="PROCESSING")
    db_session.add_all([ready, failed, working])
    db_session.commit()
    body = web_client.get(f"/web/nfc-events/status?ids={ready.id},{failed.id},{working.id}").json()
    assert body["still_working"] == [working.id]
    assert {"id": failed.id, "status": "FAILED"} in body["finished"]
    assert {"id": ready.id, "status": "READY"} in body["finished"]
