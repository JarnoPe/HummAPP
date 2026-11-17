"""Päästä päähän: oikea FFmpeg leikkaa 18 s (5 s + 13 s) leikkeen paikallisaikaan nimetystä kameratiedostosta."""
import asyncio
import datetime
import shutil
import subprocess
from pathlib import Path

import pytest

from app.config import settings
from app.models import NfcEvent, VideoClip
from app.services import video as video_module
from app.services.video import VideoService
from app.services.video_source_resolver import SynologyTimestampVideoResolver, ffprobe_duration

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg puuttuu")


def test_cut_produces_configured_clip_without_blocking(db_session, tmp_path, monkeypatch):
    camera = tmp_path / "camera"
    camera.mkdir()
    # 60 s kameratallenne, joka alkaa 12:00:00 Helsingin aikaa (= 10:00:00 UTC)
    src = camera / "CAM01_20261117_120000.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=60:size=320x240:rate=25",
                    "-c:v", "libx264", "-preset", "ultrafast", str(src)], check=True)

    event = NfcEvent(horse_id=1, nfc_uid="04A31B92C56F80", phone_timestamp=datetime.datetime(2026, 11, 17, 10, 0, 30),
                     status="RECEIVED")
    db_session.add(event)
    db_session.commit()

    monkeypatch.setattr(video_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    service = VideoService(SynologyTimestampVideoResolver(camera_root_path=str(camera), camera_timezone="Europe/Helsinki"))

    async def run():
        ticks = 0

        async def heartbeat():
            nonlocal ticks
            while True:
                ticks += 1
                await asyncio.sleep(0.01)

        hb = asyncio.create_task(heartbeat())
        await service.cut_video_for_event(event.id)
        hb.cancel()
        return ticks

    ticks = asyncio.run(run())
    db_session.refresh(event)
    assert event.status == "READY", event.error_message
    clip = db_session.query(VideoClip).filter_by(nfc_event_id=event.id).one()
    out = Path(settings.VIDEO_OUTPUT_PATH) / clip.relative_file_path
    assert abs(ffprobe_duration(out) - settings.clip_duration_seconds) < 0.2
    assert settings.clip_duration_seconds == 18
    assert clip.is_mock is False
    assert ticks > 3, "Event loop pysähtyi FFmpegin ajaksi"
