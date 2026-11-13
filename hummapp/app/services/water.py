import json
import logging
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.config import settings
from app.models import WaterMeasurement, Horse, SystemEvent, utc_now
from app.providers.water_base import AbstractWaterProvider, WaterMeasurementDTO
from app.providers.water_mock import MockWaterProvider

logger = logging.getLogger(__name__)


class WaterService:
    def __init__(self, provider: Optional[AbstractWaterProvider] = None):
        self.provider = provider or MockWaterProvider(settings.WATER_EXTERNAL_ID)

    def process_measurement_dto(
        self,
        dto: WaterMeasurementDTO,
        db: Session,
    ) -> Tuple[Optional[WaterMeasurement], str]:
        """
        Käsittelee yksittäisen juomamittauksen tiukasti Antero-rajauksen mukaisesti:
        1. Estä duplikaattien tallennus (external_measurement_id).
        2. Tarkista vastaako laitetunnus asetettua WATER_EXTERNAL_ID-arvoa.
        3. Etsi hevosista Antero (DRINKING_HORSE_NAME).
        4. Jos Anteroa ei löydy, ÄLÄ luo hevosta huomaamatta vaan kirjaa selkeä virhe!
        5. Jos laitetunnus ei täsmää, tallenna horse_id=None (älä hukkaa dataa).
        """
        # 1. Duplikaatin tarkistus
        existing = (
            db.query(WaterMeasurement)
            .filter(WaterMeasurement.external_measurement_id == dto.external_measurement_id)
            .first()
        )
        if existing:
            return existing, "DUPLICATE_SKIPPED"

        measured_time = dto.measured_at
        if measured_time.tzinfo is not None:
            measured_time = measured_time.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        # 2. Ulkoisen mittarin täsmäytys Anteron asetukseen
        if dto.external_water_id != settings.WATER_EXTERNAL_ID:
            logger.warning(
                f"Vastaanotettu mittaus tuntemattomalle juomalaitteelle '{dto.external_water_id}'. "
                f"Asetettu laite Anterolle on '{settings.WATER_EXTERNAL_ID}'. Tallennettu ilman hevosyhdistystä."
            )
            unassigned_record = WaterMeasurement(
                horse_id=None,
                external_measurement_id=dto.external_measurement_id,
                external_water_id=dto.external_water_id,
                measured_at=measured_time,
                liters=dto.liters,
                raw_data_json=dto.raw_data_json,
            )
            db.add(unassigned_record)
            db.commit()
            db.refresh(unassigned_record)
            return unassigned_record, "UNRECOGNIZED_WATER_ID"

        # 3. Anteron etsiminen tietokannasta
        antero = db.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()
        if not antero:
            error_msg = (
                f"KONFIGURAATIOVIRHE: Juomamittauksen kohdehevosta '{settings.DRINKING_HORSE_NAME}' "
                f"ei löydy tietokannasta! Mittausta #{dto.external_measurement_id} ei voida yhdistää. "
                f"Luo hevonen nimeltä '{settings.DRINKING_HORSE_NAME}' web-käyttöliittymästä tai API:lla."
            )
            logger.error(error_msg)
            # Kirjataan järjestelmätapahtuma hälytykseksi
            sys_event = SystemEvent(
                level="ERROR",
                event_type="WATER",
                message=error_msg,
                details_json=json.dumps({"external_measurement_id": dto.external_measurement_id}),
            )
            db.add(sys_event)

            # Tallennetaan mittaus silti ilman hevoslinkitystä, jotta data ei häviä
            record = WaterMeasurement(
                horse_id=None,
                external_measurement_id=dto.external_measurement_id,
                external_water_id=dto.external_water_id,
                measured_at=measured_time,
                liters=dto.liters,
                raw_data_json=dto.raw_data_json,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record, "ANTERO_NOT_FOUND"

        # 4. Onnistunut tallennus ja liitos Anteroon
        record = WaterMeasurement(
            horse_id=antero.id,
            external_measurement_id=dto.external_measurement_id,
            external_water_id=dto.external_water_id,
            measured_at=measured_time,
            liters=dto.liters,
            raw_data_json=dto.raw_data_json,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(
            f"Anteron juomismittaus tallennettu: {dto.liters} L "
            f"(mittaus-ID: {dto.external_measurement_id}, aika: {measured_time})"
        )
        return record, "OK"

    async def sync_measurements(self, db: Session) -> int:
        """Ajastettu haku juomapalvelusta."""
        try:
            measurements = await self.provider.fetch_recent_measurements()
            count = 0
            for dto in measurements:
                _, status = self.process_measurement_dto(dto, db)
                if status == "OK":
                    count += 1
            return count
        except Exception as e:
            logger.exception(f"Virhe juomamittausten noudossa: {e}")
            return 0


# Tarjotaan datetime-importti moduuliin
import datetime
water_service = WaterService()
