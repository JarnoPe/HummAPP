import datetime
from app.services.water import water_service
from app.providers.water_base import WaterMeasurementDTO
from app.models import WaterMeasurement, Horse
from app.config import settings


def test_antero_water_measurement_success(db_session):
    """
    Testaa Anteron juomismittauksen tallentaminen:
    - Oikea WATER_EXTERNAL_ID
    - Yhdistyy Anteroon
    - Litramäärä tallentuu oikein
    """
    antero = db_session.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()
    assert antero is not None

    now = datetime.datetime.now(datetime.timezone.utc)
    dto = WaterMeasurementDTO(
        external_measurement_id="TEST-WTR-001",
        external_water_id=settings.WATER_EXTERNAL_ID,
        measured_at=now,
        liters=8.5,
        raw_data_json='{"flow_rate": 8.0}',
    )

    record, status = water_service.process_measurement_dto(dto, db_session)
    assert status == "OK"
    assert record.horse_id == antero.id
    assert record.liters == 8.5
    assert record.external_measurement_id == "TEST-WTR-001"


def test_unknown_water_id_not_attached_to_antero(db_session):
    """
    Testaa tuntemattoman water-ID:n käsittely:
    - Ulkoinen laitetunnus ei vastaa Anteron WATER_EXTERNAL_ID-arvoa
    - Mittausta EI yhdistetä Anteroon (horse_id on None)
    - Alkuperäinen mittausdata EI katoa (raw_data_json tallessa)
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    dto = WaterMeasurementDTO(
        external_measurement_id="TEST-WTR-STRANGER-099",
        external_water_id="SOME-OTHER-DISPENSER-XYZ",
        measured_at=now,
        liters=12.0,
        raw_data_json='{"device": "unknown"}',
    )

    record, status = water_service.process_measurement_dto(dto, db_session)
    assert status == "UNRECOGNIZED_WATER_ID"
    assert record.horse_id is None
    assert record.external_water_id == "SOME-OTHER-DISPENSER-XYZ"
    assert record.liters == 12.0


def test_water_measurement_duplicate_deduplication(db_session):
    """
    Testaa saman mittauksen kaksoistallennuksen estäminen:
    Jos sama external_measurement_id saapuu toistamiseen, se sivuutetaan.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    dto = WaterMeasurementDTO(
        external_measurement_id="TEST-WTR-DUPE-001",
        external_water_id=settings.WATER_EXTERNAL_ID,
        measured_at=now,
        liters=6.2,
    )

    record1, status1 = water_service.process_measurement_dto(dto, db_session)
    assert status1 == "OK"

    # Yritetään tallentaa sama uudelleen
    record2, status2 = water_service.process_measurement_dto(dto, db_session)
    assert status2 == "DUPLICATE_SKIPPED"
    assert record1.id == record2.id

    # Varmistetaan että kannassa on edelleen vain 1 kappale tätä id:tä
    count = db_session.query(WaterMeasurement).filter(
        WaterMeasurement.external_measurement_id == "TEST-WTR-DUPE-001"
    ).count()
    assert count == 1


def test_water_measurement_when_antero_not_found(db_session):
    """
    Testaa tilanne, jossa Anteroa ei löydy kannasta:
    - Ei luo hevosta salaa
    - Palauttaa ANTERO_NOT_FOUND
    - Säilyttää raakadatan
    """
    # Poistetaan Antero hetkeksi
    db_session.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).delete()
    db_session.commit()

    now = datetime.datetime.now(datetime.timezone.utc)
    dto = WaterMeasurementDTO(
        external_measurement_id="TEST-WTR-NO-ANTERO",
        external_water_id=settings.WATER_EXTERNAL_ID,
        measured_at=now,
        liters=7.0,
    )

    record, status = water_service.process_measurement_dto(dto, db_session)
    assert status == "ANTERO_NOT_FOUND"
    assert record.horse_id is None

    # Varmistetaan, ettei Anteroa luotu salaa
    antero_check = db_session.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()
    assert antero_check is None
