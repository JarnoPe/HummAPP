import os
import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List
import datetime
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VideoSourceMatch:
    """
    Kameratiedoston täsmäystulos.
    """
    file_path: Path
    clip_start_offset_seconds: float  # Aloituskohta tiedoston alusta sekunteina
    duration_seconds: float           # Leikkeen kokonaispituus sekunteina


class VideoSourceResolverBase(ABC):
    """
    ========================================================================
    KAMERATALLENTEEN HAKURAJAPINTA (VIDEO SOURCE RESOLVER)
    
    Tämä luokka eristää valvontakameroiden tiedostorakenteen ja nimeämistavan
    itse HummAPPin ydinlogiikasta.
    
    MITÄ TIETOA TARVITAAN LOPULLISEEN TOTEUTUKSEEN:
    1. Tallentaako kamera jatkuvaa videota pätkissä (esim. 15 tai 60 minuutin tiedostot)
       vai liiketunnistuksella käynnistyviä leikkeitä?
    2. Tiedostojen nimeämismalli (esim. `CAM01_YYYYMMDD_HHMMSS.mp4` tai
       Synology Surveillance Stationin `/volume1/surveillance/camera1/YYYY/MM/DD/...`).
    3. Tallenteiden koodekki (H.264, H.265 / HEVC) ja aikaleiman synkronointitarkkuus (NTP).
    4. Onko kameran kello UTC:ssa vai paikallisajassa (Europe/Helsinki)?
    ========================================================================
    """

    @abstractmethod
    def resolve_source(
        self,
        event_timestamp: datetime.datetime,
        seconds_before: int = 10,
        seconds_after: int = 40,
    ) -> Optional[VideoSourceMatch]:
        """
        Etsii kamerahakemistosta videotiedoston, joka kattaa aikavälin:
        [event_timestamp - seconds_before, event_timestamp + seconds_after].
        
        Palauttaa VideoSourceMatch-olion tai None, jos tallennetta ei vielä löydy.
        """
        pass


class SynologyTimestampVideoResolver(VideoSourceResolverBase):
    """
    Oletustoteutus Synology NASin kameratallenteille.
    Tukee yleisiä nimeämismalleja, kuten:
    - `CAM01_YYYYMMDD_HHMMSS.mp4`
    - `YYYY-MM-DD/HH-MM-SS.mp4`
    - Rekursiivinen haku tiedoston luonti- ja muokkausajan (mtime) tai nimen perusteella.
    """

    def __init__(self, camera_root_path: Optional[str] = None):
        self.camera_root = Path(camera_root_path or settings.CAMERA_SOURCE_PATH)

    def resolve_source(
        self,
        event_timestamp: datetime.datetime,
        seconds_before: int = 10,
        seconds_after: int = 40,
    ) -> Optional[VideoSourceMatch]:
        if not self.camera_root.exists():
            logger.warning(f"Kamerahakemistoa ei löydy: {self.camera_root}")
            return None

        # Etsitään mp4 ja mkv -tiedostoja
        video_files: List[Path] = []
        for ext in ("*.mp4", "*.mkv", "*.avi"):
            video_files.extend(self.camera_root.rglob(ext))

        if not video_files:
            logger.info(f"Kamerahakemistossa {self.camera_root} ei ole videotiedostoja.")
            return None

        target_time = event_timestamp.timestamp()
        target_start = target_time - seconds_before
        duration = seconds_before + seconds_after

        # 1. Yritä päätellä tiedostonimestä aikaleima (YYYYMMDD_HHMMSS)
        pattern = re.compile(r"(\d{4})[_-]?(\d{2})[_-]?(\d{2})[_-]?(\d{2})[_-]?(\d{2})[_-]?(\d{2})")
        for f in sorted(video_files, key=lambda p: p.stat().st_mtime, reverse=True):
            match = pattern.search(f.name)
            if match:
                try:
                    year, month, day, hour, minute, second = map(int, match.groups())
                    file_start_dt = datetime.datetime(year, month, day, hour, minute, second, tzinfo=datetime.timezone.utc)
                    file_start_ts = file_start_dt.timestamp()
                    # Jos tapahtuma osuu tiedoston aikaväliin (oletetaan tiedoston kesto esim. 15-60 min)
                    if file_start_ts <= target_start <= (file_start_ts + 3600):
                        offset = max(0.0, target_start - file_start_ts)
                        logger.info(f"Löydetty vastaava kameratallenne nimestä: {f.name}, offset={offset:.1f}s")
                        return VideoSourceMatch(file_path=f, clip_start_offset_seconds=offset, duration_seconds=duration)
                except Exception as e:
                    logger.debug(f"Aikaleiman parsintavirhe tiedostosta {f.name}: {e}")

        # 2. Jos tiedostonimi ei sisällä aikaleimaa, tarkistetaan tiedoston muokkausaika (mtime)
        for f in sorted(video_files, key=lambda p: p.stat().st_mtime, reverse=True):
            stat = f.stat()
            file_mtime = stat.st_mtime
            # Jos tiedosto on muokattu tapahtuman jälkeen (tallenne päättynyt tapahtuman jälkeen)
            if file_mtime >= target_start:
                # Oletetaan aloitus 10s ennen tapahtumaa
                offset = max(0.0, file_mtime - target_time)
                return VideoSourceMatch(file_path=f, clip_start_offset_seconds=0.0, duration_seconds=duration)

        return None
