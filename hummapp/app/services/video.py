import os
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import datetime
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models import NfcEvent, VideoClip, Horse, SystemEvent, utc_now
from app.services.video_source_resolver import VideoSourceResolverBase, SynologyTimestampVideoResolver

logger = logging.getLogger(__name__)


def validate_and_resolve_video_path(relative_path: str) -> Path:
    """
    Tarkistaa ja estää Path Traversal -hyökkäykset.
    Varmistaa, että suhteellinen polku pysyy aina sallitussa VIDEO_OUTPUT_PATH -hakemistossa.
    """
    if ".." in relative_path or relative_path.startswith("/") or relative_path.startswith("\\"):
        raise ValueError("Luvaton suhteellinen polku (Path Traversal estetty).")

    base_dir = Path(settings.VIDEO_OUTPUT_PATH).resolve()
    resolved = (base_dir / relative_path).resolve()

    try:
        # Python 3.9+ is_relative_to
        if not resolved.is_relative_to(base_dir):
            raise ValueError("Polku osoittaa sallitun videohakemiston ulkopuolelle.")
    except AttributeError:
        if not str(resolved).startswith(str(base_dir)):
            raise ValueError("Polku osoittaa sallitun videohakemiston ulkopuolelle.")

    return resolved


class VideoService:
    def __init__(self, resolver: Optional[VideoSourceResolverBase] = None):
        self.resolver = resolver or SynologyTimestampVideoResolver()

    async def cut_video_for_event(self, event_id: int):
        """
        Taustaprosessi: leikkaa kameratallenteesta ~50 sekunnin videon
        (10s ennen NFC-tapahtumaa ja 40s tapahtuman jälkeen).
        Sisältää uudelleenyrityslogiikan siltä varalta, että kameran tallenne
        on vielä kesken tai tallentumassa levylle.
        """
        db: Session = SessionLocal()
        try:
            event = db.query(NfcEvent).filter(NfcEvent.id == event_id).first()
            if not event:
                logger.error(f"NfcEvent #{event_id} ei löydy videoleikkausta varten.")
                return

            event.status = "WAITING_FOR_RECORDING"
            db.commit()

            match = None
            retries = 0
            max_retries = settings.VIDEO_MAX_RETRIES
            interval = settings.VIDEO_RETRY_INTERVAL_SECONDS

            # Odotussilmukka kameratallenteen valmistumiselle
            while retries < max_retries:
                match = self.resolver.resolve_source(
                    event.phone_timestamp,
                    seconds_before=settings.VIDEO_SECONDS_BEFORE,
                    seconds_after=settings.VIDEO_SECONDS_AFTER,
                )
                if match and match.file_path.exists():
                    break

                retries += 1
                logger.info(
                    f"Kameratallennetta ei vielä löytynyt tapahtumalle #{event_id}. "
                    f"Yritys {retries}/{max_retries}. Odotetaan {interval}s..."
                )
                await asyncio.sleep(interval)

            event.status = "PROCESSING"
            db.commit()

            # Kohdehakemistorakenne: videos/<horse_id>/<vuosi>/<kuukausi>/<event_id>.mp4
            horse_folder = str(event.horse_id) if event.horse_id else "unassigned"
            year_str = event.phone_timestamp.strftime("%Y")
            month_str = event.phone_timestamp.strftime("%m")
            filename = f"event_{event.id}_{event.phone_timestamp.strftime('%Y%m%d_%H%M%S')}.mp4"

            rel_path = f"{horse_folder}/{year_str}/{month_str}/{filename}"
            abs_dest_path = validate_and_resolve_video_path(rel_path)
            abs_dest_path.parent.mkdir(parents=True, exist_ok=True)

            success = False
            error_msg = None

            if match and match.file_path.exists():
                logger.info(f"Leikataan video FFmpegillä tiedostosta: {match.file_path} -> {abs_dest_path}")
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-ss", str(max(0.0, match.clip_start_offset_seconds)),
                    "-i", str(match.file_path),
                    "-t", str(match.duration_seconds),
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "24",
                    "-c:a", "aac",
                    "-movflags", "+faststart",
                    str(abs_dest_path),
                ]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
                if proc.returncode == 0:
                    success = True
                else:
                    error_msg = f"FFmpeg virhekoodi {proc.returncode}: {proc.stderr.decode('utf-8', errors='ignore')[:300]}"
            elif settings.ENABLE_MOCK_CAMERA_FALLBACK:
                # Mock-videon luonti demonstraatiota ja pilotin ensitestausta varten
                logger.info(f"Luodaan demonstraatio-videoleike tapahtumalle #{event_id} (Mock fallback)...")
                horse_name = event.horse.name if event.horse else "Tuntematon"
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "lavfi",
                    "-i", "testsrc=duration=50:size=640x360:rate=25",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    str(abs_dest_path),
                ]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
                if proc.returncode == 0:
                    success = True
                else:
                    error_msg = f"Mock FFmpeg epäonnistui: {proc.stderr.decode('utf-8', errors='ignore')[:300]}"
            else:
                error_msg = "Kameratallennetta ei löytynyt määritetyssä ajassa eikä mock-tila ole käytössä."

            if success:
                video_clip = VideoClip(
                    nfc_event_id=event.id,
                    relative_file_path=rel_path,
                    status="READY",
                )
                db.add(video_clip)
                event.status = "READY"
                db.commit()
                logger.info(f"Videoleike #{video_clip.id} luotu onnistuneesti: {rel_path}")
            else:
                event.status = "FAILED"
                event.error_message = error_msg
                db.commit()
                logger.error(f"Videoleikkaus epäonnistui tapahtumalle #{event.id}: {error_msg}")

        except Exception as e:
            logger.exception(f"Kriittinen virhe videonkäsittelyssä tapahtumalle #{event_id}: {e}")
            try:
                event = db.query(NfcEvent).filter(NfcEvent.id == event_id).first()
                if event:
                    event.status = "FAILED"
                    event.error_message = str(e)
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()


video_service = VideoService()
