import json
import random
import datetime
from typing import Optional, List
from app.providers.water_base import AbstractWaterProvider, WaterMeasurementDTO
from app.config import settings


class MockWaterProvider(AbstractWaterProvider):
    """
    Mock-toteutus juoma-automaatille.
    Simuloi Anteron säännöllisiä juomiskertoja (3 - 12 litraa kerrallaan).
    """

    def __init__(self, external_water_id: Optional[str] = None):
        self.external_water_id = external_water_id or settings.WATER_EXTERNAL_ID

    async def fetch_recent_measurements(
        self, since: Optional[datetime.datetime] = None
    ) -> List[WaterMeasurementDTO]:
        measurements: List[WaterMeasurementDTO] = []
        now = datetime.datetime.now(datetime.timezone.utc)

        # Simuloidaan mittaus tälle tunnille
        timestamp_str = now.strftime("%Y%m%d%H%M")
        measurement_id = f"MOCK-WTR-{timestamp_str}"

        # Realistinen hevosannos juoma-automaatista: 4.5 - 9.5 litraa
        liters = round(random.uniform(4.5, 9.5), 2)

        raw_payload = {
            "source": "MockWaterDispenserV1",
            "device_serial": self.external_water_id,
            "flow_rate_lpm": 8.2,
            "duration_sec": int(liters * 7.2),
            "temp_celsius": 12.4,
            "raw_timestamp": now.isoformat(),
        }

        dto = WaterMeasurementDTO(
            external_measurement_id=measurement_id,
            external_water_id=self.external_water_id,
            measured_at=now,
            liters=liters,
            raw_data_json=json.dumps(raw_payload),
        )
        measurements.append(dto)
        return measurements
