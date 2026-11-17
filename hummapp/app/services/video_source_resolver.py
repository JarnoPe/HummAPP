"""
========================================================================
KAMERATALLENTEEN HAKURAJAPINTA (VIDEO SOURCE RESOLVER)

Eristää valvontakameroiden tiedostorakenteen ja nimeämistavan HummAPPin
ydinlogiikasta. Oletustoteutus tukee aikaleimallisia tiedostonimiä, kuten
- `CAM01_YYYYMMDD_HHMMSS.mp4`
- Synology Surveillance Station: `<kamera>/<YYYYMMDD>AM/<kamera>-YYYYMMDD-HHMMSS-<unix>.mp4`
- `YYYY-MM-DD/HH-MM-SS.mp4` -tyyliset rakenteet, joissa aikaleima on nimessä

TÄRKEÄÄ LEIKKEEN OSUMATARKKUUDELLE (leike on vain 5 s + 5 s):
1. Tiedostonimen aikaleima tulkitaan CAMERA_TIMEZONE-aikavyöhykkeessä
   (Synology tallentaa yleensä paikallisaikaan, Europe/Helsinki).
2. Kameran ja puhelimen kellot pitää synkronoida NTP:llä.
3. Kesken oleva tallenne (MP4 ilman moov-atomia) ei ole luettavissa ennen kuin
   kamera sulkee tiedoston. Mitä lyhyemmät tallennepätkät kamerassa on
   (esim. 1–5 min), sitä nopeammin leike valmistuu.
========================================================================
"""
import datetime
import logging
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional
from zoneinfo import ZoneInfo

from app.config import settings
from app.timeutils import as_aware_utc

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov"}
FILENAME_TIMESTAMP = re.compile(r"(\d{4})[_-]?(\d{2})[_-]?(\d{2})[_T_-]?(\d{2})[_:-]?(\d{2})[_:-]?(\d{2})")

ProbeFn = Callable[[Path], Optional[float]]


@dataclass
class VideoSourceMatch:
    """Kameratiedoston täsmäystulos."""
    file_path: Path
    clip_start_offset_seconds: float  # Aloituskohta tiedoston alusta sekunteina
    duration_seconds: float           # Leikkeen pituus sekunteina
    partial: bool = False             # True = tiedosto vaihtui kesken leikkeen, leike on lyhyempi


@dataclass
class _Candidate:
    path: Path
    start_utc: datetime.datetime


def ffprobe_duration(path: Path) -> Optional[float]:
    """Palauttaa videotiedoston keston sekunteina tai None, jos tiedosto ei ole (vielä) luettavissa."""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
        )
        return float(proc.stdout.decode().strip()) if proc.returncode == 0 else None
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return None


class VideoSourceResolverBase(ABC):
    @abstractmethod
    def resolve_source(
        self,
        event_timestamp: datetime.datetime,
        seconds_before: int,
        seconds_after: int,
    ) -> Optional[VideoSourceMatch]:
        """
        Etsii videotiedoston, joka kattaa aikavälin
        [event_timestamp - seconds_before, event_timestamp + seconds_after].
        `event_timestamp` on naiivi UTC (kuten kannassa) tai aware-aika.
        Palauttaa None, jos sopivaa valmista tallennetta ei (vielä) ole.
        """


class SynologyTimestampVideoResolver(VideoSourceResolverBase):
    def __init__(
        self,
        camera_root_path: Optional[str] = None,
        camera_timezone: Optional[str] = None,
        max_file_duration_seconds: Optional[int] = None,
        probe: ProbeFn = ffprobe_duration,
    ):
        self.camera_root = Path(camera_root_path or settings.CAMERA_SOURCE_PATH)
        self.camera_tz = ZoneInfo(camera_timezone or settings.CAMERA_TIMEZONE)
        self.max_file_duration = datetime.timedelta(
            seconds=max_file_duration_seconds or settings.CAMERA_FILE_MAX_DURATION_SECONDS
        )
        self.probe = probe

    # --- Julkinen rajapinta ---------------------------------------------------
    def resolve_source(
        self,
        event_timestamp: datetime.datetime,
        seconds_before: int,
        seconds_after: int,
    ) -> Optional[VideoSourceMatch]:
        if not self.camera_root.exists():
            logger.warning("Kamerahakemistoa ei löydy: %s", self.camera_root)
            return None

        event_utc = as_aware_utc(event_timestamp)
        clip_start = event_utc - datetime.timedelta(seconds=seconds_before)
        duration = float(seconds_before + seconds_after)

        candidates = sorted(self._find_candidates(clip_start), key=lambda c: c.start_utc)
        if not candidates:
            logger.info("Kameratallennetta ei löytynyt ajalle %s", event_utc.isoformat())
            return None

        preceding = [c for c in candidates if c.start_utc <= clip_start]
        if preceding:
            chosen = preceding[-1]
            offset = (clip_start - chosen.start_utc).total_seconds()
        else:
            # Tiedosto alkoi vasta leikkeen aikana (kamera aloitti uuden pätkän juuri ennen leimausta)
            chosen = candidates[0]
            if chosen.start_utc > event_utc:
                return None
            offset = 0.0
            duration -= (chosen.start_utc - clip_start).total_seconds()

        file_length = self.probe(chosen.path)
        if file_length is None:
            logger.info("Tallenne %s ei ole vielä luettavissa (kirjoitus kesken?)", chosen.path.name)
            return None

        if file_length >= offset + duration:
            logger.info("Kameratallenne löytyi: %s, offset=%.1fs", chosen.path.name, offset)
            return VideoSourceMatch(chosen.path, offset, duration)

        newer_exists = any(c.start_utc > chosen.start_utc for c in candidates)
        if newer_exists and file_length > offset:
            # Kamera vaihtoi tiedostoa kesken leikkeen -> otetaan se mitä on
            logger.warning("Leike %s jää vajaaksi tiedostonvaihdon takia", chosen.path.name)
            return VideoSourceMatch(chosen.path, offset, file_length - offset, partial=True)

        return None  # Tallenne ei vielä kata koko leikettä -> yritetään myöhemmin uudelleen

    # --- Sisäiset apurit ------------------------------------------------------
    def parse_file_start(self, path: Path) -> Optional[datetime.datetime]:
        """Lukee tiedostonimen aikaleiman kameran aikavyöhykkeessä ja palauttaa sen UTC:nä."""
        match = FILENAME_TIMESTAMP.search(path.name)
        if not match:
            return None
        try:
            local = datetime.datetime(*map(int, match.groups()), tzinfo=self.camera_tz)
        except ValueError:
            return None
        return local.astimezone(datetime.timezone.utc)

    def _find_candidates(self, clip_start_utc: datetime.datetime) -> List[_Candidate]:
        earliest = clip_start_utc - self.max_file_duration
        result = []
        for path in self._iter_video_files(clip_start_utc):
            start = self.parse_file_start(path)
            if start is not None and start >= earliest:
                result.append(_Candidate(path, start))
        return result

    def _iter_video_files(self, clip_start_utc: datetime.datetime) -> Iterable[Path]:
        """
        Rajaa haun ensin päiväkansioihin (esim. 20261117AM, 2026-11-17, 2026/11/17),
        jotta koko valvontahakemistoa ei käydä läpi jokaisella yrityksellä.
        Jos päiväkansioita ei löydy, haetaan koko hakemistosta.
        """
        local_start = clip_start_utc.astimezone(self.camera_tz)
        days = {local_start.date(), (local_start - self.max_file_duration).date()}
        day_dirs: set[Path] = set()
        for day in days:
            for token in (day.strftime("%Y%m%d"), day.strftime("%Y-%m-%d")):
                for pattern in (f"{token}*", f"*/{token}*"):
                    day_dirs.update(p for p in self.camera_root.glob(pattern) if p.is_dir())
            nested = self.camera_root / day.strftime("%Y/%m/%d")
            if nested.is_dir():
                day_dirs.add(nested)

        roots = day_dirs or {self.camera_root}
        seen: set[Path] = set()
        for root in roots:
            for path in root.rglob("*"):
                if path.suffix.lower() in VIDEO_EXTENSIONS and path not in seen and path.is_file():
                    seen.add(path)
                    yield path
        # Tiedostot suoraan juuressa päiväkansioiden rinnalla (esim. CAM01_YYYYMMDD_HHMMSS.mp4)
        if day_dirs:
            for path in self.camera_root.iterdir():
                if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS and path not in seen:
                    yield path
