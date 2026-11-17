from app.auth import create_access_token
from app.constants import ClipStatus
from app.models import Horse, HorseNote, NfcEvent, VideoClip, utc_now
from app.web.routes import safe_next


def _clip(db, status="READY"):
    event = NfcEvent(horse_id=1, nfc_uid="04A31B92C56F80", phone_timestamp=utc_now(), status="READY")
    db.add(event)
    db.commit()
    clip = VideoClip(nfc_event_id=event.id, relative_file_path="1/x.mp4", status=status)
    db.add(clip)
    db.commit()
    return clip


def test_safe_next_blocks_open_redirect():
    assert safe_next("/web/horses/1") == "/web/horses/1"
    assert safe_next("https://evil.example") == "/web/nfc-events"
    assert safe_next("//evil.example") == "/web/nfc-events"
    assert safe_next(None) == "/web/nfc-events"


def test_web_approve_cannot_revive_deleted_clip(client, admin_token, db_session):
    clip = _clip(db_session, status=ClipStatus.DELETED.value)
    client.cookies.set("access_token", f"Bearer {admin_token}")
    r = client.post(f"/web/video-clips/{clip.id}/approve", follow_redirects=False)
    assert r.status_code == 404
    db_session.refresh(clip)
    assert clip.status == "DELETED"


def test_web_redirect_ignores_external_next(client, admin_token, db_session):
    clip = _clip(db_session)
    client.cookies.set("access_token", f"Bearer {admin_token}")
    r = client.post(f"/web/video-clips/{clip.id}/reject?next=https://evil.example", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].startswith("/web/nfc-events")
    assert "evil" not in r.headers["location"]


def test_approve_after_reject_clears_rejected_at(client, auth_headers, db_session):
    clip = _clip(db_session)
    client.post(f"/api/video-clips/{clip.id}/reject", headers=auth_headers)
    body = client.post(f"/api/video-clips/{clip.id}/approve", headers=auth_headers).json()
    assert body["status"] == "APPROVED"
    assert body["rejected_at"] is None


def test_public_overview_hides_personal_data(client, db_session):
    horse = db_session.get(Horse, 1)
    horse.owner_name = "Matti Meikäläinen"
    db_session.add(HorseNote(horse_id=1, content="Ontuu vasenta etujalkaa", user_id=1))
    db_session.commit()

    body = client.get("/api/public/overview").json()
    text = str(body)
    assert "Matti Meikäläinen" not in text
    assert "04A31B92C56F80" not in text
    assert "Ontuu" not in text  # PUBLIC_INCLUDE_NOTES=false oletuksena
    assert "owner_name" not in body["horses"][0]
    assert body["horses"][0]["has_nfc_tag"] is True
    assert body["clip_seconds_before"] == 5 and body["clip_seconds_after"] == 13


def test_system_status_requires_admin(client, db_session):
    assert client.get("/api/system/status").status_code == 401
    user_token = create_access_token({"sub": "worker"})
    from app.auth import get_password_hash
    from app.models import User
    db_session.add(User(username="worker", password_hash=get_password_hash("x" * 12), role="user", active=True))
    db_session.commit()
    r = client.get("/api/system/status", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 403


def test_video_download_link_is_scoped(client, auth_headers, db_session, tmp_path):
    from pathlib import Path
    from app.config import settings
    clip = _clip(db_session)
    path = Path(settings.VIDEO_OUTPUT_PATH) / clip.relative_file_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"MP4")

    link = client.post(f"/api/video-clips/{clip.id}/download-link", headers=auth_headers).json()
    assert client.get(link["url"]).status_code == 200
    # Linkkitoken ei kelpaa toiseen leikkeeseen eikä kirjautumiseen
    other = _clip(db_session)
    sig = link["url"].split("sig=")[1]
    assert client.get(f"/api/video-clips/{other.id}/download?sig={sig}").status_code == 401
    assert client.get("/api/me", headers={"Authorization": f"Bearer {sig}"}).status_code == 401
    # Ilman tunnistautumista ei saa ladata
    assert client.get(f"/api/video-clips/{clip.id}/download").status_code == 401


def test_invalid_nfc_uid_rejected(client, auth_headers):
    r = client.post("/api/horses/1/nfc-tag", json={"nfc_uid": "ZZZZ-NOT-HEX"}, headers=auth_headers)
    assert r.status_code == 422
