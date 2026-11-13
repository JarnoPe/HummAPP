import datetime
from app.services.air_quality import air_quality_service
from app.providers.air_base import AirMeasurementDTO
from app.models import StableAirMeasurement


def test_stable_air_measurement_storage(db_session, client, auth_headers):
    """
    Testaa ilmanlaatumittauksen tallentaminen:
    - Lämpötila, kosteus, ammoniakki, CO2, pienhiukkaset
    - Mittaustiedot näkyvät API-rajapinnassa
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    dto = AirMeasurementDTO(
        sensor_id="SENSOR-TEST-KARSINA-1",
        location="Tallikäytävä Ovi B",
        measured_at=now,
        temperature=11.5,
        humidity=68.0,
        ammonia=3.2,
        co2=850.0,
        particulate_matter=22.5,
        raw_data_json='{"status": "ok"}',
    )

    record = air_quality_service.save_reading_dto(dto, db_session)
    assert record.id is not None
    assert record.sensor_id == "SENSOR-TEST-KARSINA-1"
    assert record.temperature == 11.5
    assert record.ammonia == 3.2

    # Haetaan API:sta
    resp = client.get("/api/stable-air?limit=5", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert items[0]["sensor_id"] == "SENSOR-TEST-KARSINA-1"
    assert items[0]["temperature"] == 11.5
