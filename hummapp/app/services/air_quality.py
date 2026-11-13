import datetime
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from app.config import settings
from app.models import StableAirMeasurement
from app.providers.air_base import AbstractAirQualityProvider, AirMeasurementDTO
from app.providers.air_mock import MockAirQualityProvider

logger = logging.getLogger(__name__)


class AirQualityService:
    def __init__(self, provider: Optional[AbstractAirQualityProvider] = None):
        self.provider = provider or MockAirQualityProvider()

    def save_reading_dto(self, dto: AirMeasurementDTO, db: Session) -> StableAirMeasurement:
        measured_time = dto.measured_at
        if measured_time.tzinfo is not None:
            measured_time = measured_time.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        record = StableAirMeasurement(
            sensor_id=dto.sensor_id,
            location=dto.location,
            measured_at=measured_time,
            temperature=dto.temperature,
            humidity=dto.humidity,
            ammonia=dto.ammonia,
            co2=dto.co2,
            particulate_matter=dto.particulate_matter,
            raw_data_json=dto.raw_data_json,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    async def sync_air_readings(self, db: Session) -> int:
        """Ajastettu haku talli-ilman mittauspalvelusta."""
        try:
            readings = await self.provider.fetch_recent_readings()
            count = 0
            for dto in readings:
                self.save_reading_dto(dto, db)
                count += 1
            logger.info(f"Talli-ilman mittaukset päivitetty: {count} mittausta tallennettu.")
            return count
        except Exception as e:
            logger.exception(f"Virhe talli-ilman mittausten noudossa: {e}")
            return 0


air_quality_service = AirQualityService()
