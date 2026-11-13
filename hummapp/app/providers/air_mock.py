import json
import random
import datetime
from typing import List
from app.providers.air_base import AbstractAirQualityProvider, AirMeasurementDTO


class MockAirQualityProvider(AbstractAirQualityProvider):
    """
    Mock-toteutus talli-ilman mittauksille.
    Tuottaa realistisia talliympäristön arvoja:
    - Lämpötila: 8.0 - 14.5 °C
    - Kosteus: 60 - 78 %
    - Ammoniakki: 1.5 - 6.5 ppm (suositus alle 10 ppm tallissa)
    - CO2: 650 - 1100 ppm
    - Pienhiukkaset PM2.5: 12 - 35 µg/m³
    """

    async def fetch_recent_readings(self) -> List[AirMeasurementDTO]:
        now = datetime.datetime.now(datetime.timezone.utc)
        readings: List[AirMeasurementDTO] = []

        locations = [
            ("SENSOR-STABLE-MAIN", "Päätalli / Karsinakäytävä"),
            ("SENSOR-STABLE-BOX-ANTERO", "Karsina 4 (Antero)"),
        ]

        for sensor_id, loc in locations:
            temp = round(random.uniform(9.0, 13.5), 1)
            humidity = round(random.uniform(62.0, 74.0), 1)
            ammonia = round(random.uniform(1.8, 5.2), 2)
            co2 = round(random.uniform(700.0, 1050.0), 1)
            pm = round(random.uniform(14.0, 28.0), 1)

            raw = {
                "sensor": sensor_id,
                "battery_mv": 3280,
                "signal_rssi": -65,
                "calibrated": True,
                "timestamp": now.isoformat(),
            }

            dto = AirMeasurementDTO(
                sensor_id=sensor_id,
                location=loc,
                measured_at=now,
                temperature=temp,
                humidity=humidity,
                ammonia=ammonia,
                co2=co2,
                particulate_matter=pm,
                raw_data_json=json.dumps(raw),
            )
            readings.append(dto)

        return readings
