import os
from pathlib import Path
from app.models import VideoClip, NfcEvent, utc_now
from app.config import settings


def create_sample_video_clip(db_session):
    event = NfcEvent(
        horse_id=1,
        nfc_uid="04A31B92C56F80",
        phone_timestamp=utc_now(),
        location="kuvausalue-1",
        status="READY",
    )
    db_session.add(event)
    db_session.commit()

    # Luodaan tiedosto testiä varten
    rel_path = "1/2026/11/sample_test_clip.mp4"
    full_path = Path(settings.VIDEO_OUTPUT_PATH) / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(b"FAKE_MP4_HEADER_DATA")

    clip = VideoClip(
        nfc_event_id=event.id,
        relative_file_path=rel_path,
        status="READY",
    )
    db_session.add(clip)
    db_session.commit()
    db_session.refresh(clip)
    return clip, full_path


def test_approve_video_clip(client, auth_headers, db_session):
    """Testaa videon hyväksyminen -> Tila APPROVED."""
    clip, _ = create_sample_video_clip(db_session)
    response = client.post(f"/api/video-clips/{clip.id}/approve", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    assert response.json()["approved_at"] is not None


def test_reject_video_clip(client, auth_headers, db_session):
    """Testaa videon hylkääminen -> Tila REJECTED, tiedosto säilyy toistaiseksi."""
    clip, file_path = create_sample_video_clip(db_session)
    response = client.post(f"/api/video-clips/{clip.id}/reject", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    # Tiedosto on yhä tallessa
    assert file_path.exists()


def test_safe_delete_video_clip(client, auth_headers, db_session):
    """Testaa ylläpitäjän turvallinen videon poisto levyltä."""
    clip, file_path = create_sample_video_clip(db_session)
    assert file_path.exists()

    response = client.delete(f"/api/video-clips/{clip.id}", headers=auth_headers)
    assert response.status_code == 204

    # Tiedosto poistettu levyltä ja tila kannassa DELETED
    assert not file_path.exists()


def test_path_traversal_prevention(client, auth_headers, db_session):
    """Testaa, että Path Traversal -yritys (esim. ../../etc/passwd) estetään tiukasti."""
    event = NfcEvent(
        horse_id=1,
        nfc_uid="04A31B92C56F80",
        phone_timestamp=utc_now(),
        status="READY",
    )
    db_session.add(event)
    db_session.commit()

    malicious_clip = VideoClip(
        nfc_event_id=event.id,
        relative_file_path="../../etc/passwd",
        status="READY",
    )
    db_session.add(malicious_clip)
    db_session.commit()

    # Yritetään ladata tiedostoa -> sovelluksen tulee estää
    response = client.get(f"/api/video-clips/{malicious_clip.id}/download", headers=auth_headers)
    assert response.status_code in (400, 403, 404)
