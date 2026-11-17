import datetime
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models import WaterMeasurement
from app.providers.water_base import AbstractWaterProvider, WaterMeasurementDTO
from app.providers.water_mock import MockWaterProvider
from app.services.horses import get_drinking_horse
from app.services.system_events import record_system_event
from app.timeutils import local_date_key, local_day_start_utc, to_naive_utc

logger = logging.getLogger(__name__)


@dataclass
class DailyWater:
    date: str
    total_liters: float
    measurement_count: int


@dataclass
class TodayWater:
    liters: float
    count: int
    latest: Optional[WaterMeasurement]


class WaterService:
    def __init__(self, provider: Optional[AbstractWaterProvider] = None):
        self.provider = provider or MockWaterProvider(settings.WATER_EXTERNAL_ID)

    # --- Mittausten vastaanotto ------------------------------------------------
    def process_measurement_dto(
        self, dto: WaterMeasurementDTO, db: Session
    ) -> Tuple[Optional[WaterMeasurement], str]:
        """
        Käsittelee juomamittauksen Antero-rajauksen mukaisesti:
        1. Duplikaatit (external_measurement_id) ohitetaan.
        2. Väärän laitetunnuksen mittaus tallennetaan ilman hevosta (data ei häviä).
        3. Jos Anteroa ei löydy, hevosta EI luoda, vaan kirjataan hälytys ja
           mittaus tallennetaan ilman hevosta.
        """
        existing = (
            db.query(WaterMeasurement)
            .filter(WaterMeasurement.external_measurement_id == dto.external_measurement_id)
            .first()
        )
        if existing:
            return existing, "DUPLICATE_SKIPPED"

        if dto.external_water_id != settings.WATER_EXTERNAL_ID:
            logger.warning(
                "Mittaus tuntemattomalta juomalaitteelta '%s' (odotettu '%s'), tallennetaan ilman hevosta.",
                dto.external_water_id, settings.WATER_EXTERNAL_ID,
            )
            return self._save(db, dto, horse_id=None), "UNRECOGNIZED_WATER_ID"

        horse = get_drinking_horse(db)
        if not horse:
            error_msg = (
                f"KONFIGURAATIOVIRHE: Juomamittauksen kohdehevosta '{settings.DRINKING_HORSE_NAME}' "
                f"ei löydy tietokannasta! Mittausta #{dto.external_measurement_id} ei voida yhdistää. "
                f"Luo hevonen nimeltä '{settings.DRINKING_HORSE_NAME}' web-käyttöliittymästä tai API:lla."
            )
            logger.error(error_msg)
            record_system_event(
                db, "ERROR", "WATER", error_msg,
                {"external_measurement_id": dto.external_measurement_id}, commit=False,
            )
            return self._save(db, dto, horse_id=None), "ANTERO_NOT_FOUND"

        record = self._save(db, dto, horse_id=horse.id)
        logger.info("Juomismittaus tallennettu: %s L (mittaus-ID %s)", dto.liters, dto.external_measurement_id)
        return record, "OK"

    @staticmethod
    def _save(db: Session, dto: WaterMeasurementDTO, horse_id: Optional[int]) -> WaterMeasurement:
        record = WaterMeasurement(
            horse_id=horse_id,
            external_measurement_id=dto.external_measurement_id,
            external_water_id=dto.external_water_id,
            measured_at=to_naive_utc(dto.measured_at),
            liters=dto.liters,
            raw_data_json=dto.raw_data_json,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    async def sync_measurements(self, db: Session) -> int:
        """Hakee uudet mittaukset juomapalvelusta. Palauttaa Anteroon liitettyjen uusien rivien määrän."""
        try:
            measurements = await self.provider.fetch_recent_measurements()
        except Exception:
            logger.exception("Virhe juomamittausten noudossa")
            return 0
        count = 0
        for dto in measurements:
            _, status = self.process_measurement_dto(dto, db)
            if status == "OK":
                count += 1
        return count

    # --- Raportointi -----------------------------------------------------------
    def daily_summary(self, db: Session, days: int = 14) -> List[DailyWater]:
        """Juomahevosen vuorokausisummat Suomen ajan mukaan, viimeiset `days` päivää."""
        horse = get_drinking_horse(db)
        if not horse or days <= 0:
            return []
        since = local_day_start_utc(days_ago=days - 1)
        rows = (
            db.query(WaterMeasurement.measured_at, WaterMeasurement.liters)
            .filter(WaterMeasurement.horse_id == horse.id, WaterMeasurement.measured_at >= since)
            .all()
        )
        totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0])
        for measured_at, liters in rows:
            bucket = totals[local_date_key(measured_at)]
            bucket[0] += liters
            bucket[1] += 1
        return [
            DailyWater(date=key, total_liters=round(total, 1), measurement_count=int(count))
            for key, (total, count) in sorted(totals.items())
        ]

    def today(self, db: Session, now: Optional[datetime.datetime] = None) -> TodayWater:
        """Juomahevosen tämän päivän (Suomen aika) juomamäärä ja viimeisin mittaus."""
        horse = get_drinking_horse(db)
        if not horse:
            return TodayWater(0.0, 0, None)
        start = local_day_start_utc(now)
        liters = [
            m.liters
            for m in db.query(WaterMeasurement.liters)
            .filter(WaterMeasurement.horse_id == horse.id, WaterMeasurement.measured_at >= start)
            .all()
        ]
        latest = (
            db.query(WaterMeasurement)
            .filter(WaterMeasurement.horse_id == horse.id)
            .order_by(WaterMeasurement.measured_at.desc())
            .first()
        )
        return TodayWater(round(sum(liters), 1), len(liters), latest)


water_service = WaterService()
