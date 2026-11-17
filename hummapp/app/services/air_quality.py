import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models import StableAirMeasurement
from app.providers.air_base import AbstractAirQualityProvider, AirMeasurementDTO
from app.providers.air_mock import MockAirQualityProvider
from app.timeutils import to_naive_utc

logger = logging.getLogger(__name__)


class AirQualityService:
    def __init__(self, provider: Optional[AbstractAirQualityProvider] = None):
        self.provider = provider or MockAirQualityProvider()

    @staticmethod
    def _is_duplicate(db: Session, dto: AirMeasurementDTO) -> bool:
        return (
            db.query(StableAirMeasurement.id)
            .filter(
                StableAirMeasurement.sensor_id == dto.sensor_id,
                StableAirMeasurement.measured_at == to_naive_utc(dto.measured_at),
            )
            .first()
            is not None
        )

    def save_reading_dto(self, dto: AirMeasurementDTO, db: Session, commit: bool = True) -> Optional[StableAirMeasurement]:
        """Tallentaa lukeman. Sama anturi + sama mittausaika tallennetaan vain kerran."""
        if self._is_duplicate(db, dto):
            return None
        record = StableAirMeasurement(
            sensor_id=dto.sensor_id,
            location=dto.location,
            measured_at=to_naive_utc(dto.measured_at),
            temperature=dto.temperature,
            humidity=dto.humidity,
            ammonia=dto.ammonia,
            co2=dto.co2,
            particulate_matter=dto.particulate_matter,
            raw_data_json=dto.raw_data_json,
        )
        db.add(record)
        if commit:
            db.commit()
            db.refresh(record)
        return record

    async def sync_air_readings(self, db: Session) -> int:
        """Hakee tuoreet lukemat ja tallentaa uudet yhtenä eränä. Palauttaa uusien rivien määrän."""
        try:
            readings = await self.provider.fetch_recent_readings()
        except Exception:
            logger.exception("Virhe talli-ilman mittausten noudossa")
            return 0
        count = sum(1 for dto in readings if self.save_reading_dto(dto, db, commit=False))
        db.commit()
        logger.info("Talli-ilman mittaukset päivitetty: %s uutta lukemaa.", count)
        return count


air_quality_service = AirQualityService()
