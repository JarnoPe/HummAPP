"""
NFC-tapahtuman videoleikkaus.

Leike on oletuksena 5 s ennen ja 5 s jälkeen NFC-leimauksen (VIDEO_SECONDS_BEFORE /
VIDEO_SECONDS_AFTER), koska talutuksessa hevonen on kameran edessä enintään ~10 s.

FFmpeg ja tiedostohaku ajetaan niin, etteivät ne pysäytä FastAPIn event looppia:
FFmpeg asyncio-aliprosessina ja kamerahakemiston läpikäynti säikeessä.
"""
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from app.config import settings
from app.constants import ClipStatus, EventStatus
from app.database import SessionLocal
from app.models import NfcEvent, VideoClip
from app.services.system_events import record_system_event
from app.services.video_source_resolver import (
    SynologyTimestampVideoResolver,
    VideoSourceMatch,
    VideoSourceResolverBase,
)

logger = logging.getLogger(__name__)

FFMPEG_CUT_TIMEOUT_SECONDS = 60
FFMPEG_MOCK_TIMEOUT_SECONDS = 30
FFMPEG_ERROR_MAX_CHARS = 300


def validate_and_resolve_video_path(relative_path: str) -> Path:
    """
    Estää Path Traversal -hyökkäykset: suhteellinen polku pysyy aina
    VIDEO_OUTPUT_PATH-hakemiston sisällä.
    """
    if not relative_path or ".." in relative_path or relative_path.startswith(("/", "\\")):
        raise ValueError("Luvaton suhteellinen polku (Path Traversal estetty).")

    base_dir = Path(settings.VIDEO_OUTPUT_PATH).resolve()
    resolved = (base_dir / relative_path).resolve()
    if not resolved.is_relative_to(base_dir):
        raise ValueError("Polku osoittaa sallitun videohakemiston ulkopuolelle.")
    return resolved


def build_clip_relative_path(event: NfcEvent) -> str:
    """videos/<horse_id>/<vuosi>/<kuukausi>/event_<id>_<aikaleima>.mp4"""
    horse_folder = str(event.horse_id) if event.horse_id else "unassigned"
    ts = event.phone_timestamp
    return f"{horse_folder}/{ts:%Y}/{ts:%m}/event_{event.id}_{ts:%Y%m%d_%H%M%S}.mp4"


def build_cut_command(match: VideoSourceMatch, destination: Path) -> List[str]:
    # -ss ennen -i: nopea haku. Uudelleenkoodaus takaa tarkan aloituskohdan myös
    # avainkuvien välistä (tärkeää, kun leike on vain 10 s).
    return [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{max(0.0, match.clip_start_offset_seconds):.3f}",
        "-i", str(match.file_path),
        "-t", f"{match.duration_seconds:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(destination),
    ]


def build_mock_command(destination: Path, duration_seconds: int) -> List[str]:
    return [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={duration_seconds}:size=640x360:rate=25",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(destination),
    ]


async def run_ffmpeg(cmd: List[str], timeout: int) -> Tuple[bool, Optional[str]]:
    """Ajaa FFmpegin estämättä event looppia. Palauttaa (onnistui, virheteksti)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
    except FileNotFoundError:
        return False, "FFmpegiä ei löydy kontista."
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False, f"FFmpeg aikakatkaisu ({timeout} s)."
    if proc.returncode == 0:
        return True, None
    detail = stderr.decode("utf-8", errors="ignore")[:FFMPEG_ERROR_MAX_CHARS]
    return False, f"FFmpeg virhekoodi {proc.returncode}: {detail}"


class VideoService:
    def __init__(self, resolver: Optional[VideoSourceResolverBase] = None):
        self.resolver = resolver or SynologyTimestampVideoResolver()

    async def cut_video_for_event(self, event_id: int) -> None:
        """Taustatehtävä: odottaa kameratallennetta ja leikkaa siitä NFC-leimauksen leikkeen."""
        db = SessionLocal()
        try:
            event = db.get(NfcEvent, event_id)
            if not event:
                logger.error("NfcEvent #%s ei löydy videoleikkausta varten.", event_id)
                return

            event.status = EventStatus.WAITING_FOR_RECORDING.value
            db.commit()

            match = await self._wait_for_source(event)

            event.status = EventStatus.PROCESSING.value
            db.commit()

            rel_path = build_clip_relative_path(event)
            destination = validate_and_resolve_video_path(rel_path)
            destination.parent.mkdir(parents=True, exist_ok=True)

            success, error_msg, is_mock = await self._produce_clip(match, destination)

            if success:
                clip = VideoClip(
                    nfc_event_id=event.id,
                    relative_file_path=rel_path,
                    status=ClipStatus.READY.value,
                    is_mock=is_mock,
                )
                db.add(clip)
                event.status = EventStatus.READY.value
                if match and match.partial:
                    event.error_message = "Leike jäi vajaaksi: kamera vaihtoi tallennetiedostoa kesken leikkeen."
                db.commit()
                logger.info("Videoleike #%s luotu: %s", clip.id, rel_path)
            else:
                self._mark_failed(db, event, error_msg or "Tuntematon virhe")
        except Exception as e:
            logger.exception("Kriittinen virhe videonkäsittelyssä tapahtumalle #%s", event_id)
            db.rollback()
            event = db.get(NfcEvent, event_id)
            if event:
                self._mark_failed(db, event, str(e))
        finally:
            db.close()

    async def _wait_for_source(self, event: NfcEvent) -> Optional[VideoSourceMatch]:
        for attempt in range(1, settings.VIDEO_MAX_RETRIES + 1):
            # Kamerahakemiston läpikäynti ja ffprobe ovat estäviä -> säikeeseen
            match = await asyncio.to_thread(
                self.resolver.resolve_source,
                event.phone_timestamp,
                settings.VIDEO_SECONDS_BEFORE,
                settings.VIDEO_SECONDS_AFTER,
            )
            if match:
                return match
            logger.info(
                "Kameratallennetta ei vielä löytynyt tapahtumalle #%s (yritys %s/%s).",
                event.id, attempt, settings.VIDEO_MAX_RETRIES,
            )
            if attempt < settings.VIDEO_MAX_RETRIES:
                await asyncio.sleep(settings.VIDEO_RETRY_INTERVAL_SECONDS)
        return None

    async def _produce_clip(
        self, match: Optional[VideoSourceMatch], destination: Path
    ) -> Tuple[bool, Optional[str], bool]:
        """Palauttaa (onnistui, virhe, onko testisignaalivideo)."""
        if match:
            ok, err = await run_ffmpeg(build_cut_command(match, destination), FFMPEG_CUT_TIMEOUT_SECONDS)
            return ok, err, False
        if settings.ENABLE_MOCK_CAMERA_FALLBACK:
            logger.warning("Kameratallennetta ei löytynyt -> luodaan TESTISIGNAALIVIDEO (mock-tila päällä).")
            ok, err = await run_ffmpeg(
                build_mock_command(destination, settings.clip_duration_seconds), FFMPEG_MOCK_TIMEOUT_SECONDS
            )
            return ok, err, True
        wait_total = settings.VIDEO_MAX_RETRIES * settings.VIDEO_RETRY_INTERVAL_SECONDS
        return False, f"Kameratallennetta ei löytynyt {wait_total} sekunnin kuluessa.", False

    @staticmethod
    def _mark_failed(db, event: NfcEvent, error_msg: str) -> None:
        event.status = EventStatus.FAILED.value
        event.error_message = error_msg
        db.commit()
        logger.error("Videoleikkaus epäonnistui tapahtumalle #%s: %s", event.id, error_msg)
        record_system_event(db, "ERROR", "VIDEO", f"Videoleikkaus epäonnistui (tapahtuma #{event.id})",
                            {"event_id": event.id, "error": error_msg})


video_service = VideoService()
